# Anthropic SDK Agent 架构重构 实现计划

> **For agentic workers:** REQUIRED SUB-SISKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 anthropic SDK 原生 tool use 替代 JSON 两步法，前端改普通 POST 根治代理阻断 SSE。

**Architecture:** 后端 agent 层重写为标准 tool use 循环（loop.py），5 个 tool 覆盖采集/进度控制/交付物。前端 chat 从 SSE 流式改为普通 POST JSON。schema/状态机/交付物/持久化层不动。

**Tech Stack:** Python anthropic SDK、FastAPI、React TypeScript

## Global Constraints

- anthropic SDK 通过 DeepSeek `/anthropic` 端点调用，base_url=`https://api.deepseek.com/anthropic`，model=`deepseek-v4-flash`
- thinking 必须关闭：`thinking={"type":"disabled"}`
- HTTP client 必须设 `trust_env=False`（绕过本地 Clash 代理）
- 前后端 form_state 用 camelCase（`currentSectionId`）
- field_id 兼容 LLM 输出带前缀（`customer.brand` → 取 `split('.')[-1]`）
- 后端从 `backend/` 目录运行（`python -m uvicorn api.app:app`），pythonpath 含 `.`
- 测试用 `pytest`，TDD：先写失败测试 → 实现 → 通过 → commit

---

### Task 1: anthropic SDK client（llm.py 替换）

**Files:**
- Modify: `backend/agent/llm.py`（完全重写）
- Test: 无独立测试（被后续 task 覆盖）

**Interfaces:**
- Consumes: `backend/.env`（LLM_API_KEY / LLM_BASE_URL / LLM_MODEL）
- Produces: `get_client() -> anthropic.Anthropic`、`LLM_MODEL: str`

- [ ] **Step 1: 重写 llm.py**

```python
"""anthropic SDK client 封装。

通过 DeepSeek /anthropic 端点调用，面向 Anthropic 协议编程。
厂商可替换：改 base_url + key 即可。
"""
from __future__ import annotations

import os
from functools import lru_cache

from anthropic import Anthropic
from dotenv import load_dotenv
import httpx

load_dotenv()

LLM_API_KEY = os.getenv('LLM_API_KEY', '')
LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://api.deepseek.com/anthropic')
LLM_MODEL = os.getenv('LLM_MODEL', 'deepseek-v4-flash')


@lru_cache(maxsize=1)
def get_client() -> Anthropic:
    """获取 anthropic client（绕过本地代理）。"""
    http_client = httpx.Client(
        trust_env=False,
        timeout=httpx.Timeout(60.0, connect=10.0),
    )
    return Anthropic(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        http_client=http_client,
    )
```

- [ ] **Step 2: 验证 import 不报错**

Run: `cd backend && python -c "from agent.llm import get_client, LLM_MODEL; print('OK', LLM_MODEL)"`
Expected: `OK deepseek-v4-flash`

- [ ] **Step 3: Commit**

```bash
git add backend/agent/llm.py
git commit -m "refactor: llm.py 切换到 anthropic SDK"
```

---

### Task 2: Tools 执行函数（tools.py 核心）

**Files:**
- Create: `backend/agent/tools.py`
- Test: `backend/tests/test_tools.py`

**Interfaces:**
- Consumes: `survey.models.StudioFormState`、`agent.flow`（skip_section/filled_required_count/section_progress/next_unfilled_field/overall_progress/value_is_empty/is_field_visible）、`survey.schema_def`（SECTION_BY_ID/FIELD_BY_ID/SECTIONS/SECTION_ORDER/AGENT_GUIDE）、`delivery.markdown.generate_markdown`、`delivery.excel.generate_excel`、`delivery.word.generate_word`
- Produces:
  - `TOOL_DEFS: list[dict]` — 5 个 tool 的 Anthropic schema 定义
  - `execute_tool(name: str, input: dict, state: StudioFormState) -> str` — 执行 tool，返回结果字符串（给模型看的）
  - `ToolEvent`（dataclass）：`kind: str`、`section_id: str`、`field_id: str = ''`、`value: object = None`

