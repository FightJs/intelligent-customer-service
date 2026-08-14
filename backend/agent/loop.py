"""Agent loop 引擎 — 标准 tool use 循环。

用户消息 → messages.create → 模型返回 tool_use 或 end_turn
  → tool_use 则执行 tool，结果回传，再 create
  → end_turn 则取文本回复，结束
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator, Literal

from anthropic import Anthropic, AsyncAnthropic
from agent.llm import (
    get_client,
    get_async_client,
    LLM_MODEL,
    LLM_TEMPERATURE,
)
from agent.tools import TOOL_DEFS, execute_tool, ToolEvent
from agent import flow
from store.uploads import SavedImage
from survey.models import StudioFormState
from survey.schema_def import (
    AGENT_GUIDE,
    FIELD_BY_ID,
    SECTION_BY_ID,
    SECTIONS,
    SECTION_ORDER,
    FieldDef,
)

MAX_ITERATIONS = 5
RECENT_MESSAGE_LIMIT = 12

logger = logging.getLogger(__name__)

FILL_ONLY_TOOLS = [
    tool for tool in TOOL_DEFS
    if tool['name'] == 'fill_fields'
]

SUGGESTION_FIELD_PREFIXES = (
    '目标客群',
    '客户',
    '商品',
    '品牌',
    '直播间',
    '场地',
    '预算',
    '现有',
    '需求与',
)

SUGGESTION_GENERIC_WORDS = {
    '目标',
    '客户',
    '商品',
    '品牌',
    '场地',
    '预算',
    '现有',
    '需求',
}

@dataclass
class AgentResult:
    reply: str
    tool_events: list[ToolEvent]
    state: StudioFormState
    form_complete: bool
    suggestions: list[dict] = field(default_factory=list)


@dataclass
class AgentStreamDelta:
    text: str


@dataclass
class AgentStreamStatus:
    phase: Literal['generating', 'tool_call']
    message: str


@dataclass
class AgentStreamToolEvent:
    event: ToolEvent


@dataclass
class AgentStreamResult:
    reply: str
    tool_events: list[ToolEvent]
    state: StudioFormState
    form_complete: bool
    suggestions: list[dict] = field(default_factory=list)


def _extract_text(content: str | list[dict]) -> str:
    """从 content（字符串或数组）中提取纯文本。图片用 [图片] 占位。"""
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, dict):
            if block.get('type') == 'text':
                parts.append(block.get('text', ''))
            elif block.get('type') == 'image':
                parts.append('[图片]')
    return ''.join(parts)


def _build_user_content(message: str, images: list[SavedImage] | None) -> str | list[dict]:
    """构造 user message 的 content。

    images 为已落盘的 SavedImage 列表：文本里注入 [图片N id=...] 标记
    （供 LLM 在 fill_fields 里引用），图片本体送缩放后的文件内容。
    """
    if not images:
        return message or ''
    markers = ' '.join(
        f'[图片{i} id={img.id}]'
        for i, img in enumerate(images, 1)
    )
    note = (
        f'（用户上传了 {len(images)} 张图片。请识别图片内容，'
        '并用 fill_fields 把对应 id 填到合适的图片字段，'
        'value 传 id 字符串数组）'
    )
    text = f'{markers}\n{note}\n{message}' if message else f'{markers}\n{note}'
    content: list[dict] = [{'type': 'text', 'text': text}]
    for img in images:
        data_str = base64.b64encode(img.path.read_bytes()).decode('ascii')
        content.append({
            'type': 'image',
            'source': {'type': 'base64', 'media_type': img.mime, 'data': data_str},
        })
    return content


_EXTRACT_NUDGE = (
    '（系统检查：请检查客户上一条消息，如有尚未记录的需求信息或图片，'
    '调用 fill_fields 补记；图片 value 用消息里 [图片N id=...] 的 id。'
    '确实没有可记录的，传 updates=[]。）'
)


def _extraction_messages(
    messages: list[dict],
    reply: str,
) -> list[dict]:
    """构造抽取补轮的消息：对话现场 + 刚生成的回复 + 系统检查指令。"""
    extract_messages = [*messages]
    if reply:
        extract_messages.append({'role': 'assistant', 'content': reply})
    extract_messages.append({'role': 'user', 'content': _EXTRACT_NUDGE})
    return extract_messages


def _run_extraction_pass(
    client: Anthropic,
    state: StudioFormState,
    messages: list[dict],
    reply: str,
    history_summary: str,
    events: list[ToolEvent],
) -> None:
    """漏采保险：整轮没调过 fill_fields 时补一轮抽取（模型可能只顾回复忘了填表）。

    抽取失败不影响已生成的回复，记日志即可。
    """
    try:
        resp = client.messages.create(
            model=LLM_MODEL,
            max_tokens=800,
            temperature=LLM_TEMPERATURE,
            thinking={'type': 'disabled'},
            system=_build_system_prompt(state, history_summary),
            tools=FILL_ONLY_TOOLS,
            tool_choice={'type': 'auto'},
            messages=_extraction_messages(messages, reply),
        )
    except Exception:
        logger.warning('extraction pass failed', exc_info=True)
        return
    for block in resp.content:
        if block.type == 'tool_use' and block.name == 'fill_fields':
            execute_tool('fill_fields', block.input, state)
            events.extend(
                _tool_events_for_block('fill_fields', block.input, state)
            )


async def _run_extraction_pass_async(
    client: AsyncAnthropic,
    state: StudioFormState,
    messages: list[dict],
    reply: str,
    history_summary: str,
) -> list[ToolEvent]:
    """_run_extraction_pass 的异步版（流式路径用），返回产生的事件。"""
    try:
        resp = await client.messages.create(
            model=LLM_MODEL,
            max_tokens=800,
            temperature=LLM_TEMPERATURE,
            thinking={'type': 'disabled'},
            system=_build_system_prompt(state, history_summary),
            tools=FILL_ONLY_TOOLS,
            tool_choice={'type': 'auto'},
            messages=_extraction_messages(messages, reply),
        )
    except Exception:
        logger.warning('extraction pass failed', exc_info=True)
        return []
    events: list[ToolEvent] = []
    for block in resp.content:
        if block.type == 'tool_use' and block.name == 'fill_fields':
            execute_tool('fill_fields', block.input, state)
            events.extend(
                _tool_events_for_block('fill_fields', block.input, state)
            )
    return events


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
        text = _extract_text(content) if content else ''
        if not text or text == '[图片]':
            continue

        speaker = (
            '客户'
            if message.get('role') == 'user'
            else '客服'
        )

        history_lines.append(
            f'{speaker}：{text}'
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


async def _summarize_history_async(
    client: AsyncAnthropic,
    history: list[dict],
) -> str:
    """异步压缩较早历史，避免阻塞流式事件循环。"""
    if not history:
        return ''

    history_lines = []
    for message in history:
        content = message.get('content')
        text = _extract_text(content) if content else ''
        if not text or text == '[图片]':
            continue
        speaker = '客户' if message.get('role') == 'user' else '客服'
        history_lines.append(f'{speaker}：{text}')

    if not history_lines:
        return ''

    response = await client.messages.create(
        model=LLM_MODEL,
        max_tokens=300,
        temperature=LLM_TEMPERATURE,
        thinking={'type': 'disabled'},
        system=(
            '你是对话记忆整理器。'
            '请总结客户已经明确提供的信息、客户对旧答案的修改、'
            '仍未解决的问题和重要上下文。不要补充或猜测。摘要控制在 300 字以内。'
        ),
        messages=[{'role': 'user', 'content': '\n'.join(history_lines)}],
    )
    return ''.join(
        block.text
        for block in response.content
        if block.type == 'text'
    ).strip()


def _suggestion_matches_reply(
    field_def: FieldDef,
    reply: str,
) -> bool:
    """判断客服回复是否确实在询问候选字段。"""
    if not reply:
        return False

    field_tail = field_def.label

    for prefix in SUGGESTION_FIELD_PREFIXES:
        if field_tail.startswith(prefix):
            field_tail = field_tail[len(prefix):]
            break

    keywords = (
        field_def.label,
        field_tail,
        field_def.label[:2],
    )

    if any(
        keyword in reply
        for keyword in keywords
        if (
            len(keyword) > 1
            and keyword
            not in SUGGESTION_GENERIC_WORDS
        )
    ):
        return True

    mentioned_options = [
        option
        for option in (field_def.options or [])
        if (
            len(option.label) > 1
            and option.label in reply
        )
    ]

    return len(mentioned_options) >= 2


def _build_suggestions(
    state: StudioFormState,
    reply: str,
) -> list[dict]:
    """仅为回复实际询问的 choice 字段返回快捷回答。"""
    next_field = flow.next_unfilled_field(state)

    if not next_field:
        return []

    section_id, field_def = next_field

    if not field_def.options:
        return []

    if not _suggestion_matches_reply(
        field_def,
        reply,
    ):
        return []

    return [{
        'section_id': section_id,
        'field_id': field_def.id,
        'options': [
            {
                'value': option.value,
                'label': option.label,
            }
            for option in field_def.options
        ],
    }]


def _build_system_prompt(state: StudioFormState,history_summary: str = '',) -> str:
    """构造 system prompt，含字段说明 + 当前进度 + SOP。"""
    progress = flow.section_progress(state)
    filled, total = flow.overall_progress(state)
    batch = flow.next_field_batch(state, n=3)


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
                dimension_example = {
                    dimension: '值'
                    for dimension in fdef.dims
                }

                if (
                    sec_id == 'host'
                    and fdef.id == 'height'
                ):
                    dimension_example = {
                        '女主播': '165',
                        '男主播': '175',
                    }

                example_text = json.dumps(
                    dimension_example,
                    ensure_ascii=False,
                )

                dimensions_text = (
                    f'  维度{fdef.dims}；'
                    'value 必须传对象，'
                    '可只传本轮提到的维度，'
                    f'例如 {example_text}'
                )

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

    if state.mode == 'quick':
        completion_rule = (
            '快速体验的必填信息齐了，'
            '提醒用户查看右上角'
            '客户需求表；'
            '说明快速体验已经完成，'
            '登录或注册后可以进行'
            '完整采集和发送订单。'
        )

        topic_hint = (
            '快速体验所需信息'
            '已采集完毕。'
            '请提醒用户查看右上角'
            '客户需求表；'
            '如需完整需求采集和'
            '发送订单，请登录或注册'
            '正式账号。'
        )
    else:
        completion_rule = (
            '所有必填信息齐了，'
            '提醒用户查看右上角'
            '客户需求表，'
            '确认无误后点击'
            '“发送订单”。'
        )

        topic_hint = (
            '所有必填信息已采集完毕。'
            '请告知用户：右上角'
            '客户需求表会实时展示'
            '当前信息，'
            '确认内容无误后，'
            '可点击右侧“发送订单”。'
            '不要再询问用户需要'
            '生成哪种文件。'
        )

    if batch:
        topics_text = '；'.join(
            f'【{SECTION_BY_ID[sec_id].title}】{f.label}'
            for sec_id, f in batch
        )
        topic_hint = (
            '接下来还需要了解'
            f'（话题参考，不必逐个盘问）：'
            f'{topics_text}'
        )

    return f"""你是「小搭」，一位经验丰富的直播间搭建顾问。你正在和客户聊天，了解他们的需求，顺手把信息记进表单。

