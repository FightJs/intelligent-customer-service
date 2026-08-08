import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useFormState } from '../../state/FormContext'
import { createSession, chat } from '../../api/client'
import type { FieldUpdate, Suggestion, SuggestionOption } from '../../api/client'
import { SECTIONS } from '../../data/sections'
import MessageBubble from './MessageBubble'
import QuickChips from './QuickChips'

const MAX_INPUT_HEIGHT = 136

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

export // 字段 label 的常见中文前缀。匹配回复时去掉这些前缀，用剩余"实义"部分作为关键词，
// 避免"客户"、"场地"这类泛词误匹配。改 data/sections.ts 字段 label 时需同步复核此处。
const FIELD_PREFIXES = ['目标客群', '客户', '商品', '品牌', '直播间', '场地', '预算', '现有', '需求与']
const GENERIC_WORDS = ['目标', '客户', '商品', '品牌', '场地', '预算', '现有', '需求']

export function suggestionMatchesReply(suggestion: Suggestion, reply: string | undefined): boolean {
  if (!reply) return false
  const field = SECTIONS
    .find((section) => section.id === suggestion.section_id)
    ?.fields.find(({ id }) => id === suggestion.field_id)
  if (!field) return false

  const fieldTail = field.label.replace(new RegExp(`^(${FIELD_PREFIXES.join('|')})`), '')
  const firstKeyword = field.label.slice(0, 2)
  const keywords = [field.label, fieldTail, firstKeyword]
    .filter((keyword) => keyword.length > 1 && !GENERIC_WORDS.includes(keyword))

  if (keywords.some((keyword) => reply.includes(keyword))) return true
  const mentioned = suggestion.options.filter(({ label }) => label.length > 1 && reply.includes(label))
  return mentioned.length >= 2
}


export default function ChatPanel() {
  const { dispatch } = useFormState()
  const [sessionId, setSessionId] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [finished, setFinished] = useState(false)
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)
  const draftRef = useRef<HTMLTextAreaElement>(null)
  const sendingRef = useRef(false)

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

  useEffect(() => {
    const input = draftRef.current
    if (!input) return
    input.style.height = 'auto'
    input.style.height = `${Math.min(Math.max(input.scrollHeight, 40), MAX_INPUT_HEIGHT)}px`
    input.style.overflowY = input.scrollHeight > MAX_INPUT_HEIGHT ? 'auto' : 'hidden'
  }, [draft])

  const sendMessage = useCallback(async (text: string, updates?: FieldUpdate[]) => {
    if (!text || !sessionId || sendingRef.current) return

    sendingRef.current = true
    setMessages((prev) => [...prev, { id: newId(), role: 'user', text }])
    setDraft('')
    setSending(true)
    setSuggestions([])

    const history = messages
      .filter((m) => m.text)
      .slice(-6)
      .map((m) => ({ role: m.role === 'ai' ? 'assistant' : 'user', content: m.text }))

    try {
      const result = await chat(sessionId, text, history, updates)
      setMessages((prev) => [...prev, { id: newId(), role: 'ai', text: result.reply }])
      dispatch({ type: 'replace_state', state: result.form_state })
      setSuggestions(result.suggestions || [])
            setFinished(result.form_complete)
    } catch (err) {
      setMessages((prev) => [...prev, {
        id: newId(), role: 'ai', text: `（出错：${(err as Error).message}）`,
      }])
    } finally {
      sendingRef.current = false
      setSending(false)
    }
  }, [sessionId, messages, dispatch])

  const send = useCallback(() => {
    sendMessage(draft.trim())
  }, [draft, sendMessage])

  const latestReply = messages.at(-1)?.role === 'ai' ? messages.at(-1)?.text : undefined
  const suggestion = suggestions[0]
  const quickOptions = suggestion && suggestionMatchesReply(suggestion, latestReply)
    ? suggestion.options
    : []
  const pickQuickOption = useCallback((option: SuggestionOption) => {
    if (!suggestion) return
    sendMessage(option.label, [{
      section_id: suggestion.section_id,
      field_id: suggestion.field_id,
      value: option.value,
    }])
  }, [sendMessage, suggestion])

  return (
    <div className="h-full flex flex-col pt-1 px-2 pb-2">
      <div className="chat-surface flex-1 flex flex-col rounded-[12px] shadow-xl overflow-hidden">
        <div ref={scrollRef} className="chat-scrollbar flex-1 overflow-y-auto p-4">
          {loading && <div className="text-muted text-xs text-center">正在连接顾问…</div>}
          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role} text={m.text} aiAvatarSrc="/lit-blue.svg">
              {m.role === 'ai' ? (
                <div className="prose-chat">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
                </div>
              ) : (
                <div>{m.text}</div>
              )}
            </MessageBubble>
          ))}
          {sending && (
            <MessageBubble role="ai" text="思考中…" aiAvatarSrc="/lit-blue.svg">
              <div className="text-muted">思考中…</div>
            </MessageBubble>
          )}
          {finished && (
            <div className="text-done text-xs text-center mt-2">
              ✓ 必填信息已采集完成，请查看右上角客户需求表，确认后发送订单
            </div>
          )}
        </div>
        <div className="p-3 flex flex-col gap-2">
          <QuickChips
            options={quickOptions}
            onPick={pickQuickOption}
            disabled={sending || loading}
          />
          <div className="flex items-end gap-2">
            <div className="relative min-w-0 flex-1">
              <textarea
                ref={draftRef}
                rows={1}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
                placeholder={sending ? '顾问回复中…' : '输入您的回答…'}
                disabled={sending || loading}
                className="chat-input block w-full resize-none rounded-bubble py-2.5 pl-3.5 pr-11 text-sm leading-5 text-primary placeholder:text-muted outline-none focus:ring-1 focus:ring-accent disabled:opacity-50"
              />
              {draft && (
                <button
                  type="button"
                  onClick={() => setDraft('')}
                  className="chat-clear-button"
                  aria-label="清空输入"
                  title="清空输入"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                    <path d="m7 7 10 10M17 7 7 17" />
                  </svg>
                </button>
              )}
            </div>
            <button
              type="button"
              onClick={send}
              className="grid h-10 w-10 shrink-0 place-items-center rounded-bubble bg-accent text-white disabled:opacity-40"
              disabled={sending|| loading|| draft.trim() === ''}
              aria-label="发送"
              title="发送"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M12 19V5" />
                <path d="m5 12 7-7 7 7" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
