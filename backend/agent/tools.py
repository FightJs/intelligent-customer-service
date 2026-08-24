"""Agent tools 定义与执行函数。

5 个工具负责信息采集和进度控制。
订单发送由用户在前端明确确认，不由 LLM 工具完成。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from agent import flow
from store.uploads import resolve_image
from survey.models import StudioFormState, FieldValue
from survey.schema_def import SECTION_BY_ID, SECTION_ORDER, AGENT_GUIDE


@dataclass
class ToolEvent:
    """字段更新事件（前端用来更新表单）。"""
    kind: str          # 'fill' | 'skip' | 'deliverable'
    section_id: str
    field_id: str = ''
    value: Any = None


def _normalize_multi_choice(value: object, fdef) -> tuple[list[str] | None, str | None]:
    """兼容模型或快捷选项把单个多选答案传成字符串。"""
    if isinstance(value, str):
        candidates = [value.strip()]
        for separator in ('、', '，', ',', '；', ';', '/'):
            if separator in value:
                candidates = [item.strip() for item in value.split(separator)]
                break
    elif isinstance(value, list):
        candidates = value
    else:
        return None, f'需要 list 或 string，收到 {type(value).__name__}'

    valid_values = {option.value for option in (fdef.options or [])}
    labels = {option.label: option.value for option in (fdef.options or [])}
    cleaned: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        normalized = candidate.strip()
        if valid_values and normalized not in valid_values:
            normalized = labels.get(normalized, normalized)
        cleaned.append(normalized)
    return list(dict.fromkeys(cleaned)), None


# ── Tool 定义（Anthropic 格式）──────────────────────────────

TOOL_DEFS: list[dict] = [
    {
        'name': 'fill_fields',
        'description': (
            '只提取最后一条用户消息中新出现、补充或明确修改的信息。'
            '历史消息只用于判断当前回答对应哪个字段，'
            '不要重新传递历史中已经保存的值。'
            '没有可写入的信息时，必须返回 updates=[]。'
            'choice-single 填选项 value（英文标识），text 填原话。'
            'choice-multi 必须传选项 value 的字符串数组。'
            'choice-multi、dimension、table 只传本轮新增或补充的内容，'
            '后端会与已有值合并。'
            'dimension 必须传对象，键必须使用字段定义中的 dims。'
            'table 填行对象数组，例如 '
            '[{"type":"相机","model":"Sony A7M4","qty":"1"}]。'
            'image 填本轮消息 [图片N id=...] 标记里的 id 字符串数组，'
            '不要编造 id。'
            'text 或 choice-single 修改已有值时，'
            '必须先向用户确认，'
            '确认后传 confirmed=true。'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'updates': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'section_id': {
                                'type': 'string',
                                'description': '章节 id，如 customer',
                            },
                            'field_id': {
                                'type': 'string',
                                'description': '字段 id，如 brand',
                            },
                            'value': {
                                'description': (
                                    '字段值。dimension 必须传对象，例如 '
                                    '{"宽":"4.5","深":"5","高":"3"}；'
                                    'table 必须传行对象数组，'
                                    '列 id 使用 type、model、qty'
                                ),
                            },
                            'confirmed': {
                                'type': 'boolean',
                                'description': (
                                    '仅当用户明确确认修改已有 '
                                    'text 或 choice-single 值时传 true'
                                ),
                            },
                        },
                        'required': [
                            'section_id',
                            'field_id',
                            'value',
                        ],
                    },
                },
            },
            'required': ['updates'],
        },
    },
    {
        'name': 'skip_field',
        'description': '仅当当前题在 schema 中标记为可跳过时跳过该题；核心必答题会被后端拒绝。',
        'input_schema': {
            'type': 'object',
            'properties': {
                'section_id': {'type': 'string'},
                'field_id': {'type': 'string'},
            },
            'required': ['section_id', 'field_id'],
        },
    },
    {
        'name': 'skip_section',
        'description': '仅当当前模块在 schema 中标记为可跳过时跳过该模块。条件答案“否”应正常记录，不要用本工具代替。',
        'input_schema': {
            'type': 'object',
            'properties': {
                'section_id': {'type': 'string'},
                'reason': {'type': 'string'},
            },
            'required': ['section_id'],
        },
    },
    {
        'name': 'get_progress',
        'description': '查询当前采集进度：各章节完成情况、未填必填字段、下一个该问的字段。',
        'input_schema': {'type': 'object', 'properties': {}},
    },
    {
        'name': 'set_current_section',
        'description': '主动切换当前采集章节。正常按顺序推进，用户跳着回答或回头改时用。',
        'input_schema': {
            'type': 'object',
            'properties': {
                'section_id': {'type': 'string'},
            },
            'required': ['section_id'],
        },
    },
]


# ── 执行函数 ────────────────────────────────────────────────

def _apply_one(
    state: StudioFormState,
    section_id: str,
    field_id: str,
    value,
    confirmed: bool = False,
) -> tuple[bool, str | None]:
    """应用单个字段值，兼容带前缀的 field_id。

    返回 (ok, reason)；失败时 reason 描述原因（section 不存在/字段不存在/类型不匹配/choice 非法值）。
    """
    clean_fid = field_id.split('.')[-1] if '.' in field_id else field_id
    sec = state.sections.get(section_id)
    if sec is None:
        return False, f'章节不存在: {section_id}'
    current = sec.fields.get(clean_fid)
    if current is None:
        return False, f'字段不存在: {section_id}.{clean_fid}'
    fdef = next(
        (field for field in SECTION_BY_ID[section_id].fields if field.id == clean_fid),
        None,
    )
    if fdef is None:
        return False, f'字段定义不存在: {section_id}.{clean_fid}'
    try:
        if current.type == 'text':
            new_value = (
                str(value)
                if value is not None
                else ''
            )

            if (
                current.value
                and current.value != new_value
                and not confirmed
            ):
                return False, (
                    f'{clean_fid} 已有值 '
                    f'{current.value}，'
                    f'新值为 {new_value}。'
                    '请先向用户确认，'
                    '确认后传 confirmed=true。'
                )

            current.value = new_value
        elif current.type == 'choice-single':
            if not isinstance(value, str):
                return False, (
                    f'{clean_fid} 需要 string，'
                    f'收到 {type(value).__name__}'
                )

            valid_values = {
                option.value
                for option in (fdef.options or [])
            }

            if valid_values and value not in valid_values:
                label_match = next(
                    (
                        option.value
                        for option in (fdef.options or [])
                        if option.label == value
                    ),
                    None,
                )

                if label_match is None:
                    return False, (
                        f'{clean_fid} value={value} '
                        '不在 options 内'
                    )

                value = label_match

            if (
                current.value is not None
                and current.value != value
                and not confirmed
            ):
                return False, (
                    f'{clean_fid} 已有值 {current.value}，'
                    f'新值为 {value}。'
                    '请先向用户确认，确认后传 confirmed=true。'
                )

            current.value = value
        elif current.type == 'choice-multi':
            cleaned, error = _normalize_multi_choice(value, fdef)
            if error is not None or cleaned is None:
                return False, f'{clean_fid} {error}'
            current.value = list(dict.fromkeys([
                *current.value,
                *cleaned,
            ]))
        elif current.type == 'dimension':
            if not isinstance(value, dict):
                return False, (
                    f'{clean_fid} 需要 object，'
                    f'收到 {type(value).__name__}'
                )

            valid_dims = set(fdef.dims or [])
            unknown_dims = set(value) - valid_dims

            if unknown_dims:
                return False, (
                    f'{clean_fid} 包含未知维度：'
                    f'{", ".join(sorted(unknown_dims))}'
                )

            new_values = {
                key: str(item)
                for key, item in value.items()
                if item is not None
                and str(item).strip()
            }

            current.value = {
                **current.value,
                **new_values,
            }
        elif current.type == 'image':
            if isinstance(value, str):
                value = [value]
            elif not isinstance(value, list):
                return False, (
                    f'{clean_fid} image 需要 list 或 string，'
                    f'收到 {type(value).__name__}'
                )

            new_images = []
            for item in value:
                if item is None or not str(item).strip():
                    continue
                image_id = str(item)
                if not state._session_id:
                    return False, (
                        f'{clean_fid} 缺少当前会话信息，不能写入图片'
                    )
                if not image_id.startswith(f'{state._session_id}/'):
                    return False, (
                        f'{clean_fid} 图片不属于当前会话，不能写入: {image_id}'
                    )
                # 只接受真实落盘的图片 id，丢弃幻觉引用
                if resolve_image(image_id) is None:
                    return False, (
                        f'{clean_fid} 图片 id 无效: {image_id}。'
                        '只能填本轮消息 [图片N id=...] 标记里的 id。'
                    )
                new_images.append(image_id)

            current.value = list(dict.fromkeys([
                *current.value,
                *new_images,
            ]))
        elif current.type == 'table':
            if isinstance(value, dict):
                value = [value]
            elif not isinstance(value, list):
                return False, (
                    f'{clean_fid} table 需要 list 或 object，'
                    f'收到 {type(value).__name__}'
                )

            valid_columns = {
                column.id
                for column in (fdef.columns or [])
            }

            cleaned_rows: list[dict[str, str]] = []

            for index, row in enumerate(value, start=1):
                if not isinstance(row, dict):
                    return False, (
                        f'{clean_fid} 第 {index} 行需要 object，'
                        f'收到 {type(row).__name__}'
                    )

                unknown_columns = set(row) - valid_columns
                if unknown_columns:
                    column_names = ', '.join(
                        sorted(unknown_columns)
                    )
                    return False, (
                        f'{clean_fid} 包含未知列: '
                        f'{column_names}'
                    )

                cleaned_row = {
                    key: '' if cell is None else str(cell)
                    for key, cell in row.items()
                }
                cleaned_rows.append(cleaned_row)

            merged_rows = list(current.value)

            for row in cleaned_rows:
                if row not in merged_rows:
                    merged_rows.append(row)

            current.value = merged_rows
        skipped_key = f'{section_id}.{clean_fid}'
        if skipped_key in state.skipped_field_ids:
            state.skipped_field_ids.remove(skipped_key)
        if sec.status == 'skipped':
            sec.status = 'pending'
        return True, None
    except Exception as exc:
        return False, f'异常: {exc}'


def apply_updates(state: StudioFormState, updates: list[dict]) -> tuple[int, list[str]]:
    """公开 helper：批量应用字段更新（前端权威提交用，绕过 LLM）。

    返回 (成功数, 失败描述列表)。
    """
    count = 0
    failures: list[str] = []
    for index, upd in enumerate(updates):
        if not isinstance(upd, dict):
            failures.append(f'updates[{index}] 需要 object')
            continue
        section_id = upd.get('section_id')
        field_id = upd.get('field_id')
        if not isinstance(section_id, str) or not isinstance(field_id, str):
            failures.append(f'updates[{index}] 缺少有效的 section_id 或 field_id')
            continue
        ok, reason = _apply_one(
            state,
            section_id,
            field_id,
            upd.get('value'),
            confirmed=upd.get('confirmed') is True,
        )
        if ok:
            count += 1
        elif reason:
            failures.append(f'{section_id}.{field_id}: {reason}')
    flow.recompute_section_status(state)
    flow.sync_current_question(state)
    return count, failures


def execute_tool(name: str, tool_input: dict, state: StudioFormState) -> tuple[str, bool]:
    """执行 tool，返回 (结果字符串, 是否全部成功)。直接操作 state（原地修改）。"""
    if name == 'fill_fields':
        count = 0
        details: list[str] = []
        failures: list[str] = []
        for index, upd in enumerate(tool_input.get('updates', [])):
            if not isinstance(upd, dict):
                failures.append(f'updates[{index}] 需要 object')
                continue
            section_id = upd.get('section_id')
            field_id = upd.get('field_id')
            if not isinstance(section_id, str) or not isinstance(field_id, str):
                failures.append(f'updates[{index}] 缺少有效的 section_id 或 field_id')
                continue
            ok, reason = _apply_one(
                state,
                section_id,
                field_id,
                upd.get('value'),
                confirmed=upd.get('confirmed') is True,
            )
            if ok:
                count += 1
                val = upd.get('value')
                if isinstance(val, str) and val:
                    details.append(val)
            elif reason:
                failures.append(f'{section_id}.{field_id}: {reason}')
        msg = f'已填充 {count} 个字段。'
        if details:
            msg = f'已填充 {count} 个字段（{"、".join(details)}）。'
        if failures:
            msg += f' 失败 {len(failures)} 个：{"; ".join(failures)}。请根据原因修正后最多重试一次。'
        flow.recompute_section_status(state)
        flow.sync_current_question(state)
        return msg, not failures

    if name == 'skip_field':
        sid = tool_input['section_id']
        fid = tool_input['field_id'].split('.')[-1]
        ok, message = flow.skip_field(state, sid, fid)
        return message, ok

    if name == 'skip_section':
        sid = tool_input['section_id']
        ok, message = flow.skip_section(state, sid)
        return message, ok

    if name == 'get_progress':
        progress = flow.section_progress(state)
        filled, total = flow.overall_progress(state)
        lines = [f'总进度：{filled}/{total}']
        nxt = flow.next_question_field(state)
        for p in progress:
            mark = '✓' if p['complete'] else f"{p['filled']}/{p['total']}"
            tag = ' [skipped]' if p['status'] == 'skipped' else ''
            lines.append(f"  [{p['section_id']}] {p['title']} {mark}{tag}")
        if nxt:
            sec_id, field = nxt
            lines.append(
                f'下一个该问：[{sec_id}] 【{SECTION_BY_ID[sec_id].title}】{field.id} {field.label}'
            )
        else:
            lines.append('所有必填信息已采集完毕。')
        return '\n'.join(lines), True

    if name == 'set_current_section':
        sid = tool_input['section_id']
        if sid in state.sections:
            state.current_section_id = sid
            return f'已切换到章节 {SECTION_BY_ID[sid].title}。', True
        return f'[error] 未知章节 {sid}', False


    return f'[error] 未知 tool {name}', False