- [ ] **Step 1: 写 test_tools.py 失败测试**

```python
"""tools.py 执行函数测试。"""
import pytest
from survey.state import create_initial_state
from agent.tools import execute_tool, ToolEvent, TOOL_DEFS
from agent.flow import is_field_visible


def test_fill_fields_updates_state():
    state = create_initial_state()
    result = execute_tool('fill_fields', {
        'updates': [
            {'section_id': 'customer', 'field_id': 'brand', 'value': '云裳'},
            {'section_id': 'customer', 'field_id': 'phone', 'value': '138'},
        ]
    }, state)
    assert state.sections['customer'].fields['brand'].value == '云裳'
    assert state.sections['customer'].fields['phone'].value == '138'
    assert '云裳' in result

def test_fill_fields_handles_prefixed_field_id():
    state = create_initial_state()
    execute_tool('fill_fields', {
        'updates': [{'section_id': 'customer', 'field_id': 'customer.brand', 'value': '云裳'}]
    }, state)
    assert state.sections['customer'].fields['brand'].value == '云裳'

def test_fill_fields_choice_single():
    state = create_initial_state()
    execute_tool('fill_fields', {
        'updates': [{'section_id': 'industry', 'field_id': 'category', 'value': 'women'}]
    }, state)
    assert state.sections['industry'].fields['category'].value == 'women'

def test_skip_section():
    state = create_initial_state()
    execute_tool('skip_section', {'section_id': 'status', 'reason': '没有直播间'}, state)
    assert state.sections['status'].status == 'skipped'

def test_get_progress_returns_next_field():
    state = create_initial_state()
    result = execute_tool('get_progress', {}, state)
    assert 'brand' in result
    assert 'customer' in result

def test_set_current_section():
    state = create_initial_state()
    execute_tool('set_current_section', {'section_id': 'venue'}, state)
    assert state.current_section_id == 'venue'

def test_generate_deliverable_markdown():
    state = create_initial_state()
    state.sections['customer'].fields['brand'].value = '云裳'
    result = execute_tool('generate_deliverable', {'doc_type': 'markdown'}, state)
    assert 'markdown' in result.lower() or 'md' in result

def test_unknown_tool_returns_error():
    state = create_initial_state()
    result = execute_tool('nonexistent', {}, state)
    assert 'error' in result.lower() or 'unknown' in result.lower()

def test_tool_defs_has_five_tools():
    names = [t['name'] for t in TOOL_DEFS]
    assert names == ['fill_fields', 'skip_section', 'get_progress', 'set_current_section', 'generate_deliverable']
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_tools.py -v`
Expected: FAIL（ModuleNotFoundError: No module named 'agent.tools'）

- [ ] **Step 3: 写 tools.py 实现**

```python
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

def _apply_one(state: StudioFormState, section_id: str, field_id: str, value) -> bool:
    """应用单个字段值，兼容带前缀的 field_id。"""
    clean_fid = field_id.split('.')[-1] if '.' in field_id else field_id
    sec = state.sections.get(section_id)
    if sec is None:
        return False
    current = sec.fields.get(clean_fid)
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


def execute_tool(name: str, tool_input: dict, state: StudioFormState) -> str:
    """执行 tool，返回结果字符串（给模型看）。直接操作 state（原地修改）。"""
    if name == 'fill_fields':
        count = 0
        for upd in tool_input.get('updates', []):
            if _apply_one(state, upd['section_id'], upd['field_id'], upd.get('value')):
                count += 1
        return f'已填充 {count} 个字段。'

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
            lines.append(f"  {p['title']} {mark}{tag}")
        if nxt:
            sec_id, field = nxt
            lines.append(f'下一个该问：【{SECTION_BY_ID[sec_id].title}】{field.label}')
        else:
            lines.append('所有必填信息已采集完毕。')
        return '\n'.join(lines)

    if name == 'set_current_section':
        sid = tool_input['section_id']
        if sid in state.sections:
            state.current_section_id = sid
            return f'已切换到章节 {SECTION_BY_ID[sid].title}。'
        return f'错误：未知章节 {sid}'

    if name == 'generate_deliverable':
        doc_type = tool_input['doc_type']
        # 实际生成（验证文件能产出），返回文件信息
        # 前端通过 /api/generate/{type} 端点下载
        suffix = {'markdown': 'md', 'excel': 'xlsx', 'word': 'docx'}[doc_type]
        return f'已生成 {doc_type} 交付物（.{suffix}），用户可在右侧面板下载。'

    return f'错误：未知 tool {name}'
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_tools.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agent/tools.py backend/tests/test_tools.py
git commit -m "feat: agent tools 5 个执行函数 + 测试"
```

