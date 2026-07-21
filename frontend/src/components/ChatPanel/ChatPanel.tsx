import { useState, useRef, useEffect, useCallback } from 'react'
import { useFormState } from '../../state/FormContext'
import { createSession, chat } from '../../api/client'
import type { Suggestion } from '../../api/client'
import MessageBubble from './MessageBubble'
import QuickChips from './QuickChips'

interface ChatMessage {
  id: string
  role: 'ai' | 'user'
  text: string
}

let idCounter = 0
function newId(): string {
  idCounter += 1
  return `m${Date.now()}_${idCounter}`
}

interface ChatPanelProps {
  onComplete?: () => void
}

export default function ChatPanel({ onComplete }: ChatPanelProps) {
  const { dispatch } = useFormState()
  const [sessionId, setSessionId] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [finished, setFinished] = useState(false)
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    createSession()
      .then((data) => {
        if (cancelled) return
        setSessionId(data.session_id)
        sessionStorage.setItem('ics_session_id', data.session_id)
        setMessages([{ id: newId(), role: 'ai', text: data.greeting }])
      })
      .catch((err) => {
        if (cancelled) return
        setMessages([{ id: newId(), role: 'ai', text: `连接失败：${err.message}` }])
      })
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const sendMessage = useCallback(async (text: string) => {
    if (!text || !sessionId || sending) return

    setMessages((prev) => [...prev, { id: newId(), role: 'user', text }])
    setDraft('')
    setSending(true)
    setSuggestions([])

    const history = messages
      .filter((m) => m.text)
      .slice(-6)
      .map((m) => ({ role: m.role === 'ai' ? 'assistant' : 'user', content: m.text }))

    try {
      const result = await chat(sessionId, text, history)
      setMessages((prev) => [...prev, { id: newId(), role: 'ai', text: result.reply }])
      dispatch({ type: 'replace_state', state: result.form_state })
      setSuggestions(result.suggestions || [])
      if (result.form_complete) {
        setFinished(true)
        onComplete?.()
      }
    } catch (err) {
      setMessages((prev) => [...prev, {
        id: newId(), role: 'ai', text: `（出错：${(err as Error).message}）`,
      }])
    } finally {
      setSending(false)
    }
  }, [sessionId, sending, messages, dispatch, onComplete])

  const send = useCallback(() => {
    sendMessage(draft.trim())
  }, [draft, sendMessage])

  return (
    <div className="h-full flex flex-col pt-1 px-2 pb-2">
      <div className="flex-1 flex flex-col bg-black rounded-[12px] shadow-xl ring-1 ring-white/10 overflow-hidden">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
          {loading && <div className="text-muted text-xs text-center">正在连接顾问…</div>}
          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role}>
              <div>{m.text}</div>
            </MessageBubble>
          ))}
          {sending && (
            <MessageBubble role="ai">
              <div className="text-muted">思考中…</div>
            </MessageBubble>
          )}
          {finished && (
            <div className="text-done text-xs text-center mt-2">
              ✓ 信息采集完成，可在右侧查看交付物
            </div>
          )}
        </div>
        <div className="p-3 flex flex-col gap-2">
          <QuickChips
            options={suggestions[0]?.options || []}
            onPick={(o) => sendMessage(o.label)}
            disabled={sending || loading || finished}
          />
          <div className="flex gap-2">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
              placeholder={sending ? '顾问回复中…' : '输入您的回答…'}
              disabled={sending || loading || finished}
              className="flex-1 bg-base rounded-bubble px-3.5 py-2.5 text-sm text-primary placeholder:text-muted outline-none focus:ring-1 focus:ring-accent disabled:opacity-50"
            />
            <button
              type="button"
              onClick={send}
              className="px-4 py-2.5 bg-accent text-white rounded-bubble text-sm disabled:opacity-40"
              disabled={sending || loading || finished || draft.trim() === ''}
            >
              发送
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
