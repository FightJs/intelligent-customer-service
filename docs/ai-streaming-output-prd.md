# AI 对话流式输出 PRD

> 状态：实现前评审稿  
> 适用范围：直播间智能客服系统的聊天回复链路  
> 依据：[`docs/ai-streaming-output-research.md`](./ai-streaming-output-research.md)

## 1. 产品结论

新增 `POST /api/chat/stream`，使用 `fetch + ReadableStream` 消费 SSE 格式事件，让用户在模型生成过程中看到可展示的回复增量；保留现有 `POST /api/chat` 作为兼容和降级接口。

本次只改聊天文本输出链路，不改 `/api/generate/{doc_type}` 交付物下载流，不引入 WebSocket，也不向浏览器暴露模型隐藏思考、系统提示词、原始上游响应或异常堆栈。

## 2. 背景与问题

当前聊天流程要等 Agent 完成 LLM 调用、工具调用、状态计算和持久化后，前端才能收到完整 JSON。用户在首字出现前只能看到“思考中”，当模型或工具耗时较长时，容易误以为页面失效。

流式输出必须同时满足：

1. LLM SDK 使用真实 streaming API 产生文本增量。
2. FastAPI 持续把增量转发到 HTTP 响应，而不是把完整文本切片伪装成流。
3. 前端按事件边界解析网络字节流，并以最终快照校正临时 UI 状态。

## 3. 目标与非目标

### 3.1 目标

- 用户提交消息后，尽快看到第一段可展示文本。
- 回复增量顺序稳定、UTF-8 不乱码、不重复。
- `fill_fields`、`skip_section`、`generate_deliverable` 等工具事件可被前端识别，并在最终结果前提供阶段反馈。
- `done` 事件包含完整回复、完整表单状态、完成标记和建议项，作为最终一致性快照。
- 支持用户主动停止、服务端错误、网络中断和安全重试。
- 保持现有 JWT 鉴权、会话归属校验、数据库权威历史和普通 `/api/chat` 接口可用。
- 通过 `request_id` 保证重试不会重复写入同一轮用户消息或 assistant 消息。

### 3.2 非目标

- 不把模型思维链、工具原始参数、系统 prompt 或内部堆栈展示给用户。
- 不把交付物 Markdown、Excel、Word 下载改成聊天 SSE。
- 不实现 WebSocket、多人协作、服务端主动通知或 token 级断点回放。
- 不删除或立即废弃 `/api/chat`。

## 4. 用户故事与体验要求

### 4.1 正常对话

1. 用户发送一条消息。
2. 输入区进入发送中状态，避免同一会话并发提交。
3. AI 消息占位立即出现。
4. 收到 `delta` 后，AI 消息逐步显示 Markdown 文本；前端可按帧节流渲染。
5. 工具执行时显示简短状态，例如“正在更新表单”，不显示工具调用 JSON。
6. 收到 `done` 后，用完整 `reply` 替换临时文本，使用完整 `form_state` 更新进度卡，并恢复输入。

### 4.2 用户停止

用户点击“停止”后，前端调用当前请求的 `AbortController`。页面立即结束发送中状态，保留已经显示的临时文本并标记为未完成；后端停止 LLM stream 和后续工具循环，不写入半截 assistant 消息。

### 4.3 错误与重试

- 鉴权、会话不存在、无权访问、请求格式错误等发生在流建立前，继续使用普通 HTTP JSON 错误。
- 流已建立后发生的 LLM、工具、持久化错误，发送 `error` SSE 事件并关闭连接。
- 页面展示稳定的用户文案和“重试”入口；重试复用同一个 `request_id` 和原始请求内容。
- 已经成功完成但客户端没有收到 `done` 时，服务端按 `request_id` 回放最终 `done`，不得再次调用 LLM。

## 5. 产品范围与接口摘要

| 项目 | 约定 |
|---|---|
| 新接口 | `POST /api/chat/stream` |
| 内容类型 | 请求 `application/json`，响应 `text/event-stream` |
| 鉴权 | `Authorization: Bearer <JWT>` |
| 请求幂等键 | 客户端生成 UUID `request_id`，同一轮重试保持不变 |
| 兼容接口 | `POST /api/chat` 保留，返回现有一次性 JSON |
| 流结束 | 必须以 `done` 或 `error` 业务事件结束，然后关闭 HTTP 响应 |
| 心跳 | 空闲期间发送 SSE 注释 `: heartbeat`，不作为业务事件 |
| 事件序号 | `id: <request_id>:<sequence>`，从 `0` 开始递增 |

### 5.1 请求体

```json
{
  "request_id": "req_01JABC...",
  "session_id": "session-id",
  "message": "品牌名是云裳",
  "history": [],
  "updates": []
}
```

`history` 只保留现有客户端兼容能力；服务端优先使用数据库最近消息。`updates` 继续承载前端快捷选项的权威字段更新。

### 5.2 SSE 事件

每个事件使用 SSE 的 `event`、`id`、`data` 字段，`data` 是单行 JSON，事件之间以空行分隔。

| 事件 | 必填数据 | 用途 |
|---|---|---|
| `start` | `request_id`、`status` | 连接已接受，前端创建临时 AI 消息 |
| `delta` | `text` | 用户可见文本增量 |
| `status` | `phase`、`message` | 生成或工具执行阶段提示 |
| `tool_event` | `kind`、`section_id`，以及事件所需字段 | 表单/交付物事件的安全结构化通知 |
| `done` | `request_id`、`reply`、`tool_events`、`form_state`、`form_complete`、`suggestions` | 最终一致性快照 |
| `error` | `request_id`、`code`、`message`、`retryable`、`phase` | 可展示的失败状态 |