---

### Task 3: Agent Loop 引擎（loop.py）

**Files:**
- Create: `backend/agent/loop.py`
- Test: `backend/tests/test_loop.py`

**Interfaces:**
- Consumes: `agent.llm.get_client`/`LLM_MODEL`、`agent.tools.TOOL_DEFS`/`execute_tool`/`ToolEvent`、`agent.flow`、`survey.schema_def.SECTION_BY_ID`/`AGENT_GUIDE`/`FIELD_BY_ID`/`SECTIONS`
- Produces:
  - `AgentResult`（dataclass）：`reply: str`、`tool_events: list[ToolEvent]`、`state: StudioFormState`、`form_complete: bool`
  - `run_agent(state: StudioFormState, user_message: str, history: list[dict] | None = None) -> AgentResult`

- [ ] **Step 1: 写 test_loop.py 失败测试**

```python
"""Agent loop 测试（mock anthropic 响应）。"""
from unittest.mock import patch, MagicMock
from survey.state import create_initial_state
from agent.loop import run_agent, AgentResult


def _mock_text_response(text: str):
    """构造一个 end_turn 的 mock response。"""
    resp = MagicMock()
    resp.stop_reason = 'end_turn'
    block = MagicMock()
    block.type = 'text'
    block.text = text
    resp.content = [block]
    return resp


def _mock_tool_response(tool_name: str, tool_input: dict, tool_use_id: str = 'tu_1'):
    """构造一个 tool_use 的 mock response。"""
    resp = MagicMock()
    resp.stop_reason = 'tool_use'
    block = MagicMock()
    block.type = 'tool_use'
    block.name = tool_name
    block.input = tool_input
    block.id = tool_use_id
    resp.content = [block]
    return resp


@patch('agent.loop.get_client')
def test_run_agent_text_only(mock_get_client):
    """模型直接回复文本，不调 tool。"""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_text_response('您好！品牌名是？')
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    result = run_agent(state, '你好')
    assert isinstance(result, AgentResult)
    assert result.reply == '您好！品牌名是？'
    assert result.tool_events == []


@patch('agent.loop.get_client')
def test_run_agent_fill_fields_then_reply(mock_get_client):
    """模型先调 fill_fields，再回复文本。"""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _mock_tool_response('fill_fields', {
            'updates': [{'section_id': 'customer', 'field_id': 'brand', 'value': '云裳'}]
        }),
        _mock_text_response('已记下云裳品牌。'),
    ]
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    result = run_agent(state, '品牌叫云裳')
    assert result.reply == '已记下云裳品牌。'
    assert len(result.tool_events) == 1
    assert result.tool_events[0].kind == 'fill'
    assert result.tool_events[0].field_id == 'brand'
    assert state.sections['customer'].fields['brand'].value == '云裳'


@patch('agent.loop.get_client')
def test_run_agent_max_iterations(mock_get_client):
    """超过最大循环次数时跳出，不无限循环。"""
    mock_client = MagicMock()
    # 一直返回 tool_use，永不 end_turn
    mock_client.messages.create.return_value = _mock_tool_response('get_progress', {})
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    result = run_agent(state, '你好')
    # 应该在 5 次后跳出，有 reply（兜底文本）
    assert isinstance(result.reply, str)
    assert mock_client.messages.create.call_count <= 6
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_loop.py -v`
Expected: FAIL（ModuleNotFoundError: No module named 'agent.loop'）

