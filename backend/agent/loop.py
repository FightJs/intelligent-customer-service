"""Agent loop 引擎 — 标准 tool use 循环。

用户消息 → messages.create → 模型返回 tool_use 或 end_turn
  → tool_use 则执行 tool，结果回传，再 create
  → end_turn 则取文本回复，结束
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from anthropic import Anthropic
from agent.llm import get_client, LLM_MODEL
from agent.tools import TOOL_DEFS, execute_tool, ToolEvent, _apply_one
from agent import flow
from survey.models import StudioFormState
from survey.schema_def import SECTION_BY_ID, FIELD_BY_ID, SECTIONS, SECTION_ORDER, AGENT_GUIDE

MAX_ITERATIONS = 5


@dataclass
class AgentResult:
    reply: str
    tool_events: list[ToolEvent]
    state: StudioFormState
    form_complete: bool
    suggestions: list[dict] = field(default_factory=list)


def _build_suggestions(state: StudioFormState) -> list[dict]:
    """根据下一个未填字段，构造 chip 选项（仅 choice 类字段有 options）。"""
    nxt = flow.next_unfilled_field(state)
    if not nxt:
        return []
    sec_id, fdef = nxt
    if not fdef.options:
        return []
    return [{
        'section_id': sec_id,
        'field_id': fdef.id,
        'options': [{'value': o.value, 'label': o.label} for o in fdef.options],
    }]


def _build_system_prompt(state: StudioFormState) -> str:
    """构造 system prompt，含字段说明 + 当前进度 + SOP。"""
    progress = flow.section_progress(state)
    filled, total = flow.overall_progress(state)
    nxt = flow.next_unfilled_field(state)

    # 可填字段说明
    field_lines = []
    for sec_id in SECTION_ORDER:
        sec_def = SECTION_BY_ID[sec_id]
        sec_state = state.sections[sec_id]
        if sec_state.status == 'skipped':
            continue
        f, t = flow.filled_required_count(sec_def, sec_state)
        if t > 0 and f >= t:
            continue
        for fdef in sec_def.fields:
            if not flow.is_field_visible(fdef, sec_state):
                continue
            v = sec_state.fields.get(fdef.id)
            if v is not None and not flow.value_is_empty(v):
                continue
            opts = ''
            if fdef.options:
                opts = '  可选: ' + ', '.join(f'{o.value}={o.label}' for o in fdef.options)
            dims = f'  维度{fdef.dims}' if fdef.dims else ''
            req = '必填' if fdef.required else '选填'
            field_lines.append(f'- {sec_id}.{fdef.id}: {fdef.label}({fdef.type},{req}){opts}{dims}')
    fields_text = '\n'.join(field_lines) if field_lines else '（所有字段已填）'

    # 进度
    progress_lines = []
    for p in progress:
        if p['status'] == 'skipped':
            continue
        mark = '✓' if p['complete'] else f"{p['filled']}/{p['total']}"
        progress_lines.append(f"  {p['title']} {mark}")

    next_hint = '所有必填信息已采集完毕，请总结确认。'
    if nxt:
        sec_id, field = nxt
        next_hint = f'下一个该问：【{SECTION_BY_ID[sec_id].title}】{field.label}'

    return f"""你是直播间搭建顾问，负责通过对话收集客户搭建直播间的需求。

你可以调用以下工具：
- fill_fields：把用户说的信息填入表单（一句话含多个字段就一次填多个）
- skip_section：用户不具备某条件时跳过章节（如"没有直播间"→skip status）
- get_progress：查看采集进度和下一个该问的字段
- set_current_section：用户跳着回答或回头改时切换章节
- generate_deliverable：采集完成或用户要求时生成交付物

工作方式：
1. 用户消息含信息时，调 fill_fields 填入
2. 需要知道下一步问什么时，调 get_progress
3. 信息足够时，自然地确认并问下一个问题
4. 所有必填信息齐了，告知用户可生成交付物

{AGENT_GUIDE}

当前可填字段：
{fields_text}

当前进度（{filled}/{total}）：
{chr(10).join(progress_lines)}

{next_hint}

回复规则：
- 像真人客服，亲切自然，2-3 句话
- 不要机械照念字段名
- 用户没说清的信息不要猜"""


def run_agent(
    state: StudioFormState,
    user_message: str,
    history: list[dict] | None = None,
) -> AgentResult:
    """跑 agent loop。"""
    client = get_client()
    events: list[ToolEvent] = []

    system_prompt = _build_system_prompt(state)

    # 构造初始 messages（history 限 6 条）
    # Anthropic API 要求第一条 message 的 role 必须是 user，
    # 前端传来的 history 可能以 assistant（开场白）开头，需丢弃开头的非 user 消息
    messages: list[dict] = []
    if history:
        trimmed = history[-6:]
        while trimmed and trimmed[0].get('role') != 'user':
            trimmed = trimmed[1:]
        messages.extend(trimmed)
    messages.append({'role': 'user', 'content': user_message})

    for iteration in range(MAX_ITERATIONS):
        # 每轮刷新 system prompt（state 可能变了）
        resp = client.messages.create(
            model=LLM_MODEL,
            max_tokens=800,
            thinking={'type': 'disabled'},
            system=_build_system_prompt(state),
            tools=TOOL_DEFS,
            messages=messages,
        )

        # 处理 content blocks
        text_parts = []
        tool_use_blocks = []
        for block in resp.content:
            if block.type == 'text':
                text_parts.append(block.text)
            elif block.type == 'tool_use':
                tool_use_blocks.append(block)

        if resp.stop_reason != 'tool_use' or not tool_use_blocks:
            # end_turn，取文本回复
            reply = ''.join(text_parts).strip()
            break

        # 执行 tools，收集 assistant 消息 + tool_result
        messages.append({'role': 'assistant', 'content': resp.content})
        tool_results = []
        for tb in tool_use_blocks:
            try:
                result_str = execute_tool(tb.name, tb.input, state)
            except Exception as exc:
                result_str = f'[error] tool {tb.name} 执行失败：{exc}'
            # 记录事件
            if tb.name == 'fill_fields':
                for upd in tb.input.get('updates', []):
                    raw_fid = upd.get('field_id', '')
                    clean_fid = raw_fid.split('.')[-1] if '.' in raw_fid else raw_fid
                    events.append(ToolEvent(
                        kind='fill', section_id=upd['section_id'],
                        field_id=clean_fid, value=upd.get('value'),
                    ))
            elif tb.name == 'skip_section':
                events.append(ToolEvent(kind='skip', section_id=tb.input['section_id']))
            elif tb.name == 'generate_deliverable':
                events.append(ToolEvent(
                    kind='deliverable', section_id='',
                    value=tb.input.get('doc_type'),
                ))
            tool_results.append({
                'type': 'tool_result',
                'tool_use_id': tb.id,
                'content': result_str,
            })
        messages.append({'role': 'user', 'content': tool_results})
    else:
        # 循环用尽，兜底
        reply = '信息已记录，还有什么需要补充的吗？'

    return AgentResult(
        reply=reply,
        tool_events=events,
        state=state,
        form_complete=flow.form_complete(state),
        suggestions=_build_suggestions(state),
    )
