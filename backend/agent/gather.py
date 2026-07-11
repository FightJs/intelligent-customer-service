"""AI 对话采集 Agent（DeepSeek V4-Flash）。

分工：
- 状态机（flow.py）管「问什么」——按章节推进，跳过条件不可见字段
- LLM 管「怎么理解用户」和「怎么自然地问」

每轮对话采用两步策略（绕过 DeepSeek thinking 模式不支持 tool_choice=required 的限制）：
1. JSON 提取：LLM 用 response_format=json_object 输出要填的字段，后端解析填入
2. 自然回复：基于更新后的 state，LLM 生成确认 + 下一问

不用 function calling，改用 JSON 模式——更可靠，不受 thinking 模式限制。
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from agent import flow
from agent.llm import get_client, LLM_MODEL
from survey.models import StudioFormState
from survey.schema_def import SECTION_BY_ID, FIELD_BY_ID, AGENT_GUIDE


@dataclass
class ToolEvent:
    """字段更新事件（前端用来更新表单）。"""
    kind: str          # 'fill' | 'skip'
    section_id: str
    field_id: str = ''
    value: object = None


@dataclass
class TurnResult:
    """单轮对话结果。"""
    reply: str
    tool_events: list[ToolEvent]
    state: StudioFormState
    form_complete: bool


# ── 值应用 ────────────────────────────────────────────────────

def _apply_value(state: StudioFormState, section_id: str, field_id: str, value) -> bool:
    """把提取的值应用到 form_state。返回是否成功。"""
    field = FIELD_BY_ID.get(field_id)
    if field is None:
        return False
    sec = state.sections.get(section_id)
    if sec is None:
        return False
    current = sec.fields.get(field_id)
    if current is None:
        return False
    try:
        if current.type == 'text':
            current.value = str(value) if value is not None else ''
        elif current.type == 'choice-single':
            current.value = value if isinstance(value, str) else None
        elif current.type == 'choice-multi':
            current.value = list(value) if isinstance(value, list) else []
        elif current.type == 'dimension':
            current.value = {k: str(v) for k, v in value.items()} if isinstance(value, dict) else {}
        elif current.type == 'image':
            current.value = list(value) if isinstance(value, list) else []
        elif current.type == 'table':
            current.value = list(value) if isinstance(value, list) else []
        return True
    except Exception:
        return False


# ── Prompt 构造 ───────────────────────────────────────────────

def _collectable_fields(state: StudioFormState) -> str:
    """生成「当前可填字段说明」，给 JSON 提取步骤用。

    只列当前章节 + 下一章节的字段，避免 prompt 过长。
    """
    lines = []
    current_sec = flow.current_section_for_agent(state)
    # 列当前章节所有可见字段
    for sec_id in [current_sec]:
        sec_def = SECTION_BY_ID[sec_id]
        sec_state = state.sections[sec_id]
        for f in sec_def.fields:
            if not flow.is_field_visible(f, sec_state):
                continue
            opts = ''
            if f.options:
                opts = '  可选: ' + ', '.join(f'{o.value}={o.label}' for o in f.options)
            dims = ''
            if f.dims:
                dims = f'  维度{f.dims}'
            req = '必填' if f.required else '选填'
            lines.append(f'- {sec_id}.{f.id}: {f.label}({f.type},{req}){opts}{dims}')
    return '\n'.join(lines)


def _build_extraction_prompt(state: StudioFormState) -> str:
    """步骤 1：JSON 提取的 system prompt。"""
    fields_desc = _collectable_fields(state)
    return f"""你是信息提取器。从用户消息中提取直播间搭建需求信息，填入对应表单字段。

当前可填字段：
{fields_desc}

规则：
- 只输出用户明确提到的字段，不要猜测
- choice-single 字段填选项的 value（英文），不是 label（中文）
- choice-multi 字段填 value 数组
- text 字段填用户原话
- dimension 字段填 {{维度名: 值}} 对象
- 如果用户说"没有直播间"之类，在 skip_sections 里加上对应章节 id（如 status）
- 用户消息没有可提取信息时，updates 和 skip_sections 都留空

输出 JSON 格式：
{{
  "updates": [{{"section_id": "章节id", "field_id": "字段id", "value": 值}}],
  "skip_sections": ["章节id"]
}}"""


def _build_reply_prompt(state: StudioFormState) -> str:
    """步骤 2：生成自然回复的 system prompt。"""
    progress = flow.section_progress(state)
    filled, total = flow.overall_progress(state)
    next_field_info = flow.next_unfilled_field(state)

    progress_lines = []
    for p in progress:
        if p['status'] == 'skipped':
            continue
        mark = '✓' if p['complete'] else f"{p['filled']}/{p['total']}"
        progress_lines.append(f"  {p['title']} {mark}")
    progress_text = '\n'.join(progress_lines)

    if next_field_info is None:
        next_hint = '所有必填信息已采集完毕，请做最终总结确认。'
    else:
        sec_id, field = next_field_info
        opts = ''
        if field.options:
            opts = '（选项：' + '、'.join(o.label for o in field.options) + '）'
        next_hint = f'下一个该问：【{SECTION_BY_ID[sec_id].title}】{field.label}{opts}'

    return f"""你是直播间搭建顾问。用户刚回答了问题，信息已记录。

{AGENT_GUIDE}

当前进度（{filled}/{total}）：
{progress_text}

{next_hint}