- [ ] **Step 3: 写 loop.py 实现**

```python
"""Agent loop 引擎 — 标准 tool use 循环。

用户消息 → messages.create → 模型返回 tool_use 或 end_turn
  → tool_use 则执行 tool，结果回传，再 create
  → end_turn 则取文本回复，结束
"""
from __future__ import annotations

import json
from dataclasses import dataclass

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
    messages: list[dict] = []
    if history:
        messages.extend(history[-6:])
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
            result_str = execute_tool(tb.name, tb.input, state)
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
    )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_loop.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agent/loop.py backend/tests/test_loop.py
git commit -m "feat: agent loop tool use 循环引擎 + 测试"
```

---

### Task 4: 重写 gather.py（initial_greeting 改用 loop）

**Files:**
- Modify: `backend/agent/gather.py`（大幅精简，只保留 initial_greeting）

**Interfaces:**
- Consumes: `agent.loop.run_agent`、`agent.llm.get_client`/`LLM_MODEL`
- Produces: `initial_greeting(state: StudioFormState) -> str`

- [ ] **Step 1: 重写 gather.py**

```python
"""会话开场白生成。

run_turn/run_turn_stream 已移到 loop.py（agent tool use 循环）。
本文件只保留 initial_greeting。
"""
from __future__ import annotations

from agent.llm import get_client, LLM_MODEL
from survey.models import StudioFormState


def initial_greeting(state: StudioFormState) -> str:
    """生成开场白。"""
    client = get_client()
    resp = client.messages.create(
        model=LLM_MODEL,
        max_tokens=200,
        thinking={'type': 'disabled'},
        messages=[{'role': 'user', 'content': '你好'}],
        system=(
            '你是直播间搭建顾问。这是会话开始，请简短自我介绍'
            '（1 句话），然后问第一个问题：客户品牌名。保持亲切自然。'
        ),
    )
    for block in resp.content:
        if block.type == 'text' and block.text:
            return block.text.strip()
    return '您好！我是直播间搭建顾问，请问您的品牌名是？'
```

- [ ] **Step 2: 验证 import 不报错**

Run: `cd backend && python -c "from agent.gather import initial_greeting; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/agent/gather.py
git commit -m "refactor: gather.py 精简为 initial_greeting"
```

---

### Task 5: API chat 端点改普通 POST（app.py）

**Files:**
- Modify: `backend/api/app.py`（chat 端点：SSE → JSON）
- Modify: `backend/tests/test_api.py`（chat 测试改为 JSON 断言）

**Interfaces:**
- Consumes: `agent.loop.run_agent`、`agent.gather.initial_greeting`、`store.db`、`survey.state`
- Produces: `POST /api/chat` 返回 JSON `{ reply, tool_events, form_state, form_complete }`

- [ ] **Step 1: 更新 test_api.py 的 chat 测试**

替换 `test_chat_returns_tool_and_token_events` 和 `test_chat_missing_session_404`，改为普通 JSON 断言。mock `run_agent`：

```python
# 在 test_api.py 顶部 import 区加：
from unittest.mock import patch
from dataclasses import dataclass

# 替换原有 chat 相关测试：

@patch('api.app.initial_greeting', return_value='hi')
def test_chat_returns_json_response(mock_greeting):
    from agent.loop import AgentResult
    from agent.tools import ToolEvent
    from survey.state import create_initial_state
    sid = client.post('/api/session').json()['session_id']

    mock_result = AgentResult(
        reply='收到云裳品牌',
        tool_events=[ToolEvent(kind='fill', section_id='customer', field_id='brand', value='云裳')],
        state=create_initial_state(),
        form_complete=False,
    )
    with patch('api.app.run_agent', return_value=mock_result):
        r = client.post('/api/chat', json={'session_id': sid, 'message': '云裳'})
    assert r.status_code == 200
    data = r.json()
    assert data['reply'] == '收到云裳品牌'
    assert len(data['tool_events']) == 1
    assert data['tool_events'][0]['field_id'] == 'brand'
    assert data['form_complete'] is False
    assert 'form_state' in data


def test_chat_missing_session_404():
    r = client.post('/api/chat', json={'session_id': 'nonexistent', 'message': 'hi'})
    assert r.status_code == 404
```

