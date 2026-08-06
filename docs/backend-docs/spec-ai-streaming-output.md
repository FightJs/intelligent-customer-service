# 后端流式输出 Spec

> 对应 PRD：[`docs/ai-streaming-output-prd.md`](../ai-streaming-output-prd.md)  
> 目标：后续开发可直接按本文实现 FastAPI + Agent + Anthropic 兼容接口的聊天 SSE；本文不要求当前立即改代码。

## 1. 现状与改造边界

当前实现位置：

- API：`backend/api/app.py` 的 `POST /api/chat`
- Agent：`backend/agent/loop.py` 的同步 `run_agent`
- LLM client：`backend/agent/llm.py` 的同步 `Anthropic`
- 状态与历史：`backend/store/db.py`
- 工具：`backend/agent/tools.py` 的 `ToolEvent`、`execute_tool`

新增 `POST /api/chat/stream`，不改变旧 `/api/chat` 的响应模型和行为。交付物 `/api/generate/{doc_type}` 不属于本 spec。

## 2. 路由与 HTTP 契约

```http
POST /api/chat/stream
Authorization: Bearer <JWT>
Content-Type: application/json
Accept: text/event-stream
```

### 2.1 请求模型

```python
class ChatStreamRequest(BaseModel):
    request_id: UUID
    session_id: str
    message: str
    history: list[dict] | None = None
    updates: list[dict] | None = None
```

校验规则：

- `request_id` 必须是合法 UUID 字符串。
- `message` 去除首尾空白后不得为空，长度上限沿用普通 `/api/chat` 的业务限制；若当前没有限制，第一版设置为 8,000 个 Unicode 字符。
- `session_id` 必须存在，且只能由会话 owner 或 admin 操作。
- `updates` 继续经过现有 `apply_updates` 校验，不能直接信任客户端字段值。
- `history` 只作为空数据库历史时的兼容 fallback；数据库消息仍是权威源。

校验、鉴权、会话错误发生在响应创建前，使用普通 JSON HTTP 错误：`401`、`403`、`404`、`409`、`422`。进入 SSE 后才使用 `error` 事件。

### 2.2 响应头

```python
StreamingResponse(
    event_generator(),
    media_type='text/event-stream',
    headers={
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
    },
)
```

部署层必须关闭 Nginx/网关响应缓冲和会把 SSE 合并的压缩策略；CORS 继续允许前端开发地址和 `Authorization`。

## 3. SSE 编码规范

事件格式：

```text
id: <request_id>:<sequence>\n
event: <event_name>\n
data: <one-line-json>\n
\n
```

`sequence` 从 `0` 开始，在一次响应内单调递增。服务端不发送原始模型事件。

### 3.1 事件结构

#### start

```json
{"request_id":"req-uuid","status":"started"}
```

#### delta

```json
{"text":"好的，我先记录品牌名。"}
```

只发送用户可见的文本增量。模型 thinking、tool input JSON、system prompt 不进入此事件。

#### status

```json
{"phase":"tool_call","message":"正在更新表单"}
```

`phase` 只能是 `generating | tool_call | persisting`；`message` 使用稳定短文案，不包含内部异常。

#### tool_event

字段沿用 `agent.tools.ToolEvent`：

```json
{"kind":"fill","section_id":"customer","field_id":"brand","value":"云裳"}
```

允许的 `kind` 是 `fill | skip | deliverable`。未使用的 `field_id`、`value` 使用空字符串或 `null`，不要把 SDK tool-use block 直接透传。

#### done

```json
{
  "request_id":"req-uuid",
  "reply":"好的，我先记录品牌名。请问您的联系人是？",
  "tool_events":[
    {"kind":"fill","section_id":"customer","field_id":"brand","value":"云裳"}
  ],
  "form_state": {},
  "form_complete": false,
  "suggestions": [],
  "assistant_message_id": 123
}
```

`form_state` 使用 `survey.state.to_dict()` 的现有结构；`suggestions` 使用现有 `ChatResponse.suggestions` 结构。`assistant_message_id` 是最终持久化消息的数据库 ID。

