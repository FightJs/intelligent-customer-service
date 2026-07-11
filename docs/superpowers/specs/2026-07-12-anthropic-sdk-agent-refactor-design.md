# Anthropic SDK Agent 架构重构设计

> 日期：2026-07-12
> 分支：feat/anthropic-sdk-agent
> 前置：PR #5（schema）、#6（AI 对话）、#7（交付物）已合并到 main

## 背景与动机

### 当前架构的问题

现有后端用 **DeepSeek V4-Flash + OpenAI SDK + JSON 模式两步法**实现 AI 对话采集：
1. 步骤 1：`response_format=json_object` 提取字段值
2. 步骤 2：普通对话生成自然回复

这套方案有以下根本性问题：

**1. 不是真正的 Agent**
智能客服本质是一个 agent——需要在对话过程中调用 tools（填表单）、控制采集进度（跳转/跳过章节）、触发生成交付物。现有方案用 JSON 模式模拟 tool use，模型无法自主决策调用什么、何时调用，只是被动输出结构化数据。

**2. SSE 流式被代理阻断**
前端通过 `fetch` + SSE 流式接收 AI 回复。用户环境有 Clash 代理（`127.0.0.1:7897`），代理会缓冲整个 streaming response 而非流式转发，导致：
- 前端 `reader.read()` 阻塞，等不到 token
- `streamChat` 的 Promise 不 resolve
- `finally { setStreaming(false) }` 不执行
- `streaming` 状态锁死为 `true`
- 后续所有 `send` 被 guard 拦截，请求发不出

这不是偶发 bug，是架构性的环境兼容问题。

**3. DeepSeek thinking 模式的限制**
- `tool_choice=required` 不被支持（thinking 模式限制）
- 默认开启 thinking，延迟波动大（5-6 秒）
- 多轮对话需回传 `reasoning_content`，否则报错

### 设计目标

- 用 **anthropic SDK 原生 tool use** 替代 JSON 模式，实现真正的 agent 行为
- 面向 Anthropic `/messages` 协议编程，厂商可替换（改 base_url + key）
- 前端改普通 POST，根治代理阻断 SSE 问题
- 先对齐现有能力（对话填表单 + 生成交付物），MCP/需求分析后置

---

## 技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| SDK | `anthropic` Python SDK | 原生 tool use + agent loop，厂商可替换 |
| 协议 | Anthropic `/messages` | DeepSeek/通义/硅基流动均兼容，改 base_url 即可换厂商 |
| 当前厂商 | DeepSeek V4-Flash（`/anthropic` 端点） | 已验证连通 + tool use，国内直连 |
| 传输 | 普通 POST + JSON | 彻底避坑代理缓冲 SSE |
| thinking | 关闭（`thinking: {"type": "disabled"}`） | 客服场景不需深度推理，实测 1.5-3s |
| agent loop | 单次 tool use 循环（方案 A） | 模型自主决策，真 agent 行为 |

---

## 架构设计

### Agent Tool 定义

5 个 tool，覆盖采集 → 进度控制 → 交付物生成全流程：

#### 采集类

**`fill_fields`** — 填写表单字段（核心）
```python
{
    "name": "fill_fields",
    "description": "把从用户消息提取的信息填入调研表字段，可一次填多个",
    "input_schema": {
        "type": "object",
        "properties": {
            "updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section_id": {"type": "string"},
                        "field_id": {"type": "string"},
                        "value": {}  # text→string, choice-single→value, choice-multi→array, dimension→{dim:val}
                    },
                    "required": ["section_id", "field_id", "value"]
                }
            }
        },
        "required": ["updates"]
    }
}
```

**`skip_section`** — 跳过章节
```python
{
    "name": "skip_section",
    "description": "条件跳过某章节。如用户说\"没有直播间\"→ skip status",
    "input_schema": {
        "type": "object",
        "properties": {
            "section_id": {"type": "string"},
            "reason": {"type": "string"}
        },
        "required": ["section_id"]
    }
}
```

#### 进度控制类

**`get_progress`** — 查采集进度
```python
{
    "name": "get_progress",
    "description": "查询当前采集进度：各章节完成情况、未填必填字段列表、下一个该问的字段",
    "input_schema": {"type": "object", "properties": {}}
    # 返回：{ section_states, next_section, next_field, overall_filled, overall_total, form_complete }
}
```

