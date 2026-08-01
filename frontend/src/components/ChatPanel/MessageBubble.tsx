import { useState } from 'react'

interface Props {
  role: 'ai' | 'user'
  text: string
  aiAvatarSrc: string
  children: React.ReactNode
}

export default function MessageBubble({ role, text, aiAvatarSrc, children }: Props) {
  const isAi = role === 'ai'
  const [copied, setCopied] = useState(false)

  async function copyMessage() {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1400)
  }

  return (
    <div className={`message-row ${isAi ? 'is-ai' : 'is-user'}`}>
      {isAi && (
        <span className="message-avatar message-avatar-ai" aria-hidden="true">
          <img src={aiAvatarSrc} alt="" />
        </span>
      )}
      <div className={`message-bubble-wrap ${isAi ? 'is-ai' : 'is-user'}`}>
        <div className={`message-bubble ${isAi ? 'is-ai' : 'is-user'}`}>
          {children}
        </div>
        <button
          type="button"
          className="message-copy"
          onClick={copyMessage}
          aria-label={copied ? '已复制消息' : '复制消息'}
          title={copied ? '已复制' : '复制消息'}
        >
          {copied ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m5 12 4 4L19 6" /></svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>
          )}
        </button>
      </div>
      {!isAi && (
        <span className="message-avatar message-avatar-user" aria-hidden="true">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="4" /><path d="M4 20c0-4 4-6 8-6s8 2 8 6" /></svg>
        </span>
      )}
    </div>
  )
}
