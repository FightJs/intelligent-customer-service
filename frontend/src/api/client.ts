/**
 * 后端 API client。
 *
 * 封装：
 * - createSession: 创建会话，返回 session_id + 开场白
 * - streamChat: SSE 流式对话，回调式接收 token/tool/done 事件
 * - getSession: 跨会话恢复
 */
import type { StudioFormState, FieldValue, SectionId } from '../types/schema'

const API_BASE = 'http://localhost:8000/api'

export interface ToolEvent {
  kind: 'fill' | 'skip'
  section_id: SectionId
  field_id?: string
  value?: unknown
}

export interface SessionData {
  session_id: string
  form_state: StudioFormState
  greeting: string
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

export interface ChatCallbacks {
  onTool?: (events: ToolEvent[]) => void
  onToken?: (text: string) => void
  onDone?: (formState: StudioFormState, complete: boolean) => void
}

/**
 * 流式对话。用 fetch + ReadableStream 解析 SSE。
 * 返回 AI 完整回复文本。
 */
export async function streamChat(
  sessionId: string,
  message: string,
  history: { role: string; content: string }[] | undefined,
  cb: ChatCallbacks,
): Promise<string> {
  const resp = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, history }),
  })
  if (!resp.ok) throw new Error(`streamChat: ${resp.status}`)
  if (!resp.body) throw new Error('no response body')

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let fullReply = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE 按双换行分块
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() ?? ''

    for (const block of blocks) {
      const lines = block.split('\n')
      let event = ''
      let data = ''
      for (const line of lines) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) data += line.slice(5).trim()
      }
      if (!event || !data) continue

      if (event === 'tool') {
        const parsed = JSON.parse(data)
        cb.onTool?.(parsed.events)
      } else if (event === 'token') {
        const parsed = JSON.parse(data)
        fullReply += parsed.text
        cb.onToken?.(parsed.text)
      } else if (event === 'done') {
        const parsed = JSON.parse(data)
        cb.onDone?.(parsed.form_state, parsed.form_complete ?? false)
      }
    }
  }

  return fullReply
}

/**
 * 从 ToolEvent 列表提取字段更新，转为 reducer 可用的格式。
 */
export function eventsToFieldUpdates(
  events: ToolEvent[],
): { sectionId: SectionId; fieldId: string; value: FieldValue }[] {
  const updates: { sectionId: SectionId; fieldId: string; value: FieldValue }[] = []
  for (const e of events) {
    if (e.kind === 'fill' && e.field_id && e.value !== undefined) {
      // value 类型由后端决定，这里透传。后端保证与 schema 一致。
      // FieldValue 的 type 由现有 state 推断，但简化处理：直接用 any 透传。
      updates.push({
        sectionId: e.section_id,
        fieldId: e.field_id,
        value: e.value as FieldValue,
      })
    }
  }
  return updates
}
