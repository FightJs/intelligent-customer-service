# 前端流式输出 Spec

> 对应 PRD：[`docs/ai-streaming-output-prd.md`](../ai-streaming-output-prd.md)  
> 目标：后续开发可直接按本文实现 React 聊天流式消费；本文不要求当前立即改代码。

## 1. 实现范围

本 spec 只覆盖聊天面板的流式消费，不覆盖登录、工作台布局、后台管理和交付物文件下载。

当前代码基线：

- API client：`frontend/src/api/client.ts`
- 聊天 UI：`frontend/src/components/ChatPanel/ChatPanel.tsx`
- 表单状态：`frontend/src/state/FormContext.tsx`、`frontend/src/state/reducer.ts`
- 现有降级接口：`POST /api/chat`

建议新增一个职责单一的 `frontend/src/api/chatStream.ts`，将 SSE 解析、请求生命周期和 ChatPanel 解耦；不把网络 buffer、JSON 解析和重试逻辑堆进页面组件。

## 2. 类型契约

### 2.1 请求

```ts
export interface ChatStreamRequest {
  request_id: string
  session_id: string
  message: string
  history?: { role: string; content: string }[]
  updates?: FieldUpdate[]
}
```

`FieldUpdate` 继续复用 `frontend/src/api/client.ts` 中的类型。`request_id` 在发送这一轮消息时生成 UUID；手动重试必须复用原值。

### 2.2 事件

```ts
export interface StreamStartEvent {
  request_id: string
  status: 'started'
}

export interface StreamDeltaEvent {
  text: string
}

export type StreamPhase = 'generating' | 'tool_call' | 'persisting'

export interface StreamStatusEvent {
  phase: StreamPhase
  message: string
}

export interface StreamToolEvent extends ToolEvent {}

export interface StreamDoneEvent {
  request_id: string
  reply: string
  tool_events: ToolEvent[]
  form_state: StudioFormState
  form_complete: boolean
  suggestions: Suggestion[]
  assistant_message_id: number
}

export type StreamErrorCode =
  | 'llm_balance_insufficient'
  | 'llm_unavailable'
  | 'tool_failed'
  | 'persistence_failed'
  | 'request_in_progress'
  | 'stream_interrupted'

export interface StreamErrorEvent {
  request_id: string
  code: StreamErrorCode
  message: string
  retryable: boolean
  phase: 'generating' | 'tool_call' | 'persisting' | 'transport'
}
```

SSE 的 `event` 值是 `start | delta | status | tool_event | done | error`。SSE `id` 只用于诊断和未来回放，不由前端推断业务状态。

## 3. API client 契约

建议暴露以下函数，具体名称可调整，但职责和入参出参保持不变：

```ts
export interface ChatStreamHandlers {
  onStart: (event: StreamStartEvent) => void
  onDelta: (event: StreamDeltaEvent) => void
  onStatus: (event: StreamStatusEvent) => void
  onToolEvent: (event: StreamToolEvent) => void
  onDone: (event: StreamDoneEvent) => void
  onError: (event: StreamErrorEvent) => void
}

export async function streamChat(
  request: ChatStreamRequest,
  handlers: ChatStreamHandlers,
  signal: AbortSignal,
): Promise<void>
```

请求必须使用现有 `request()` 的 JWT 注入规则：

```http
POST /api/chat/stream
Authorization: Bearer <ics_token>
Content-Type: application/json
Accept: text/event-stream
```

建立流前的非 2xx 响应不按 SSE 解析，使用现有 FastAPI `detail` 错误读取逻辑。`401` 仍清理登录态并跳转登录页。

## 4. SSE 解析器要求

解析器必须是独立、无 React 依赖的纯函数或小类，接收任意大小的文本片段并产出完整事件。

处理顺序：

1. `response.body.getReader()` 读取 `Uint8Array`。
2. 使用同一个 `TextDecoder('utf-8')` 调用 `decode(chunk, { stream: true })`。
3. 文本追加到跨 read 保留的 `buffer`。
4. 用空行分割完整 SSE 事件：同时支持 `\n\n` 和 `\r\n\r\n`。
5. 保留最后一个不完整片段，下一次继续拼接。
6. 逐行解析 `event:`、`id:`、`data:`；多行 `data:` 用 `\n` 拼接。
7. 对 `data` 执行一次 `JSON.parse`，按 `event` 分发给对应 handler。
8. 流结束时用 `decoder.decode()` flush buffer；若还有业务事件但没有终止空行，仍尝试解析最后一段。

约束：