**`set_current_section`** — 主动跳转章节
```python
{
    "name": "set_current_section",
    "description": "主动切换当前采集章节。正常按顺序推进，但当用户跳着回答或想回头改时用这个",
    "input_schema": {
        "type": "object",
        "properties": {
            "section_id": {"type": "string"}
        },
        "required": ["section_id"]
    }
}
```

#### 交付物类

**`generate_deliverable`** — 生成交付物
```python
{
    "name": "generate_deliverable",
    "description": "当采集完成或用户要求时，生成交付物文档。返回文件下载信息",
    "input_schema": {
        "type": "object",
        "properties": {
            "doc_type": {"type": "string", "enum": ["markdown", "excel", "word"]}
        },
        "required": ["doc_type"]
    }
    # 返回：{ filename, doc_type }
}
```

### 工具执行层

每个 tool 对应一个 Python 执行函数（`backend/agent/tools.py`），操作 `StudioFormState` 或调 `delivery/` 模块：

| tool | 执行逻辑 | 数据来源 |
|------|---------|---------|
| `fill_fields` | 遍历 updates，按 field type 应用值到 state | schema_def FIELD_BY_ID |
| `skip_section` | `flow.skip_section(state, sid)` | flow.py |
| `get_progress` | 聚合各章节进度 + 下一个未填必填字段 | flow.py |
| `set_current_section` | 设置 state.current_section_id | state |
| `generate_deliverable` | 调 delivery 模块生成文件，返回文件信息 | delivery/ |

field_id 兼容处理：LLM 可能输出带前缀的 `customer.brand`，执行时取 `split('.')[-1]`。

### Agent Loop（核心引擎）

标准 tool use 循环：

```
用户消息 + history + system_prompt + tools
    ↓
messages.create()  ← 第 1 次 LLM 调用
    ↓
┌─ stop_reason == "tool_use"?
│   ├─ 是 → 执行 tool（fill_fields/skip_section/get_progress/...）
│   │       → tool_result 回传
│   │       → messages.create() 再调  ← 循环
│   └─ 否（end_turn）→ 取文本回复，跳出循环
└──────────────────────┘
    ↓
返回：{ reply, tool_events, state, form_complete }
```

**循环边界保护：**
- 最大循环 5 次（理论 2-3 次够：调 progress + 调 fill_fields + 生成回复）
- 总超时 30 秒
- tool 执行失败：返回错误信息给模型，模型自行决定重试或换方式

**system prompt 每轮刷新：**
每次 `messages.create` 前重新生成 system prompt——tool 执行后 state 变了（填了字段、跳了章节），"下一个该问什么"也变了。模型始终基于最新状态决策。

**对话历史管理：**
- 传给 `messages.create` 的 history 只保留最近 6 条（3 轮）
- tool_use 和 tool_result 消息按 Anthropic 格式成对保留
- system prompt 单独传（不在 messages 数组里）

**system prompt 内容：**
- 角色设定（直播间搭建顾问）
- 调研表完整字段说明（动态注入：label/options/dims/required）
- 当前进度摘要（哪些章节完成、下一个该问什么）
- 客服填写指南 SOP（`AGENT_GUIDE`）
- 工具使用指导（何时调 fill_fields / skip_section / get_progress 等）

### 前后端接口

#### chat 端点（普通 POST 替代 SSE）

**请求：**
```json
POST /api/chat
{
  "session_id": "xxx",
  "message": "用户消息",
  "history": [{"role":"user","content":"..."},{"role":"assistant","content":"..."}]
}
```

**响应：**
```json
{
  "reply": "好的，已记下云裳品牌...下一个问问您的行业品类？",
  "tool_events": [
    {"kind":"fill","section_id":"customer","field_id":"brand","value":"云裳"},
    {"kind":"fill","section_id":"customer","field_id":"contact","value":"张三"}
  ],
  "form_state": { ... 完整 StudioFormState（camelCase） ... },
  "form_complete": false
}
```

#### generate_deliverable tool 与前端联动