请用自然亲切的语气：
1. 用一句话确认刚才收到的信息（不要逐条复述）
2. 然后问下一个该问的问题
保持 2-3 句话，像真人客服。"""


# ── 对话主循环 ────────────────────────────────────────────────

def run_turn(
    state: StudioFormState,
    user_message: str,
    history: list[dict] | None = None,
) -> TurnResult:
    """单轮对话：JSON 提取填值 → 生成自然回复。"""
    client = get_client()
    events: list[ToolEvent] = []

    # 步骤 1：JSON 提取
    extract_messages = [
        {'role': 'system', 'content': _build_extraction_prompt(state)},
        {'role': 'user', 'content': user_message},
    ]
    if history:
        extract_messages[1:1] = history[-4:]  # 带少量上下文帮助理解

    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=extract_messages,
        response_format={'type': 'json_object'},
        max_tokens=1500,
    )
    try:
        extracted = json.loads(resp.choices[0].message.content or '{}')
    except json.JSONDecodeError:
        extracted = {}

    # 应用提取结果
    for upd in extracted.get('updates', []):
        ok = _apply_value(state, upd['section_id'], upd['field_id'], upd.get('value'))
        if ok:
            events.append(ToolEvent(
                kind='fill',
                section_id=upd['section_id'],
                field_id=upd['field_id'],
                value=upd.get('value'),
            ))
    for sid in extracted.get('skip_sections', []):
        flow.skip_section(state, sid)
        events.append(ToolEvent(kind='skip', section_id=sid))

    # 步骤 2：生成自然回复
    skip_note = ''
    if any(e.kind == 'skip' for e in events):
        skipped_titles = [SECTION_BY_ID[e.section_id].title for e in events if e.kind == 'skip']
        skip_note = f'\n注意：用户跳过了以下章节（{", ".join(skipped_titles)}），请在回复中确认跳过，然后继续问下一个该问的问题。'

    reply_messages = [
        {'role': 'system', 'content': _build_reply_prompt(state) + skip_note},
    ]
    if history:
        reply_messages.extend(history[-6:])
    reply_messages.append({'role': 'user', 'content': user_message})

    resp2 = client.chat.completions.create(
        model=LLM_MODEL,
        messages=reply_messages,
        max_tokens=300,
    )
    reply = (resp2.choices[0].message.content or '').strip()

    return TurnResult(
        reply=reply,
        tool_events=events,
        state=state,
        form_complete=flow.form_complete(state),
    )


def run_turn_stream(
    state: StudioFormState,
    user_message: str,
    history: list[dict] | None = None,
):
    """流式版 run_turn。

    生成事件序列：
    - ('events', list[ToolEvent])   先 yield 所有 tool 事件（填值/跳过）
    - ('token', str)                逐个 yield 回复 token
    - ('done', TurnResult)          最后 yield 完整结果

    提取步骤同步完成（要拿到完整 JSON 才能填值），回复步骤流式。
    """
    client = get_client()
    events: list[ToolEvent] = []

    # 步骤 1：JSON 提取（同步）
    extract_messages = [
        {'role': 'system', 'content': _build_extraction_prompt(state)},
    ]
    if history:
        extract_messages.extend(history[-4:])
    extract_messages.append({'role': 'user', 'content': user_message})

    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=extract_messages,
        response_format={'type': 'json_object'},
        max_tokens=1500,
    )
    try:
        extracted = json.loads(resp.choices[0].message.content or '{}')
    except json.JSONDecodeError:
        extracted = {}

    for upd in extracted.get('updates', []):
        ok = _apply_value(state, upd['section_id'], upd['field_id'], upd.get('value'))
        if ok:
            events.append(ToolEvent(
                kind='fill',
                section_id=upd['section_id'],
                field_id=upd['field_id'],
                value=upd.get('value'),
            ))
    for sid in extracted.get('skip_sections', []):
        flow.skip_section(state, sid)
        events.append(ToolEvent(kind='skip', section_id=sid))

    # 先发事件
    yield ('events', events)

    # 步骤 2：流式生成回复
    skip_note = ''
    if any(e.kind == 'skip' for e in events):
        skipped_titles = [SECTION_BY_ID[e.section_id].title for e in events if e.kind == 'skip']
        skip_note = f'\n注意：用户跳过了以下章节（{", ".join(skipped_titles)}），请在回复中确认跳过，然后继续问下一个该问的问题。'

    reply_messages = [
        {'role': 'system', 'content': _build_reply_prompt(state) + skip_note},
    ]
    if history:
        reply_messages.extend(history[-6:])
    reply_messages.append({'role': 'user', 'content': user_message})

    full_reply = []
    stream = client.chat.completions.create(
        model=LLM_MODEL,
        messages=reply_messages,
        max_tokens=300,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            full_reply.append(delta)
            yield ('token', delta)

    yield ('done', TurnResult(
        reply=''.join(full_reply).strip(),
        tool_events=events,
        state=state,
        form_complete=flow.form_complete(state),
    ))


def initial_greeting(state: StudioFormState) -> str:
    """生成开场白。"""
    client = get_client()
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {'role': 'system', 'content': _build_reply_prompt(state) +
             '\n这是会话开始，请简短自我介绍并问第一个问题。'},
            {'role': 'user', 'content': '你好'},
        ],
        max_tokens=200,
    )
    return (resp.choices[0].message.content or '').strip()