- 不对每个 `reader.read()` 结果直接 `JSON.parse`。
- 未知事件记录开发日志并忽略，不得让整个流崩溃。
- `done` 或 `error` 后忽略后续事件并结束 loading。
- 连接自然关闭但没有 `done/error` 时，抛出 `stream_interrupted` 客户端错误。
- `AbortError` 只代表用户主动取消，不显示“网络错误”，但要统一清理请求状态。

## 5. ChatPanel 状态机

```text
idle
  └─ send → connecting
connecting
  ├─ start → streaming
  ├─ HTTP error → error
  └─ abort → cancelled
streaming
  ├─ delta/status/tool_event → streaming
  ├─ done → completed
  ├─ error → error
  └─ abort/network close → cancelled/error
completed/error/cancelled → idle
```

推荐状态字段：

```ts
type StreamUiState = {
  phase: 'idle' | 'connecting' | 'streaming' | 'completed' | 'error' | 'cancelled'
  requestId: string | null
  partialReply: string
  statusMessage: string | null
  error: StreamErrorEvent | null
}
```

同一个 ChatPanel 只能存在一个活动流。发送前保存 `request` 快照；重试不能重新从当前输入框拼装，也不能生成新的 `request_id`。

## 6. 消息渲染行为

1. 用户消息立即写入正式消息列表。
2. `start` 到达后插入一个临时 AI 消息，`text` 初始为空。
3. `delta.text` 追加到临时消息，不创建多个气泡。
4. Markdown 渲染允许按 `requestAnimationFrame` 或不超过 50ms 的节流批量更新，避免每个 token 触发完整树重渲染。
5. 代码围栏未闭合时仍交给现有 Markdown 渲染器处理，不自行截断文本。
6. `status` 只显示轻量的阶段提示，新的状态替换旧状态。
7. `tool_event` 只驱动安全的表单/进度 UI；不把 `value` 原样拼到聊天回复中。
8. `done.reply` 替换 `partialReply`，防止网络事件丢失导致正文缺字；`done.form_state` 通过 `dispatch({ type: 'replace_state', state })` 成为最终状态；`suggestions` 以 done 快照为准。
9. `error` 保留已生成文本，显示错误提示和重试入口，不把临时消息伪装成已完成消息。

## 7. 取消、重试与降级

### 7.1 取消

- 每次请求创建一个 `AbortController`，存入 ref。
- 停止按钮调用 `abort()`，清空 controller ref，恢复输入框。
- 不调用新的接口；服务端通过断开感知取消上游任务。
- 取消后的 partial AI 消息标记为 `interrupted`，历史提交时不能作为 assistant 正式历史发送。

### 7.2 重试

- 仅对 `retryable: true` 的错误显示重试。
- 重试使用相同 `request_id`、`session_id`、`message` 和 `updates`。
- 已有 partial 气泡先替换为同一条请求的重试状态，不再追加重复用户消息。
- 收到 `done` 后不允许再次重试该 request。

### 7.3 降级

使用 `VITE_CHAT_STREAMING_ENABLED` 控制能力开关：

- `true`：调用 `/api/chat/stream`。
- `false`：调用现有 `chat()`（`POST /api/chat`），按一次性结果更新现有 UI。
- 流接口在建立前返回 `404/405` 时，可在本轮提示后自动降级一次；不得在每个 token 或重试中无限切换。

## 8. 可访问性与交互约束

- 发送中按钮文案/aria-label 为“停止生成”，完成或错误后恢复“发送”。
- 临时 AI 消息应有 `aria-live="polite"`，不要把每个 token 以独立节点播报。
- 错误状态使用已有聊天错误样式，并提供明确的重试按钮。
- 自动滚动只在用户接近底部时执行；用户向上查看历史时不要强制拉回底部。
- `prefers-reduced-motion` 下不使用额外的逐字动画，保留内容更新本身。

## 9. 前端测试清单

### parser 单测

- 一个事件被拆成两个 byte chunk。
- 一个 chunk 包含多个事件。
- `\r\n`、`\n` 两种换行。
- UTF-8 中文字符跨 chunk。
- 多行 `data:`、未知事件、非法 JSON。
- `done/error` 后忽略事件。

### API client 单测

- 携带 JWT、JSON body 和 `Accept: text/event-stream`。
- 非 2xx JSON `detail` 转换为错误。
- `AbortController` 中止读取。
- 正常 `done`、服务端 `error`、无终止事件关闭分别返回正确状态。

### ChatPanel 集成测试

- start/delta/status/tool_event/done 的顺序更新单个 AI 气泡。
- done 快照覆盖 partial 文本和 form state。
- 点击停止不追加错误气泡、不触发重试。
- retryable error 可用同一 request_id 重试，消息不重复。
- streaming 开关关闭时仍走旧 `chat()`。