- tool 在后端生成文件（存内存/临时目录），返回 `{ filename, doc_type }`
- 模型在回复里告诉用户"已生成，请点击右侧下载"
- 前端从 `tool_events` 检测到 `kind: "deliverable"`，自动打开右侧 DeliveryPanel
- 用户在 DeliveryPanel 点击下载按钮，通过 session_id 调 `/api/generate/{type}` 端点获取文件流（该端点已存在，不变）
- 即：tool 负责"通知前端可以下载了"，实际文件下载走已有的 generate 端点

---

## 改动范围

### 保留不动

| 模块 | 原因 |
|------|------|
| `backend/survey/`（schema 定义 + state 工厂） | 调研表是数据源，agent tool 基于它 |
| `backend/agent/flow.py`（状态机） | tools.py 复用：进度计算、条件分支、必填校验 |
| `backend/delivery/`（交付物生成） | generate_deliverable tool 直接调 |
| `backend/store/db.py`（SQLite 持久化） | 会话/消息存储不变 |
| `backend/api/app.py` 的 session/generate 端点 | 不变 |
| 前端三栏 UI、schema codegen、FormContext reducer | 不变 |
| `frontend/src/components/DeliveryPanel/` | 不变（已是普通 POST 下载） |

### 替换

| 文件 | 改动 |
|------|------|
| `backend/agent/llm.py` | openai SDK → anthropic SDK，client + 辅助函数 |
| `backend/agent/gather.py` | 删除 JSON 两步法；`initial_greeting` 改用 loop.py |
| `backend/api/app.py` chat 端点 | SSE EventSourceResponse → 普通 JSON Response，调 `loop.run_agent` |
| `frontend/src/api/client.ts` | `streamChat` → `chat`（普通 POST） |
| `frontend/src/components/ChatPanel/ChatPanel.tsx` | 流式拼接 → loading + 一次性渲染 |

### 新增

| 文件 | 职责 |
|------|------|
| `backend/agent/tools.py` | 5 个 tool 的定义（Anthropic schema）+ 执行函数 |
| `backend/agent/loop.py` | agent loop 引擎（tool use 循环） |

### 测试

| 文件 | 改动 |
|------|------|
| `backend/tests/test_api.py` | chat 端点测试改为断言 JSON 字段（不再解析 SSE） |
| `backend/tests/test_flow.py` | 不变 |
| 新增 `backend/tests/test_loop.py` | agent loop 测试（mock anthropic 响应） |
| 新增 `backend/tests/test_tools.py` | 5 个 tool 执行函数单元测试 |

### 依赖变化

- 新增：`anthropic`（pip install）
- 移除：`sse-starlette` 的使用（包保留不删）
- 前端：无新增依赖

---

## 代码结构

```
backend/agent/
    __init__.py
    llm.py          # anthropic SDK client + 辅助函数（替换）
    tools.py        # 5 个 tool 定义 + 执行函数（新增）
    loop.py         # agent loop 引擎（新增）
    gather.py       # initial_greeting（保留，改用 loop）
    flow.py         # 状态机（保留不动）
```

---

## 验收标准

- [ ] anthropic SDK 连通 DeepSeek `/anthropic` 端点（基础对话 + tool use）
- [ ] agent loop 正确执行：模型调 fill_fields → 字段填入 → 生成回复
- [ ] 一句话多字段填充正常（"女装中高端预算5万"→ 3+ 字段）
- [ ] 条件分支生效（"没有直播间" → 模型调 skip_section）
- [ ] 进度查询正常（模型调 get_progress 感知状态）
- [ ] 交付物生成正常（模型调 generate_deliverable，前端检测到事件）
- [ ] 前端普通 POST 不再卡死（无 SSE，无代理问题）
- [ ] 后端测试全过（test_api + test_flow + test_loop + test_tools）
- [ ] 前端测试全过 + tsc 零报错
- [ ] 真实端到端联调通过（多轮对话 + 交付物下载）

---

## 不在本期范围

- MCP 接入（需求分析、智能推荐等外部工具）
- 多视角效果图生成
- 向量化评分报告
- 远程推送（webhook/S3）
- 打字机流式效果（如需可后续用 WebSocket 实现）
