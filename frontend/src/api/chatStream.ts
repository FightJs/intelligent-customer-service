import { API_BASE, clearAuth, getToken } from './client'
import type {
  FieldUpdate,
  Suggestion,
  ToolEvent,
} from './client'
import type { StudioFormState } from '../types/schema'

export interface ChatStreamRequest {
  request_id: string
  session_id: string
  message: string
  history?: { role: string; content: string }[]
  updates?: FieldUpdate[]
  images?: string[]
}

export type StreamPhase = 'generating' | 'tool_call' | 'persisting'

export interface StreamStartEvent {
  request_id: string
  status: 'started'
}

export interface StreamDeltaEvent {
  text: string
}

export interface StreamStatusEvent {
  phase: StreamPhase
  message: string
}

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
  phase: StreamPhase | 'transport'
}

export interface ChatStreamHandlers {
  onStart: (event: StreamStartEvent) => void
  onDelta: (event: StreamDeltaEvent) => void
  onStatus: (event: StreamStatusEvent) => void
  onToolEvent: (event: ToolEvent) => void
  onDone: (event: StreamDoneEvent) => void
  onError: (event: StreamErrorEvent) => void
}

export class ChatStreamHttpError extends Error {
  readonly status: number

  constructor(
    message: string,
    status: number,
  ) {
    super(message)
    this.status = status
    this.name = 'ChatStreamHttpError'
  }
}

export class ChatStreamInterruptedError extends Error {
  constructor() {
    super('连接中断，请重试。')
    this.name = 'ChatStreamInterruptedError'
  }
}

interface ParsedEvent {
  event: string
  data: string
}

export class SseParser {
  private buffer = ''

  push(text: string): ParsedEvent[] {
    this.buffer += text
    return this.takeCompleteEvents()
  }

  finish(): ParsedEvent[] {
    const events = this.takeCompleteEvents()
    if (this.buffer.trim()) {
      const event = parseSseEvent(this.buffer)
      if (event) events.push(event)
    }
    this.buffer = ''
    return events
  }

  private takeCompleteEvents(): ParsedEvent[] {
    const events: ParsedEvent[] = []
    let boundary: RegExpExecArray | null
    const separator = /\r?\n\r?\n/g
    let start = 0
    while ((boundary = separator.exec(this.buffer)) !== null) {
      const event = parseSseEvent(this.buffer.slice(start, boundary.index))
      if (event) events.push(event)
      start = boundary.index + boundary[0].length
    }
    this.buffer = this.buffer.slice(start)
    return events
  }
}

function parseSseEvent(block: string): ParsedEvent | null {
  let event = 'message'
  const data: string[] = []
  for (const line of block.split(/\r\n|\n|\r/)) {
    if (!line || line.startsWith(':')) continue
    const colon = line.indexOf(':')
    const field = colon === -1 ? line : line.slice(0, colon)
    const value = colon === -1 ? '' : line.slice(colon + 1).replace(/^ /, '')
    if (field === 'event') event = value
    if (field === 'data') data.push(value)
  }
  return data.length ? { event, data: data.join('\n') } : null
}

function dispatchEvent(
  parsed: ParsedEvent,
  handlers: ChatStreamHandlers,
): 'done' | 'error' | null {
  let data: unknown
  try {
    data = JSON.parse(parsed.data)
  } catch {
    console.warn('Ignoring malformed SSE payload', parsed.event)
    return null
  }

  switch (parsed.event) {
    case 'start': handlers.onStart(data as StreamStartEvent); return null
    case 'delta': handlers.onDelta(data as StreamDeltaEvent); return null
    case 'status': handlers.onStatus(data as StreamStatusEvent); return null
    case 'tool_event': handlers.onToolEvent(data as ToolEvent); return null
    case 'done': handlers.onDone(data as StreamDoneEvent); return 'done'
    case 'error': handlers.onError(data as StreamErrorEvent); return 'error'
    default:
      console.warn('Ignoring unknown SSE event', parsed.event)
      return null
  }
}

export async function streamChat(
  request: ChatStreamRequest,
  handlers: ChatStreamHandlers,
  signal: AbortSignal,
): Promise<void> {
  const token = getToken()
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(request),
    signal,
  })

  if (response.status === 401) {
    clearAuth()
    if (window.location.pathname !== '/login') window.location.href = '/login'
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: unknown }
    const detail = typeof body.detail === 'string' ? body.detail : response.statusText
    throw new ChatStreamHttpError(detail || `streamChat: ${response.status}`, response.status)
  }
  if (!response.body) throw new ChatStreamInterruptedError()

  const parser = new SseParser()
  const decoder = new TextDecoder('utf-8')
  const reader = response.body.getReader()
  let terminal = false

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      if (!value) continue
      for (const parsed of parser.push(decoder.decode(value, { stream: true }))) {
        const result = dispatchEvent(parsed, handlers)
        if (result) {
          terminal = true
          return
        }
      }
    }
    const tail = decoder.decode()
    const events = tail ? parser.push(tail) : []
    events.push(...parser.finish())
    for (const parsed of events) {
      const result = dispatchEvent(parsed, handlers)
      if (result) {
        terminal = true
        return
      }
    }
    if (!terminal) throw new ChatStreamInterruptedError()
  } finally {
    reader.releaseLock()
  }
}