你可以调用以下工具：
- fill_fields：把用户说的信息填入表单（一句话含多个字段就一次填多个）
- skip_section：用户不具备某条件时跳过章节（如"没有直播间"→skip status）
- get_progress：查看采集进度和接下来还需要了解什么
- set_current_section：用户跳着回答或回头改时切换章节

工作方式：
1. 用户消息里有新信息（品牌、品类、预算、场地、风格、图片等任何需求相关内容）时，必须在回复的同时调 fill_fields 记录——先调工具，回复文本紧随其后，漏填等于信息丢失；没有新信息（纯闲聊、提问、确认）就不用调
2. 回复时先接住用户的话（回答问题、回应情绪、承接闲聊），再自然地带出 1~2 个相关问题
3. 围绕当前话题聊，【待了解话题】只是参考，不要按表单顺序逐项盘问；用户跑题时先回应，再温和地带回来
4. {completion_rule}
5. 信息采集完成不代表会话关闭；用户仍可以继续补充或修改信息
6. 禁止询问用户需要 Markdown、Excel 或 Word 中的哪一种
7. 禁止声称订单已经发送；只有用户点击“发送订单”才算发送
8. 回复文本要么单独出，要么只和 fill_fields 一起出；get_progress、set_current_section 这类查询/切换工具要单独调用（不带回复文本，等结果回来再回复），避免用户看到两段重复的回复

