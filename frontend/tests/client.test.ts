import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  generateUrl,
  sendOrder,
  setAuth,
} from '../src/api/client'

describe('generateUrl', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('生成交付物时携带当前登录 token', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ status: 200, ok: true })
    vi.stubGlobal('fetch', fetchMock)
    setAuth('token-123', { id: 1, username: 'user-a', role: 'user' })

    await generateUrl('markdown', 'session-1')

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/generate/markdown?session_id=session-1',
      {
        method: 'POST',
        headers: { Authorization: 'Bearer token-123' },
      },
    )
  })

  it('需求表预览请求标记为 preview', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ status: 200, ok: true })
    vi.stubGlobal('fetch', fetchMock)
    setAuth('token-123', { id: 1, username: 'user-a', role: 'user' })

    await generateUrl('word', 'session-1', { preview: true })

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/generate/word?session_id=session-1&preview=true',
      {
        method: 'POST',
        headers: { Authorization: 'Bearer token-123' },
      },
    )
  })
})

describe('sendOrder', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('携带 token 和 session_id 发送订单', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: () => Promise.resolve({
        delivery_id: 7,
        sent: true,
        message: '订单发送成功',
      }),
    })

    vi.stubGlobal('fetch', fetchMock)

    setAuth(
      'token-123',
      {
        id: 1,
        username: 'user-a',
        role: 'user',
      },
    )

    await sendOrder('session-1')

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/orders',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer token-123',
        },
        body: JSON.stringify({
          session_id: 'session-1',
          allow_incomplete: false,
        }),
      },
    )
  })

  it('提前提交时发送 allow_incomplete 标记', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: () => Promise.resolve({ delivery_id: 8, sent: true, message: '已提交' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await sendOrder('session-early', true)

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      session_id: 'session-early',
      allow_incomplete: true,
    })
  })
})