`done` 中的 `reply` 是完整回复，`tool_events` 是本轮全部工具事件，`form_state` 的结构与现有 `SessionResponse.form_state` 相同，`suggestions` 的结构与现有 `ChatResponse.suggestions` 相同。

## 6. 前后端职责

| 领域 | 前端职责 | 后端职责 |
|---|---|---|
| 请求 | 生成并保存 `request_id`，发送 JSON、JWT、`Accept` | 校验 JWT、会话存在性、归属和请求字段 |
| 流读取 | `fetch` 读取 `ReadableStream`，增量解码、解析 SSE、保留半包 | `StreamingResponse` 持续发送事件，关闭代理缓冲 |
| 文本 | 只拼接 `delta.text`，按帧更新临时 AI 消息 | 从 LLM streaming API 转发用户可见文本，不转发隐藏思考 |
| 工具 | 展示安全的阶段文案，消费 `tool_event` | 执行完整 Agent/tool-use 循环，生成结构化事件 |
| 状态 | `done.form_state` 作为最终快照替换本地状态 | 以数据库状态为权威，完成后计算最终表单状态 |
| 持久化 | 不把半成品写入本地正式消息历史 | 完成后原子保存 session、user message、assistant message、request 结果 |
| 取消 | `AbortController.abort()`，清理 loading 和 reader | 感知客户端断开，取消上游 LLM，避免继续执行 |
| 重试 | 复用同一 `request_id`、原 message 和 updates | completed 回放结果，running 拒绝并发，未完成请求可安全重试 |
| 安全 | 不渲染原始内部事件 | 脱敏错误、过滤内部字段、稳定化错误码 |
| 降级 | 配置关闭流式或能力不可用时调用 `/api/chat` | 保持 `/api/chat` 行为不变 |

## 7. 关键业务规则

1. 只有 `delta.text` 可以直接进入用户消息；`status` 和 `tool_event` 不得混入回复正文。
2. `done` 是唯一正式完成信号；仅收到 TCP/HTTP 关闭而没有 `done` 或 `error`，视为中断。
3. 服务端必须在最终 Agent 结果完整后再写入 assistant 消息和 session 状态。
4. 流中断时不得将半截回复当作完整 assistant 消息；工具对内存状态的修改也不得在未完成时提交到 session。
5. 同一 `request_id` 只能对应一个用户、一个 session、一个原始 message；不同用户复用已存在的 `request_id` 返回冲突。
6. 交付物下载仍按现有接口和权限执行，流式聊天中的 `deliverable` 事件只表示 Agent 触发了生成意图。

## 8. 错误码与用户文案

| code | 场景 | retryable | 默认文案 |
|---|---|---:|---|
| `llm_balance_insufficient` | 上游返回 402 | 否 | LLM 服务余额不足，请联系管理员充值后重试。 |
| `llm_unavailable` | 上游不可用或超时 | 是 | 顾问暂时无法回复，请稍后重试。 |
| `tool_failed` | 工具执行失败 | 是 | 表单更新失败，请重试本轮回答。 |
| `persistence_failed` | 最终保存失败 | 是 | 回复生成完成，但保存失败，请重试。 |
| `request_in_progress` | 相同请求正在执行 | 是 | 这条消息正在处理中，请稍候。 |
| `stream_interrupted` | 无终止事件的连接断开 | 是 | 连接中断，请重试。 |

内部异常只记录服务端日志，事件中的 `message` 不包含堆栈、密钥、Authorization、上游原文或系统 prompt。

## 9. 验收标准

### 功能

- [ ] 正常请求能在完整回复结束前收到至少一个 `delta`。
- [ ] 前端能够跨多个网络 chunk 正确解析一个 SSE 事件，中文和 Markdown 不乱码。
- [ ] `tool_event` 到达后，页面能显示阶段反馈；`done` 到达后表单状态与服务端快照一致。
- [ ] `done` 后输入恢复可用，且正式消息只出现一次。
- [ ] 点击停止后不再继续追加文本，后端不写入半截 assistant 消息。
- [ ] 余额不足、LLM 超时、工具失败、鉴权失败都有稳定行为和可读提示。
- [ ] 重试同一 `request_id` 不重复执行已完成请求或重复写入消息。
- [ ] 关闭流式开关后，旧 `/api/chat` 仍能完成完整对话。

### 性能与可靠性

- [ ] 首字时间、完成时间、取消率、错误码可记录。
- [ ] 代理不会缓冲到请求结束后才一次性转发。
- [ ] 至少覆盖 1 个长回复、1 个工具调用、1 个中文半包、1 个客户端取消和 1 个断线重试场景。

## 10. 分阶段交付

1. **协议验证**：后端发送固定测试事件，前端完成 parser、临时消息、停止和错误 UI；保留旧接口。
2. **真实 Agent 流**：接入 LLM streaming API，按事件驱动 tool-use 循环。
3. **一致性与观测**：加入 `chat_requests` 幂等记录、最终结果回放、指标和并发/代理压测。

## 11. 相关实现规范

- 前端：[`docs/frontend-docs/spec-ai-streaming-output.md`](./frontend-docs/spec-ai-streaming-output.md)
- 后端：[`docs/backend-docs/spec-ai-streaming-output.md`](./backend-docs/spec-ai-streaming-output.md)
- 调研：[`docs/ai-streaming-output-research.md`](./ai-streaming-output-research.md)
