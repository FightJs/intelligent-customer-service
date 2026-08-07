import { beforeEach, describe, expect, it, vi } from 'vitest'
import { generateUrl, setAuth } from '../src/api/client'

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
})