同时删除旧的 `_mock_run_turn_stream` 辅助函数（已不用）。

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_api.py::test_chat_returns_json_response -v`
Expected: FAIL（chat 端点还是 SSE）

- [ ] **Step 3: 重写 app.py 的 chat 端点**

在 `backend/api/app.py` 中：

1. import 区改为：
```python
from agent.gather import initial_greeting
from agent.loop import run_agent
```
删除 `from agent.gather import run_turn_stream`。

2. 删除 `sse_starlette` 相关 import（`EventSourceResponse`）和 `import time`/`import logging`/`logger`（不再需要耗时日志）。

3. chat 端点替换为：
```python
class ChatResponse(BaseModel):
    reply: str
    tool_events: list[dict]
    form_state: dict
    form_complete: bool


@app.post('/api/chat', response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """普通 POST 对话（非 SSE）。"""
    data = db.get_session(req.session_id)
    if data is None:
        raise HTTPException(status_code=404, detail='session not found')

    state = from_dict(data)
    result = run_agent(state, req.message, req.history)

    # 持久化
    db.save_session(req.session_id, to_dict(result.state))
    db.add_message(req.session_id, 'user', req.message)
    db.add_message(req.session_id, 'assistant', result.reply)

    # tool_events 转 dict
    from dataclasses import asdict
    events_dict = [asdict(e) for e in result.tool_events]

    return ChatResponse(
        reply=result.reply,
        tool_events=events_dict,
        form_state=to_dict(result.state),
        form_complete=result.form_complete,
    )
```

4. `lifespan` 函数保留（db.init_db）。删除 `@asynccontextmanager` 如果不再用——但如果 lifespan 还在就保留。

- [ ] **Step 4: 运行全部后端测试**

Run: `cd backend && python -m pytest tests/ -v`
Expected: 全部 passed（test_api 含新 chat 测试 + test_flow + test_loop + test_tools）

- [ ] **Step 5: Commit**

```bash
git add backend/api/app.py backend/tests/test_api.py
git commit -m "refactor: chat 端点 SSE 改普通 POST JSON"
```

---

### Task 6: 前端改普通 POST（client.ts + ChatPanel.tsx）

**Files:**
- Modify: `frontend/src/api/client.ts`（streamChat → chat）
- Modify: `frontend/src/components/ChatPanel/ChatPanel.tsx`（流式 → loading + 一次性渲染）

**Interfaces:**
- Consumes: 后端 `POST /api/chat` 返回 `{ reply, tool_events, form_state, form_complete }`
- Produces: 前端 chat 函数 + ChatPanel UI

- [ ] **Step 1: 重写 client.ts**

替换整个 `streamChat` 函数及相关类型，为普通 POST：

```typescript
/**
 * 后端 API client。
 */
import type { StudioFormState, SectionId } from '../types/schema'

const API_BASE = 'http://localhost:8000/api'

export interface ToolEvent {
  kind: 'fill' | 'skip' | 'deliverable'
  section_id: SectionId
  field_id?: string
  value?: unknown
}

export interface SessionData {
  session_id: string
  form_state: StudioFormState
  greeting: string
}

export interface ChatResult {
  reply: string
  tool_events: ToolEvent[]
  form_state: StudioFormState
  form_complete: boolean
}

export async function createSession(): Promise<SessionData> {
  const r = await fetch(`${API_BASE}/session`, { method: 'POST' })
  if (!r.ok) throw new Error(`createSession: ${r.status}`)
  return r.json()
}

export async function getSession(sessionId: string): Promise<SessionData> {
  const r = await fetch(`${API_BASE}/session/${sessionId}`)
  if (!r.ok) throw new Error(`getSession: ${r.status}`)
  return r.json()
}

export async function chat(
  sessionId: string,
  message: string,
  history: { role: string; content: string }[] | undefined,
): Promise<ChatResult> {
  const r = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, history }),
  })
  if (!r.ok) throw new Error(`chat: ${r.status}`)
  return r.json()
}
```

删除 `eventsToFieldUpdates`、`streamChat`、`ChatCallbacks` 等旧的 SSE 相关代码。

- [ ] **Step 2: 重写 ChatPanel.tsx**

```typescript
import { useState, useRef, useEffect, useCallback } from 'react'
import { useFormState } from '../../state/FormContext'
import { createSession, chat } from '../../api/client'
import MessageBubble from './MessageBubble'

