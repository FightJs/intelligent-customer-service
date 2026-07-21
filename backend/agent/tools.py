"""Agent tools 定义 + 执行函数。

5 个 tool 覆盖采集 → 进度控制 → 交付物生成。
每个执行函数操作 StudioFormState，返回结果字符串（给模型看）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from agent import flow
from survey.models import StudioFormState, FieldValue
from survey.schema_def import SECTION_BY_ID, FIELD_BY_ID, SECTION_ORDER, AGENT_GUIDE


@dataclass
class ToolEvent:
    """字段更新事件（前端用来更新表单）。"""
    kind: str          # 'fill' | 'skip' | 'deliverable'
    section_id: str
    field_id: str = ''
    value: Any = None


# ── Tool 定义（Anthropic 格式）──────────────────────────────

TOOL_DEFS: list[dict] = [
    {
        'name': 'fill_fields',
        'description': '把从用户消息提取的信息填入调研表字段，可一次填多个。choice-single 填选项 value（英文标识），text 填原话，choice-multi 填 value 数组，dimension 填 {维度:值} 对象。',
        'input_schema': {
            'type': 'object',
            'properties': {
                'updates': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'section_id': {'type': 'string', 'description': '章节 id，如 customer'},
                            'field_id': {'type': 'string', 'description': '字段 id，如 brand'},
                            'value': {'description': '字段值'},
                        },
                        'required': ['section_id', 'field_id', 'value'],
                    },
                },
            },
            'required': ['updates'],
        },
    },
    {
        'name': 'skip_section',
        'description': '条件跳过某章节。如用户说"没有直播间"→ skip status。',
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
    {
        'name': 'generate_deliverable',
        'description': '当采集完成或用户要求时，生成交付物文档。',
        'input_schema': {
            'type': 'object',
            'properties': {
                'doc_type': {'type': 'string', 'enum': ['markdown', 'excel', 'word']},
            },
            'required': ['doc_type'],
        },
    },
]


# ── 执行函数 ────────────────────────────────────────────────

def _apply_one(state: StudioFormState, section_id: str, field_id: str, value) -> tuple[bool, str | None]:
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
    fdef = FIELD_BY_ID.get(clean_fid)
    try:
        if current.type == 'text':
            current.value = str(value) if value is not None else ''
        elif current.type == 'choice-single':
            if not isinstance(value, str):
                return False, f'{clean_fid} 需要 string，收到 {type(value).__name__}'
            # 校验或自动反查（label → value）
            valid_values = {o.value for o in (fdef.options or [])}
            if valid_values and value not in valid_values:
                label_match = next(
                    (o.value for o in (fdef.options or []) if o.label == value), None
                )
                if label_match is None:
                    return False, f'{clean_fid} value={value} 不在 options 内'
                value = label_match
            current.value = value
        elif current.type == 'choice-multi':
            if not isinstance(value, list):
                return False, f'{clean_fid} 需要 list，收到 {type(value).__name__}'
            valid_values = {o.value for o in (fdef.options or [])}
            cleaned: list[str] = []
            for v in value:
                if not isinstance(v, str):
                    continue
                if valid_values and v not in valid_values:
                    label_match = next(
                        (o.value for o in (fdef.options or []) if o.label == v), None
                    )
                    if label_match is None:
                        return False, f'{clean_fid} value={v} 不在 options 内'
                    v = label_match
                cleaned.append(v)
            current.value = cleaned
        elif current.type == 'dimension':
            current.value = {k: str(v) for k, v in value.items()} if isinstance(value, dict) else {}
        elif current.type == 'image':
            current.value = list(value) if isinstance(value, list) else []
        elif current.type == 'table':
            current.value = list(value) if isinstance(value, list) else []
        return True, None
    except Exception as exc:
        return False, f'异常: {exc}'


def apply_updates(state: StudioFormState, updates: list[dict]) -> tuple[int, list[str]]:
    """公开 helper：批量应用字段更新（前端权威提交用，绕过 LLM）。

    返回 (成功数, 失败描述列表)。
    """
    count = 0
    failures: list[str] = []
    for upd in updates:
        ok, reason = _apply_one(
            state, upd['section_id'], upd['field_id'], upd.get('value')
        )
        if ok:
            count += 1
        elif reason:
            failures.append(f"{upd['section_id']}.{upd['field_id']}: {reason}")
    return count, failures


def execute_tool(name: str, tool_input: dict, state: StudioFormState) -> str:
    """执行 tool，返回结果字符串（给模型看）。直接操作 state（原地修改）。"""
    if name == 'fill_fields':
        count = 0
        details: list[str] = []
        failures: list[str] = []
        for upd in tool_input.get('updates', []):
            ok, reason = _apply_one(state, upd['section_id'], upd['field_id'], upd.get('value'))
            if ok:
                count += 1
                val = upd.get('value')
                if isinstance(val, str) and val:
                    details.append(val)
            elif reason:
                failures.append(f"{upd['section_id']}.{upd['field_id']}: {reason}")
        msg = f'已填充 {count} 个字段。'
        if details:
            msg = f'已填充 {count} 个字段（{"、".join(details)}）。'
        if failures:
            msg += f' 失败 {len(failures)} 个：{"; ".join(failures)}。请根据原因修正后最多重试一次。'
        return msg

    if name == 'skip_section':
        sid = tool_input['section_id']
        flow.skip_section(state, sid)
        return f'已跳过章节 {sid}。'

    if name == 'get_progress':
        progress = flow.section_progress(state)
        filled, total = flow.overall_progress(state)
        lines = [f'总进度：{filled}/{total}']
        nxt = flow.next_unfilled_field(state)
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
        return '\n'.join(lines)

    if name == 'set_current_section':
        sid = tool_input['section_id']
        if sid in state.sections:
            state.current_section_id = sid
            return f'已切换到章节 {SECTION_BY_ID[sid].title}。'
        return f'[error] 未知章节 {sid}'

    if name == 'generate_deliverable':
        doc_type = tool_input['doc_type']
        # 实际生成（验证文件能产出），返回文件信息
        # 前端通过 /api/generate/{type} 端点下载
        suffix = {'markdown': 'md', 'excel': 'xlsx', 'word': 'docx'}[doc_type]
        return f'已生成 {doc_type} 交付物（.{suffix}），用户可在右侧面板下载。'

    return f'[error] 未知 tool {name}'