{AGENT_GUIDE}

【较早对话摘要】
{summary_text}

【采集纪律】
1. 信息成功写入表单优先于减少重复。已成功写入且无冲突的字段避免重复询问；信息不确定、新旧答案冲突或工具写入失败时，允许再次确认
2. 用户本轮回答涉及多个字段时，必须一次性 fill_fields 全部
3. 已填过的信息用口语化复述确认（如"记下了，你们主推口红"），不要念字段名
4. 选填字段只在用户主动提供时记录，禁止主动询问选填字段
5. 用户回答“无”“没有”“不用补充”时，禁止再次询问“还有什么需要补充”；仍有必填字段就换个话题继续聊，全部完成后按当前模式的完成指引回复
6. 若 fill_fields 返回失败明细，根据原因修正后最多重试一次


【已采集】
{collected_text}

当前需要推进的必填字段：
{required_fields_text}

用户主动提及时可记录的选填字段（禁止主动询问）：
{optional_fields_text}

当前进度（{filled}/{total}）：
{chr(10).join(progress_lines)}

【待了解话题】
{topic_hint}

回复规则：
- 像朋友一样聊，亲切自然，每轮 2-3 句话
- 每轮最多问 1~2 个问题，问题要融进对话里，不要罗列、不要编号
- 不要照念字段名。说"主要想吸引哪个年龄段的粉丝呀"，不说"请问目标客群年龄段"
- 用户没说清的信息不要猜

