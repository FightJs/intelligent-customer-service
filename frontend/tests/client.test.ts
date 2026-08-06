import { beforeEach, describe, expect, it, vi } from 'vitest'
import { chat, generateUrl, setAuth } from '../src/api/client'

describe('API client', () => {
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

  it('聊天接口返回服务端 detail 时保留明确错误信息', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      status: 503,
      ok: false,
      json: async () => ({ detail: 'LLM 服务余额不足，请联系管理员充值后重试。' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    setAuth('token-123', { id: 1, username: 'user-a', role: 'user' })

    await expect(chat('session-1', '你好', [])).rejects.toThrow(
      'LLM 服务余额不足，请联系管理员充值后重试。',
    )
  })
})
