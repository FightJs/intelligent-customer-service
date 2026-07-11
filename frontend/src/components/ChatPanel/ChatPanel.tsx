import { useState, useRef, useEffect, useCallback } from 'react'
import { useFormState } from '../../state/FormContext'
import { createSession, streamChat, eventsToFieldUpdates } from '../../api/client'
import MessageBubble from './MessageBubble'
import type { ChatMessage } from './chatController'

interface ChatPanelProps {
  onComplete?: () => void
}

let idCounter = 0
function newId(): string {
  idCounter += 1
  return `m${Date.now()}_${idCounter}`
}

export default function ChatPanel({ onComplete }: ChatPanelProps) {
  const { dispatch } = useFormState()
  const [sessionId, setSessionId] = useState<string>('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [streaming, setStreaming] = useState(false)
  const [finished, setFinished] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // 启动：创建会话 + 开场白
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    createSession()
      .then((data) => {
        if (cancelled) return
        setSessionId(data.session_id)
        setMessages([
          { id: newId(), role: 'ai', kind: 'text', text: data.greeting },
        ])
      })
      .catch((err) => {
        if (cancelled) return
        setMessages([
          { id: newId(), role: 'ai', kind: 'text', text: `连接失败：${err.message}` },
        ])
      })
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const send = useCallback(async () => {
    const text = draft.trim()
    if (!text || !sessionId || streaming) return

    // 立即显示用户消息
    setMessages((prev) => [...prev, { id: newId(), role: 'user', kind: 'text', text }])
    setDraft('')
    setStreaming(true)

    // 占位 AI 消息（流式填充）
    const aiMsgId = newId()
    setMessages((prev) => [...prev, { id: aiMsgId, role: 'ai', kind: 'text', text: '' }])

    // 对话历史（给后端）
    const history = messages
      .filter((m) => m.text)
      .slice(-6)
      .map((m) => ({ role: m.role === 'ai' ? 'assistant' : 'user', content: m.text || '' }))

    try {
      await streamChat(sessionId, text, history, {
        onTool: (events) => {
          // 更新表单字段
          for (const u of eventsToFieldUpdates(events)) {
            dispatch({ type: 'update_field', sectionId: u.sectionId, fieldId: u.fieldId, value: u.value })
          }
        },
        onToken: (tok) => {
          setMessages((prev) =>
            prev.map((m) => (m.id === aiMsgId ? { ...m, text: (m.text || '') + tok } : m)),
          )
        },
        onDone: (formState, complete) => {
          // 同步完整 form_state（后端是权威源）
          dispatch({ type: 'replace_state', state: formState })
          if (complete) {
            setFinished(true)
            onComplete?.()
          }
        },
      })
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiMsgId ? { ...m, text: `（出错：${(err as Error).message}）` } : m,
        ),
      )
    } finally {
      setStreaming(false)
    }
  }, [draft, sessionId, streaming, messages, dispatch, onComplete])

  return (
    <div className="h-full flex flex-col pt-1 px-2 pb-2">
      <div className="flex-1 flex flex-col bg-black rounded-[12px] shadow-xl ring-1 ring-white/10 overflow-hidden">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
          {loading && (
            <div className="text-muted text-xs text-center">正在连接顾问…</div>
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role}>
              <div>{m.text || (m.role === 'ai' ? '…' : '')}</div>
            </MessageBubble>
          ))}
          {finished && (
            <div className="text-done text-xs text-center mt-2">
              ✓ 信息采集完成，可在右侧查看交付物
            </div>
          )}
        </div>
        <div className="p-3 flex gap-2">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder={streaming ? '顾问回复中…' : '输入您的回答…'}
            disabled={streaming || loading || finished}
            className="flex-1 bg-base rounded-bubble px-3.5 py-2.5 text-sm text-primary placeholder:text-muted outline-none focus:ring-1 focus:ring-accent disabled:opacity-50"
          />
          <button
            type="button"
            onClick={send}
            className="px-4 py-2.5 bg-accent text-white rounded-bubble text-sm disabled:opacity-40"
            disabled={streaming || loading || finished || draft.trim() === ''}
          >
            发送
          </button>
        </div>
      </div>
    </div>
  )
}