示例：
- 用户："我们是做美妆的" → 好："美妆类目很上镜！你们主推哪类产品？客单价大概在什么区间？" 坏："已记录品类。请问价格带？"
- 用户："你好" → 好："你好呀！欢迎来到直播间搭建咨询～怎么称呼你的品牌？" 坏："请问客户品牌名。"
- 用户："哈哈我预算还没想好" → 好："不急～大概想做普通一点的还是专业级的？我好按档位帮你估。" 坏："请选择预算档位：1万以下/1-3万/3-5万。"
"""


def run_agent(
    state: StudioFormState,
    user_message: str,
    history: list[dict] | None = None,
    images: list[SavedImage] | None = None,
) -> AgentResult:
    """跑 agent loop。images 为已落盘的 SavedImage 列表，有图片时送多模态模型。"""
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
        'content': _build_user_content(user_message, images),
    })

    reply = ''
    filled = False  # 本轮是否调过 fill_fields（updates=[] 也算，说明模型判断过）
    for _ in range(MAX_ITERATIONS):
        # 每轮刷新 system prompt（state 可能变了）
        resp = client.messages.create(
            model=LLM_MODEL,
            max_tokens=800,
            temperature=LLM_TEMPERATURE,
            thinking={'type': 'disabled'},
                        system=_build_system_prompt(
                state,
                history_summary,
            ),
            tools=TOOL_DEFS,
            tool_choice={'type': 'auto'},
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

        # 执行 tools，收集结果
        tool_results = []
        all_ok = True
        only_fill = all(
            tb.name == 'fill_fields'
            for tb in tool_use_blocks
        )
        for tb in tool_use_blocks:
            if tb.name == 'fill_fields':
                filled = True
            try:
                result_str, ok = execute_tool(tb.name, tb.input, state)
            except Exception as exc:
                result_str = f'[error] tool {tb.name} 执行失败：{exc}'
                ok = False
            if not ok:
                all_ok = False
            # 记录事件
            events.extend(_tool_events_for_block(tb.name, tb.input, state))
            tool_results.append({
                'type': 'tool_result',
                'tool_use_id': tb.id,
                'content': result_str,
            })

        # 快速路径：纯填表且全部成功，模型本轮已给出回复文本 → 直接结束（省一次 LLM 往返）
        if (
            only_fill
            and all_ok
            and any(part.strip() for part in text_parts)
        ):
            reply = ''.join(text_parts).strip()
            break

        messages.append({'role': 'assistant', 'content': resp.content})
        messages.append({'role': 'user', 'content': tool_results})
    else:
        # 循环用尽，兜底
        reply = '信息已记录，还有什么需要补充的吗？'

    # 漏采保险：整轮没调过 fill_fields，补一轮抽取
    if not filled:
        _run_extraction_pass(
            client, state, messages, reply, history_summary, events,
        )

    # 返回前重算章节 status（治"全 pending"显示问题）
    flow.recompute_section_status(state)

    return AgentResult(
        reply=reply,
        tool_events=events,
        state=state,
        form_complete=flow.form_complete(state),
        suggestions=_build_suggestions(state,reply,),
    )


def _tool_events_for_block(
    name: str,
    tool_input: dict,
    state: StudioFormState,
) -> list[ToolEvent]:
    if name == 'fill_fields':
        events = []
        for update in tool_input.get('updates', []):
            section_id = update.get('section_id', '')
            field_id = update.get('field_id', '').split('.')[-1]
            section = state.sections.get(section_id)
            if section is None or field_id not in section.fields:
                continue
            events.append(ToolEvent(
                kind='fill',
                section_id=section_id,
                field_id=field_id,
                value=section.fields[field_id].value,
            ))
        return events
    if name == 'skip_section':
        return [ToolEvent(kind='skip', section_id=tool_input['section_id'])]
    return []


async def _stream_response(
    client: AsyncAnthropic,
    **kwargs,
) -> AsyncIterator[object]:
    """转发 SDK 文本 delta，并在空闲时发送内部 heartbeat 标记。"""
    async with client.messages.stream(**kwargs) as stream:
        iterator = stream.__aiter__()
        pending: asyncio.Task | None = None
        while True:
            if pending is None:
                pending = asyncio.create_task(anext(iterator))
            done, _ = await asyncio.wait({pending}, timeout=15)
            if not done:
                yield None
                continue
            try:
                event = pending.result()
            except StopAsyncIteration:
                break
            finally:
                pending = None

            if (
                getattr(event, 'type', None) == 'content_block_delta'
                and getattr(getattr(event, 'delta', None), 'type', None) == 'text_delta'
            ):
                text = getattr(event.delta, 'text', '')
                if text:
                    yield AgentStreamDelta(text)

        yield await stream.get_final_message()


async def run_agent_stream(
    state: StudioFormState,
    user_message: str,
    history: list[dict] | None = None,
    images: list[SavedImage] | None = None,
) -> AsyncIterator[
    AgentStreamDelta | AgentStreamStatus | AgentStreamToolEvent | AgentStreamResult | None
]:
    """运行真实 SDK stream，并产出安全的内部流式事件。images 为已落盘的 SavedImage 列表。"""
    client = get_async_client()
    events: list[ToolEvent] = []
    try:
        full_history = history or []
        older_history = full_history[:-RECENT_MESSAGE_LIMIT]
        recent_history = full_history[-RECENT_MESSAGE_LIMIT:]
        history_summary = await _summarize_history_async(client, older_history)

        messages = list(recent_history)
        while messages and messages[0].get('role') != 'user':
            messages.pop(0)
        messages.append({'role': 'user', 'content': _build_user_content(user_message, images)})

        reply = ''
        filled = False  # 本轮是否调过 fill_fields（updates=[] 也算）
        for _ in range(MAX_ITERATIONS):
            yield AgentStreamStatus(phase='generating', message='正在生成回复')
            response = None
            async for item in _stream_response(
                client,
                model=LLM_MODEL,
                max_tokens=800,
                temperature=LLM_TEMPERATURE,
                thinking={'type': 'disabled'},
                system=_build_system_prompt(state, history_summary),
                tools=TOOL_DEFS,
                tool_choice={'type': 'auto'},
                messages=messages,
            ):
                if item is None:
                    yield None
                elif isinstance(item, AgentStreamDelta):
                    yield item
                else:
                    response = item

            if response is None:
                raise RuntimeError('LLM stream ended without final response')

            text = ''.join(
                block.text
                for block in response.content
                if block.type == 'text'
            ).strip()
            tool_blocks = [
                block for block in response.content
                if block.type == 'tool_use'
            ]

            if response.stop_reason != 'tool_use' or not tool_blocks:
                reply += text
                break

            yield AgentStreamStatus(phase='tool_call', message='正在更新表单')
            tool_results = []
            all_ok = True
            only_fill = all(
                block.name == 'fill_fields'
                for block in tool_blocks
            )
            for block in tool_blocks:
                if block.name == 'fill_fields':
                    filled = True
                result, ok = execute_tool(block.name, block.input, state)
                if not ok:
                    all_ok = False
                block_events = _tool_events_for_block(block.name, block.input, state)
                events.extend(block_events)
                for event in block_events:
                    yield AgentStreamToolEvent(event)
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': block.id,
                    'content': result,
                })

            # 快速路径：纯填表且全部成功，本轮文本已流给用户 → 直接结束
            if only_fill and all_ok and text:
                reply += text
                break

            messages.append({'role': 'assistant', 'content': response.content})
            messages.append({'role': 'user', 'content': tool_results})
        else:
            reply = '信息已记录，还有什么需要补充的吗？'

        # 漏采保险：整轮没调过 fill_fields，补一轮抽取
        if not filled:
            extract_events = await _run_extraction_pass_async(
                client, state, messages, reply, history_summary,
            )
            if extract_events:
                yield AgentStreamStatus(phase='tool_call', message='正在更新表单')
                events.extend(extract_events)
                for event in extract_events:
                    yield AgentStreamToolEvent(event)

        flow.recompute_section_status(state)
        yield AgentStreamResult(
            reply=reply,
            tool_events=events,
            state=state,
            form_complete=flow.form_complete(state),
            suggestions=_build_suggestions(state, reply),
        )
    finally:
        await client.close()