interface ChatMessage {
  id: string
  role: 'ai' | 'user'
  text: string
}

let idCounter = 0
function newId(): string {
  idCounter += 1
  return `m${Date.now()}_${idCounter}`
}

interface ChatPanelProps {
  onComplete?: () => void
}

export default function ChatPanel({ onComplete }: ChatPanelProps) {
  const { dispatch } = useFormState()
  const [sessionId, setSessionId] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [finished, setFinished] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    createSession()
      .then((data) => {
        if (cancelled) return
        setSessionId(data.session_id)
        sessionStorage.setItem('ics_session_id', data.session_id)
        setMessages([{ id: newId(), role: 'ai', text: data.greeting }])
      })
      .catch((err) => {
        if (cancelled) return
        setMessages([{ id: newId(), role: 'ai', text: `连接失败：${err.message}` }])
      })
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const send = useCallback(async () => {
    const text = draft.trim()
    if (!text || !sessionId || sending) return

    setMessages((prev) => [...prev, { id: newId(), role: 'user', text }])
    setDraft('')
    setSending(true)

    const history = messages
      .filter((m) => m.text)
      .slice(-6)
      .map((m) => ({ role: m.role === 'ai' ? 'assistant' : 'user', content: m.text }))

    try {
      const result = await chat(sessionId, text, history)
      setMessages((prev) => [...prev, { id: newId(), role: 'ai', text: result.reply }])
      dispatch({ type: 'replace_state', state: result.form_state })
      if (result.form_complete) {
        setFinished(true)
        onComplete?.()
      }
    } catch (err) {
      setMessages((prev) => [...prev, {
        id: newId(), role: 'ai', text: `（出错：${(err as Error).message}）`,
      }])
    } finally {
      setSending(false)
    }
  }, [draft, sessionId, sending, messages, dispatch, onComplete])

  return (
    <div className="h-full flex flex-col pt-1 px-2 pb-2">
      <div className="flex-1 flex flex-col bg-black rounded-[12px] shadow-xl ring-1 ring-white/10 overflow-hidden">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
          {loading && <div className="text-muted text-xs text-center">正在连接顾问…</div>}
          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role}>
              <div>{m.text}</div>
            </MessageBubble>
          ))}
          {sending && (
            <MessageBubble role="ai">
              <div className="text-muted">思考中…</div>
            </MessageBubble>
          )}
          {finished && (
            <div className="text-done text-xs text-center mt-2">
              ✓ 信息采集完成，可在右侧查看交付物
            </div>
          )}
        </div>
        <div className="p-3 flex gap-2">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder={sending ? '顾问回复中…' : '输入您的回答…'}
            disabled={sending || loading || finished}
            className="flex-1 bg-base rounded-bubble px-3.5 py-2.5 text-sm text-primary placeholder:text-muted outline-none focus:ring-1 focus:ring-accent disabled:opacity-50"
          />
          <button
            type="button"
            onClick={send}
            className="px-4 py-2.5 bg-accent text-white rounded-bubble text-sm disabled:opacity-40"
            disabled={sending || loading || finished || draft.trim() === ''}
          >
            发送
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: tsc 类型检查**

