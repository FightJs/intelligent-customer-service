import { beforeEach, describe, expect, it } from 'vitest'
import {
  clearAllConversationSessions,
  getConversationSessionId,
  setConversationSessionId,
} from '../src/utils/conversationSession'

describe('conversationSession', () => {
  beforeEach(() => sessionStorage.clear())

  it('不同账号使用不同会话键', () => {
    setConversationSessionId(1, 'admin-session')
    setConversationSessionId(2, 'guest-session')

    expect(getConversationSessionId(1)).toBe('admin-session')
    expect(getConversationSessionId(2)).toBe('guest-session')
  })

  it('切换身份时清理新旧会话键但保留其他业务状态', () => {
    sessionStorage.setItem('ics_session_id', 'legacy-session')
    setConversationSessionId(1, 'admin-session')
    sessionStorage.setItem('unrelated', 'keep')

    clearAllConversationSessions()

    expect(sessionStorage.getItem('ics_session_id')).toBeNull()
    expect(getConversationSessionId(1)).toBeNull()
    expect(sessionStorage.getItem('unrelated')).toBe('keep')
  })
})
