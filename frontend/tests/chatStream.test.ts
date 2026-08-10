import { beforeEach, describe, expect, it, vi } from 'vitest'
import { setAuth } from '../src/api/client'
import {
  ChatStreamInterruptedError,
  SseParser,
  streamChat,
} from '../src/api/chatStream'

const request = {
  request_id: '819ed3a2-0f35-4d8d-83ff-c8d4357e3940',
  session_id: 'session-1',
  message: '你好',
}

function handlers() {
  return {
    onStart: vi.fn(),
    onDelta: vi.fn(),
    onStatus: vi.fn(),
    onToolEvent: vi.fn(),
    onDone: vi.fn(),
    onError: vi.fn(),
  }
}

function readable(parts: Uint8Array[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      parts.forEach((part) => controller.enqueue(part))
      controller.close()
    },
  })
}

describe('SseParser', () => {
  it('支持 CRLF、多行 data 与不完整事件', () => {
    const parser = new SseParser()
    expect(parser.push('event: delta\r\ndata: {"text":"')).toEqual([])
    expect(parser.push('A"}\r\n\r\nevent: unknown\ndata: {}\n\n')).toEqual([
      { event: 'delta', data: '{"text":"A"}' },
      { event: 'unknown', data: '{}' },
    ])
  })
})

describe('streamChat', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
    setAuth('token-123', { id: 1, username: 'user-a', role: 'user' })
  })

  it('按 UTF-8 字节流解析中文 SSE，并携带鉴权请求头', async () => {
    const body = [
      'id: req:0\nevent: start\ndata: {"request_id":"req","status":"started"}\n\n',
      'id: req:1\nevent: delta\ndata: {"text":"云裳"}\n\n',
      'id: req:2\nevent: done\ndata: {"request_id":"req","reply":"云裳","tool_events":[],"form_state":{},"form_complete":false,"suggestions":[],"assistant_message_id":1}\n\n',
    ].join('')
    const bytes = new TextEncoder().encode(body)
    const cloud = new TextEncoder().encode('云')[0]
    const split = bytes.indexOf(cloud)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      body: readable([bytes.slice(0, split + 1), bytes.slice(split + 1)]),
    }))
    const eventHandlers = handlers()

    await streamChat(request, eventHandlers, new AbortController().signal)

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/chat/stream',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer token-123',
          Accept: 'text/event-stream',
        }),
      }),
    )
    expect(eventHandlers.onDelta).toHaveBeenCalledWith({ text: '云裳' })
    expect(eventHandlers.onDone).toHaveBeenCalledWith(expect.objectContaining({ reply: '云裳' }))
  })

  it('无 done/error 终止事件时抛出中断错误', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      body: readable([new TextEncoder().encode('event: delta\ndata: {"text":"半截"}\n\n')]),
    }))

    await expect(streamChat(request, handlers(), new AbortController().signal))
      .rejects.toBeInstanceOf(ChatStreamInterruptedError)
  })
})
