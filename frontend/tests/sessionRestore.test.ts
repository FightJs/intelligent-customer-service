import { beforeEach, describe, expect, it, vi } from 'vitest'

const getSession = vi.fn()
const getLatestSession = vi.fn()
const createSession = vi.fn()

vi.mock('../src/api/client', () => ({
  getSession: (...args: unknown[]) => getSession(...args),
  getLatestSession: (...args: unknown[]) => getLatestSession(...args),
  createSession: (...args: unknown[]) => createSession(...args),
}))

async function loadModule() {
  vi.resetModules()
  return import('../src/components/ChatPanel/ChatPanel')
}

const emptySession = {
  session_id: 'new',
  form_state: {},
  greeting: 'hi',
}

const filledSession = {
  session_id: 'filled',
  form_state: {},
  greeting: '',
  messages: [{ role: 'user', content: '云裳' }],
}

describe('restoreOrCreateSession', () => {
  beforeEach(() => {
    getSession.mockReset()
    getLatestSession.mockReset()
    createSession.mockReset()
  })

  it('本地会话有效时优先恢复', async () => {
    const { restoreOrCreateSession } = await loadModule()
    getSession.mockResolvedValue(filledSession)

    const data = await restoreOrCreateSession('local-id')

    expect(data.session_id).toBe('filled')
    expect(getSession).toHaveBeenCalledWith('local-id')
    expect(getLatestSession).not.toHaveBeenCalled()
    expect(createSession).not.toHaveBeenCalled()
  })

  it('本地会话失效时回捞服务端最近有内容会话', async () => {
    const { restoreOrCreateSession } = await loadModule()
    getSession.mockRejectedValue(new Error('session not found'))
    getLatestSession.mockResolvedValue(filledSession)

    const data = await restoreOrCreateSession('stale-id')

    expect(data.session_id).toBe('filled')
    expect(getLatestSession).toHaveBeenCalled()
    expect(createSession).not.toHaveBeenCalled()
  })

  it('无本地会话时优先最近有内容会话', async () => {
    const { restoreOrCreateSession } = await loadModule()
    getLatestSession.mockResolvedValue(filledSession)

    const data = await restoreOrCreateSession(null)

    expect(data.session_id).toBe('filled')
    expect(createSession).not.toHaveBeenCalled()
  })

  it('服务端也没有调研时才新建空会话', async () => {
    const { restoreOrCreateSession } = await loadModule()
    getLatestSession.mockRejectedValue(new Error('404'))
    createSession.mockResolvedValue(emptySession)

    const data = await restoreOrCreateSession(null)

    expect(data.session_id).toBe('new')
    expect(createSession).toHaveBeenCalledTimes(1)
  })

  it('StrictMode 并行创建只发一次 createSession', async () => {
    const { createSessionOnce } = await loadModule()
    let resolveCreate: (v: typeof emptySession) => void = () => {}
    createSession.mockReturnValue(new Promise((resolve) => {
      resolveCreate = resolve
    }))

    const p1 = createSessionOnce()
    const p2 = createSessionOnce()
    resolveCreate(emptySession)

    const [a, b] = await Promise.all([p1, p2])
    expect(a.session_id).toBe('new')
    expect(b.session_id).toBe('new')
    expect(createSession).toHaveBeenCalledTimes(1)
  })
})