#### error

```json
{
  "request_id":"req-uuid",
  "code":"llm_unavailable",
  "message":"顾问暂时无法回复，请稍后重试。",
  "retryable":true,
  "phase":"generating"
}
```

错误码、文案和 retryable 取值必须遵循 PRD 第 8 节。事件发送后立即结束响应。

#### heartbeat

LLM 超过 10 秒没有业务事件时，每 15 秒发送：

```text
: heartbeat\n
\n
```

心跳不增加业务 sequence，不进入前端事件回调。

## 4. Agent 流式架构

新增异步 `run_agent_stream(...)`，职责是把一次 Agent turn 转成内部事件流；API 层负责鉴权、事件编码和最终持久化编排，不把 HTTP 对象传入 Agent。

推荐内部事件类型：

```python
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
    suggestions: list[dict]
```

处理顺序：

1. 从数据库读取最近历史，必要时生成较早摘要。
2. 应用客户端 `updates`，记录与普通 `/api/chat` 相同的前置 `ToolEvent`。
3. 第一轮仅允许 `fill_fields`，后续轮次按现有 `TOOL_DEFS` 和 `MAX_ITERATIONS` 执行。
4. 使用 Anthropic 兼容 SDK 的异步 streaming API；收集 text delta 时立即 yield `AgentStreamDelta`。
5. 一个模型 turn 完成后，读取完整 content blocks，解析 text 与 tool_use；如果需要工具，先 yield `tool_call` 状态，再执行现有 `execute_tool`。
6. 每个工具成功后 yield 安全 `AgentStreamToolEvent`，追加 tool result，继续下一轮模型 stream。
7. 达到 `end_turn` 后重算 section status、form complete、suggestions，返回 `AgentStreamResult`。
8. 超过 `MAX_ITERATIONS` 时沿用现有兜底回复，但仍必须产生正常 `done`，并在日志记录 `agent_max_iterations`。

### 4.1 LLM client

当前 `get_client()` 返回同步 `Anthropic`。流式实现新增异步 client（例如 `AsyncAnthropic`），使用独立的 `httpx.AsyncClient`、相同的 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 和超时策略。

要求：

- 上游 stream 事件只在 Agent 层转换，不在 API 层猜 SDK block 结构。
- 文本 delta 读取 SDK 的 text delta 事件；tool input 在一个模型 turn 完整结束后再解析和执行。
- 历史摘要也要使用异步调用，不能在异步生成器中阻塞式调用同步 LLM。
- `thinking` 继续关闭；即便上游返回 thinking 字段，也不得向前端发送。

## 5. API 生成器与事件顺序

`event_generator()` 应保证正常顺序：

```text
start
  → 0..n × status/delta/tool_event
  → status(persisting)
  → done
  → close
```

异常顺序：

```text
start
  → 0..n × 业务事件
  → error
  → close
```

开始发送 `start` 前完成 JWT、session、request_id 和幂等状态检查；开始发送后不要再抛出未编码的 FastAPI 异常。

`persisting` 状态只在 Agent 结果已经完整、即将执行最终事务时发送。`done` 必须在事务提交成功后发送。

## 6. 幂等与持久化

### 6.1 `chat_requests` 表

在 `backend/store/db.py` 中新增迁移式建表：

```sql
CREATE TABLE IF NOT EXISTS chat_requests (
    request_id       TEXT PRIMARY KEY,
    session_id       TEXT NOT NULL,
    user_id          INTEGER NOT NULL,
    message          TEXT NOT NULL,
    updates_json     TEXT,
    status           TEXT NOT NULL, -- running | completed | failed
    final_payload    TEXT,
    error_code       TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_chat_requests_session
    ON chat_requests(session_id);
```

`final_payload` 保存可直接还原 `done` 的 JSON，包括 `reply`、`tool_events`、`form_state`、`form_complete`、`suggestions` 和 `assistant_message_id`，不保存 JWT 或 LLM 原始响应。

### 6.2 状态规则