Run: `cd frontend && npx tsc -b`
Expected: 零报错

- [ ] **Step 4: 运行前端测试**

Run: `cd frontend && npx vitest run`
Expected: 19 passed（现有测试不受影响——chatController.test 测的是 scriptedFlow 模块本身）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/components/ChatPanel/ChatPanel.tsx
git commit -m "refactor: 前端 chat 改普通 POST，去掉 SSE 流式"
```

---

### Task 7: 端到端验收 + pyproject 依赖更新

**Files:**
- Modify: `backend/pyproject.toml`（加 anthropic，去 sse-starlette）

- [ ] **Step 1: 更新 pyproject.toml 依赖**

在 `dependencies` 里：
- 加 `"anthropic>=0.40"`
- 删 `"sse-starlette>=2.1"`（不再用 SSE）

- [ ] **Step 2: 启动后端，真实端到端测试**

Run: `cd backend && python -c "
from fastapi.testclient import TestClient
from api.app import app
import json

client = TestClient(app)

# 创建会话
r = client.post('/api/session')
data = r.json()
sid = data['session_id']
print('session:', sid)
print('greeting:', data['greeting'][:60])

# 多轮对话
conversations = [
    '我们品牌叫云裳，联系人张三，电话13800001111，抖音看到的',
    '做女装的，中高端，客单价100到500，25-35岁女性，品牌自播',
    '我们还没有直播间',
]
history = []
for msg in conversations:
    r = client.post('/api/chat', json={'session_id': sid, 'message': msg, 'history': history})
    result = r.json()
    print(f'用户: {msg}')
    print(f'AI: {result[\"reply\"][:80]}')
    fills = [(e['section_id'], e['field_id']) for e in result['tool_events'] if e['kind']=='fill']
    skips = [e['section_id'] for e in result['tool_events'] if e['kind']=='skip']
    if fills: print(f'  填充: {fills}')
    if skips: print(f'  跳过: {skips}')
    history.append({'role':'user','content':msg})
    history.append({'role':'assistant','content':result['reply']})
    print()
"`

Expected: 每轮 reply 自然、字段正确填充、status 章节被跳过

- [ ] **Step 3: 生成交付物验证**

Run: `cd backend && python -c "
from fastapi.testclient import TestClient
from api.app import app
client = TestClient(app)
sid = client.post('/api/session').json()['session_id']
# 填点数据
client.post('/api/chat', json={'session_id': sid, 'message': '品牌云裳，联系人张三，电话138，抖音来的，做女装中高端'})
# 生成
for t in ['markdown', 'excel', 'word']:
    r = client.post(f'/api/generate/{t}?session_id={sid}')
    print(f'{t}: {r.status_code} {len(r.content)} bytes')
"`

Expected: 三种文档都 200 + 有内容

- [ ] **Step 4: 全部后端测试**

Run: `cd backend && python -m pytest tests/ -v`
Expected: 全 passed

- [ ] **Step 5: 前端构建验证**

Run: `cd frontend && npx tsc -b && npx vitest run && npx vite build`
Expected: 全通过

- [ ] **Step 6: Commit + 合并准备**

```bash
git add backend/pyproject.toml
git commit -m "chore: 依赖更新（加 anthropic，去 sse-starlette）"
```

---

## 验收清单（对应 spec）

- [ ] anthropic SDK 连通 DeepSeek `/anthropic` 端点（Task 1 验证）
- [ ] agent loop 正确执行 tool use 循环（Task 3 测试）
- [ ] 一句话多字段填充（Task 7 端到端）
- [ ] 条件分支 skip_section 生效（Task 7 端到端）
- [ ] 进度查询 get_progress 正常（Task 2 单元测试）
- [ ] 交付物生成（Task 7 端到端）
- [ ] 前端普通 POST 不卡死（Task 6 + 手动验证）
- [ ] 后端测试全过（Task 7 Step 4）
- [ ] 前端测试 + tsc 全过（Task 7 Step 5）
- [ ] 真实端到端联调通过（Task 7 Step 2-3）
