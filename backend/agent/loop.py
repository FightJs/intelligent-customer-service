"""Agent loop 引擎 — 标准 tool use 循环。

用户消息 → messages.create → 模型返回 tool_use 或 end_turn
  → tool_use 则执行 tool，结果回传，再 create
  → end_turn 则取文本回复，结束
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from anthropic import Anthropic
from agent.llm import (
    get_client,
    LLM_MODEL,
    LLM_TEMPERATURE,
)
from agent.tools import TOOL_DEFS, execute_tool, ToolEvent, _apply_one
from agent import flow
from survey.models import StudioFormState
from survey.schema_def import SECTION_BY_ID, FIELD_BY_ID, SECTIONS, SECTION_ORDER, AGENT_GUIDE

MAX_ITERATIONS = 5
RECENT_MESSAGE_LIMIT = 12

FILL_FIELDS_TOOL = next(
    tool
    for tool in TOOL_DEFS
    if tool['name'] == 'fill_fields'
)

@dataclass
class AgentResult:
    reply: str
    tool_events: list[ToolEvent]
    state: StudioFormState
    form_complete: bool
    suggestions: list[dict] = field(default_factory=list)


def _summarize_history(
    client: Anthropic,
    history: list[dict],
) -> str:
    """把较早的对话压缩成供 LLM 使用的记忆摘要。"""
    if not history:
        return ''

    history_lines: list[str] = []

    for message in history:
        content = message.get('content')

        if not isinstance(content, str):
            continue

        speaker = (
            '客户'
            if message.get('role') == 'user'
            else '客服'
        )

        history_lines.append(
            f'{speaker}：{content}'
        )

    transcript = '\n'.join(history_lines)

    response = client.messages.create(
        model=LLM_MODEL,
        max_tokens=300,
        temperature=LLM_TEMPERATURE,
        thinking={'type': 'disabled'},
        system=(
            '你是对话记忆整理器。'
            '请总结客户已经明确提供的信息、'
            '客户对旧答案的修改、'
            '仍未解决的问题和重要上下文。'
            '新答案与旧答案冲突时，'
            '以用户最新明确确认的答案为准。'
            '不要补充或猜测用户没有说过的信息。'
            '摘要控制在 300 字以内。'
        ),
        messages=[{
            'role': 'user',
            'content': transcript,
        }],
    )

    text_parts = [
        block.text
        for block in response.content
        if block.type == 'text'
    ]

    return ''.join(text_parts).strip()


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


def _build_system_prompt(state: StudioFormState,history_summary: str = '',) -> str:
    """构造 system prompt，含字段说明 + 当前进度 + SOP。"""
    progress = flow.section_progress(state)
    filled, total = flow.overall_progress(state)
    nxt = flow.next_unfilled_field(state)


    summary_text = (
        history_summary
        if history_summary
        else '（暂无）'
    )

        # 必填字段主动推进，选填字段只在用户主动提及时记录
    required_field_lines: list[str] = []
    optional_field_lines: list[str] = []

    for sec_id in SECTION_ORDER:
        sec_def = SECTION_BY_ID[sec_id]
        sec_state = state.sections[sec_id]

        if sec_state.status == 'skipped':
            continue

        for fdef in sec_def.fields:
            if not flow.is_field_visible(fdef, sec_state):
                continue

            value = sec_state.fields.get(fdef.id)
            if value is not None and not flow.value_is_empty(value):
                continue

            field_required = flow.is_field_required(state,sec_id,fdef,)

            options_text = ''
            if fdef.options:
                options_text = '  可选: ' + ', '.join(
                    f'{option.value}={option.label}'
                    for option in fdef.options
                )

            dimensions_text = ''
            if fdef.dims:
                dimensions_text = f'  维度{fdef.dims}'

            columns_text = ''
            if fdef.columns:
                columns_text = '  列: ' + ', '.join(
                    f'{column.id}={column.label}'
                    for column in fdef.columns
                )

            field_type = (
                '必填'
                if field_required
                else '选填'
            )

            field_line = (
                f'- {sec_id}.{fdef.id}: {fdef.label}'
                f'({fdef.type},{field_type})'
                f'{options_text}'
                f'{dimensions_text}'
                f'{columns_text}'
            )

            if field_required:
                required_field_lines.append(field_line)
            else:
                optional_field_lines.append(field_line)

    required_fields_text = (
        '\n'.join(required_field_lines)
        if required_field_lines
        else '（所有必填字段已填）'
    )

    optional_fields_text = (
        '\n'.join(optional_field_lines)
        if optional_field_lines
        else '（暂无）'
    )


    # 已采集字段值（治"重复问"：让 LLM 看到自己已经抓到了什么具体内容）
    collected_lines = []
    for sec_id in SECTION_ORDER:
        sec_def = SECTION_BY_ID[sec_id]
        sec_state = state.sections[sec_id]
        if sec_state.status == 'skipped':
            continue
        for fdef in sec_def.fields:
            v = sec_state.fields.get(fdef.id)
            if v is None or flow.value_is_empty(v):
                continue
            collected_lines.append(f'- {sec_id}.{fdef.id}: {flow.value_to_text(v, fdef)}')
    collected_text = '\n'.join(collected_lines) if collected_lines else '（暂无）'

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

【较早对话摘要】
{summary_text}

【采集纪律】
1. 信息成功写入表单优先于减少重复。已成功写入且无冲突的字段避免重复询问；信息不确定、新旧答案冲突或工具写入失败时，允许再次确认
2. 用户本轮回答涉及多个字段时，必须一次性 fill_fields 全部
3. 优先按【下一个该问】推进；只有信息不确定、用户主动修改或工具写入失败时，才回到相关字段确认
4. 选填字段只在用户主动提供时记录，禁止主动询问选填字段
5. 用户回答“无”“没有”“不用补充”时，禁止再次询问“还有什么需要补充”；仍有必填字段就继续【下一个该问】，全部完成就告知可以生成交付物
6. 若 fill_fields 返回失败明细，根据原因修正后最多重试一次


【已采集】
{collected_text}

当前需要推进的必填字段：
{required_fields_text}

用户主动提及时可记录的选填字段（禁止主动询问）：
{optional_fields_text}

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

        # 历史拆分为“较早摘要 + 近期原文”。
    full_history = history or []

    older_history = full_history[
        :-RECENT_MESSAGE_LIMIT
    ]
    recent_history = full_history[
        -RECENT_MESSAGE_LIMIT:
    ]

    history_summary = _summarize_history(
        client,
        older_history,
    )

    # Anthropic API 要求第一条消息必须是 user。
    messages: list[dict] = []
    trimmed = list(recent_history)

    while (
        trimmed
        and trimmed[0].get('role') != 'user'
    ):
        trimmed = trimmed[1:]

    messages.extend(trimmed)
    messages.append({
        'role': 'user',
        'content': user_message,
    })

    for iteration in range(MAX_ITERATIONS):
        # 每轮刷新 system prompt（state 可能变了）
        is_capture_turn = iteration == 0

        request_tools = (
            [FILL_FIELDS_TOOL]
            if is_capture_turn
            else TOOL_DEFS
        )

        request_tool_choice = (
            {
                'type': 'tool',
                'name': 'fill_fields',
            }
            if is_capture_turn
            else {
                'type': 'auto',
            }
        )
        
        resp = client.messages.create(
            model=LLM_MODEL,
            max_tokens=800,
            temperature=LLM_TEMPERATURE,
            thinking={'type': 'disabled'},
                        system=_build_system_prompt(
                state,
                history_summary,
            ),
            tools=request_tools,
            tool_choice=request_tool_choice,
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

        if is_capture_turn:
            has_fill_fields = any(
                block.name == 'fill_fields'
                for block in tool_use_blocks
            )

            if not has_fill_fields:
                continue

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
                    clean_fid = (
                        raw_fid.split('.')[-1]
                        if '.' in raw_fid
                        else raw_fid
                    )

                    section_id = upd.get('section_id', '')
                    section_state = state.sections.get(section_id)
                    if section_state is None:
                        continue

                    stored_field = section_state.fields.get(clean_fid)
                    if stored_field is None:
                        continue

                    events.append(ToolEvent(
                        kind='fill',
                        section_id=section_id,
                        field_id=clean_fid,
                        value=stored_field.value,
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

    # 返回前重算章节 status（治"全 pending"显示问题）
    flow.recompute_section_status(state)

    return AgentResult(
        reply=reply,
        tool_events=events,
        state=state,
        form_complete=flow.form_complete(state),
        suggestions=_build_suggestions(state),
    )