- 不存在：插入 `running`，开始本轮处理。
- `running`：相同 request 不允许并发执行，响应建立前返回 `409 request_in_progress`。
- `completed`：不调用 LLM，发送 `start` 和保存的 `done`，然后关闭。
- `failed`：仅在上次失败没有提交最终事务时允许同 request 重试，并更新为 `running`。
- 不同 user 或 session 复用 request_id：返回 `409 request_conflict`，不泄露原记录内容。

### 6.3 最终事务

Agent 正常完成后，用一次数据库事务完成：

1. 更新 `sessions.form_state` 和 `updated_at`。
2. 插入 user message。
3. 插入 assistant message 及 `tool_events` JSON。
4. 更新 `chat_requests.status = completed` 和 `final_payload`。

任一步失败都回滚，不发送 `done`，将 request 标记为 `failed`，发送 `persistence_failed`。客户端断开或任务取消时，不提交以上四步。

现有 `db.add_message()` 需要返回插入行 ID，或由新的事务函数返回 `assistant_message_id`；不能用时间或内容反推 ID。

## 7. 取消、断线与超时

- `StreamingResponse` 的异步生成器捕获 `asyncio.CancelledError`、客户端断开对应异常和上游取消异常。
- 捕获后取消当前 LLM stream context，停止后续 tool loop，将未完成 request 标记 `failed`，不写入半截消息。
- 用户主动 abort 不需要发送 `error`；如果连接在服务端已无法区分主动取消与网络断开，记录日志并统一作为未完成请求处理。
- LLM 总超时、单轮超时和心跳定时器必须可取消，不能在请求结束后遗留后台任务。
- 普通 `/api/chat` 的 402 余额错误继续返回现有 `503`；流接口在已经发送 `start` 后发 `llm_balance_insufficient`，在发送前失败则返回同等语义的 HTTP `503`。

## 8. 错误映射与日志

| 来源 | SSE code | HTTP（流未开始） | 日志要求 |
|---|---|---:|---|
| Anthropic 402 | `llm_balance_insufficient` | 503 | 记录 request/session/user，不记录 key 或响应原文 |
| 上游超时/网络 | `llm_unavailable` | 503 | 记录耗时、模型、上游状态 |
| tool 执行异常 | `tool_failed` | 500 | 记录 tool 名和安全摘要，不记录 prompt |
| 最终事务异常 | `persistence_failed` | 500 | 记录 request_id、事务阶段 |
| 相同 request running | `request_in_progress` | 409 | 记录冲突 request_id |
| 无终止事件断开 | `stream_interrupted` | 无 | 记录连接生命周期和已发 sequence |

服务端日志至少包含：`request_id`、`session_id`、`user_id`、`model`、首字时间、结束时间、已发 delta 数、工具次数、结束原因、错误码。禁止记录 Authorization、API key、系统提示词和完整客户敏感内容。

## 9. 测试与验收

### 单元测试

- LLM text delta 被转换成多个 `AgentStreamDelta`，顺序和内容一致。
- tool-use turn 先有 `status(tool_call)`，再有 `tool_event`，再继续后续文本。
- thinking 或未知 SDK 事件不会泄露到外部事件。
- 达到最大迭代后正常返回 `AgentStreamResult`。

### API 测试

- 未登录、session 不存在、越权、非法 request_id 返回预期 HTTP 状态。
- 正常 SSE 顺序为 start → delta/status/tool_event → persisting → done。
- 402、超时、工具异常、持久化异常分别映射稳定 error 事件。
- `done` 之后数据库只有一条 user message、一条 assistant message 和一条 completed request。
- 同 request completed 只回放 done，不再次调用 LLM。
- 同 request running 返回 409；不同 session/user 复用 request_id 不泄露记录。
- 客户端断开不保存半截消息和 form_state。
- 原有 `/api/chat` 测试全部保持通过。

### 部署验证

- 使用浏览器 fetch 能在回复完成前收到第一条 delta。
- Nginx/网关不会把事件缓冲到连接结束。
- 长时间无文本时仍能收到 heartbeat。
- 并发请求不会阻塞 FastAPI 事件循环或遗留 AsyncClient/定时任务。
