const SESSION_KEY_PREFIX = 'ics_session_id'

export function conversationSessionKey(userId: number): string {
  return `${SESSION_KEY_PREFIX}:${userId}`
}

export function getConversationSessionId(userId: number): string | null {
  return sessionStorage.getItem(conversationSessionKey(userId))
}

export function setConversationSessionId(userId: number, sessionId: string): void {
  sessionStorage.setItem(conversationSessionKey(userId), sessionId)
}

export function clearConversationSession(userId: number): void {
  sessionStorage.removeItem(conversationSessionKey(userId))
}

export function clearAllConversationSessions(): void {
  for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
    const key = sessionStorage.key(index)
    if (key === SESSION_KEY_PREFIX || key?.startsWith(`${SESSION_KEY_PREFIX}:`)) {
      sessionStorage.removeItem(key)
    }
  }
}
