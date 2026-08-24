import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  ArrowUp,
  Camera,
  ImagePlus,
  Mic,
  SkipForward,
  Square,
  X,
} from 'lucide-react'
import {
  useSpeechRecognition,
} from '../../hooks/useSpeechRecognition'
import { useFormState } from '../../state/FormContext'
import { createSession, getSession, chat, skipCurrentQuestion } from '../../api/client'
import type { FieldUpdate, SessionMessage, Suggestion, SuggestionOption } from '../../api/client'
import type { StudioFormState } from '../../types/schema'
import type { CameraPetActivity } from '../CameraPet/types'
import {
  ChatStreamHttpError,
  ChatStreamInterruptedError,
  streamChat,
} from '../../api/chatStream'
import type {
  ChatStreamRequest,
  StreamErrorEvent,
} from '../../api/chatStream'
import { SECTIONS } from '../../data/sections'
import MessageBubble from './MessageBubble'
import QuickChips from './QuickChips'
import { suggestionOptionUpdate } from './suggestionUpdate'
import {
  getConversationSessionId,
  setConversationSessionId,
} from '../../utils/conversationSession'


const MAX_INPUT_HEIGHT = 136

const VOICE_WAVE_BARS = [8, 15, 11, 16]
const WAITING_STREAM_STATUSES = ['正在更新表单', '正在整理需求', '正在生成交付物']
const CHAT_MARKDOWN_COMPONENTS: Components = {
  p: ({ children }) => (
    <p className="whitespace-pre-line">{children}</p>
  ),
}

interface ChatMessage {
  id: string
  role: 'ai' | 'user'
  text: string
  images?: string[]
  partial?: boolean
  interrupted?: boolean
}

let idCounter = 0
function newId(): string {
  idCounter += 1
  return `m${Date.now()}_${idCounter}`
}

function toChatMessage(message: SessionMessage): ChatMessage {
  if (typeof message.content === 'string') {
    return { id: newId(), role: message.role === 'assistant' ? 'ai' : 'user', text: message.content }
  }
  const text = message.content
    .filter((block) => block.type === 'text')
    .map((block) => block.text ?? '')
    .join('')
  const images = message.content
    .filter((block) => block.type === 'image' && block.source)
    .map((block) => `data:${block.source!.media_type};base64,${block.source!.data}`)
  return { id: newId(), role: message.role === 'assistant' ? 'ai' : 'user', text, images }
}

function newRequestId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `request-${Date.now()}-${newId()}`
}

const STREAMING_ENABLED = import.meta.env.VITE_CHAT_STREAMING_ENABLED !== 'false'

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

export function toolEventStatus(kind: 'fill' | 'skip' | 'deliverable'): string {
  switch (kind) {
    case 'fill': return '正在更新表单'
    case 'skip': return '正在整理需求'
    case 'deliverable': return '正在生成交付物'
  }
}

interface ChatPanelProps {
  userId?: number
  userRole?: 'user' | 'admin' | 'guest'
  onPetActivityChange?: (activity: CameraPetActivity) => void
  onFinishEarly?: () => void
  canFinishEarly?: boolean
  conversationEnded?: boolean
}

export default function ChatPanel({
  userId = 0,
  userRole = 'user',
  onPetActivityChange,
  onFinishEarly,
  canFinishEarly = false,
  conversationEnded = false,
}: ChatPanelProps) {
  const { state, dispatch } = useFormState()
  const ended = conversationEnded || state.completed
  const [sessionId, setSessionId] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [finished, setFinished] = useState(false)
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [streamStatus, setStreamStatus] = useState<string | null>(null)
  const [streamError, setStreamError] = useState<StreamErrorEvent | null>(null)
  const [images, setImages] = useState<string[]>([])
  const [imageMenuOpen, setImageMenuOpen] = useState(false)
  const [speechError, setSpeechError] = useState('')
  const [imageError, setImageError] = useState('')
  const [actionError, setActionError] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const draftRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)
  const sendingRef = useRef(false)
  const controllerRef = useRef<AbortController | null>(null)
  const retryRef = useRef<{ request: ChatStreamRequest; messageId: string } | null>(null)
  const speechBaseRef = useRef('')

    const {
    supported: speechSupported,
    listening,
    startListening,
    stopListening,
  } = useSpeechRecognition({
    language: 'zh-CN',

    onTranscript: (transcript) => {
      const base = speechBaseRef.current

      setDraft(
        base
          ? `${base} ${transcript}`.trimEnd()
          : transcript,
      )
    },

    onError: setSpeechError,
  })

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    const savedId = getConversationSessionId(userId)
    const restore = savedId
      ? getSession(savedId).catch(() => createSession())
      : createSession()
    restore
      .then((data) => {
        if (cancelled) return
        setSessionId(data.session_id)
        dispatch({ type: 'replace_state', state: data.form_state })
        setConversationSessionId(userId, data.session_id)
        if (data.messages?.length) {
          setMessages(data.messages.map(toChatMessage))
          setFinished(data.form_complete ?? false)
        } else if (data.greeting) {
          setMessages([{ id: newId(), role: 'ai', text: data.greeting }])
        }
      })
      .catch((err) => {
        if (cancelled) return
        setMessages([{ id: newId(), role: 'ai', text: `连接失败：${err.message}` }])
      })
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [dispatch, userId])

  useEffect(() => {
    const el = scrollRef.current
    if (!el || el.scrollHeight - el.scrollTop - el.clientHeight > 96) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const input = draftRef.current
    if (!input) return
    input.style.height = 'auto'
    input.style.height = `${Math.min(Math.max(input.scrollHeight, 40), MAX_INPUT_HEIGHT)}px`
    input.style.overflowY = input.scrollHeight > MAX_INPUT_HEIGHT ? 'auto' : 'hidden'
  }, [draft])

  const runRequest = useCallback(async (
    request: ChatStreamRequest,
    options: { addUser: boolean; messageId?: string },
  ) => {
    if (sendingRef.current) return

    sendingRef.current = true
    setSending(true)
    setStreamError(null)
    setStreamStatus('正在连接顾问')
    setSuggestions([])
    if (options.addUser) setMessages((prev) => [...prev, { id: newId(), role: 'user', text: request.message, images: request.images }])

    const controller = new AbortController()
    controllerRef.current = controller
    let messageId = options.messageId
    let terminal = false

    const applyDone = (result: {
      reply: string
      form_state: StudioFormState
      suggestions: Suggestion[]
      form_complete: boolean
    }) => {
      terminal = true
      const id = messageId ?? newId()
      messageId = id
      setMessages((prev) => {
        const exists = prev.some((message) => message.id === id)
        const next = { id, role: 'ai' as const, text: result.reply }
        return exists ? prev.map((message) => message.id === id ? next : message) : [...prev, next]
      })
      dispatch({ type: 'replace_state', state: result.form_state })
      setSuggestions(result.suggestions || [])
      setFinished(result.form_complete)
      setStreamStatus(null)
      retryRef.current = null
    }

    try {
      if (!STREAMING_ENABLED) {
        applyDone(await chat(request.session_id, request.message, request.history, request.updates, request.images))
        return
      }

      await streamChat(request, {
        onStart: () => {
          const id = messageId ?? newId()
          messageId = id
          setMessages((prev) => prev.some((message) => message.id === id)
            ? prev.map((message) => message.id === id ? { ...message, text: '', partial: true, interrupted: false } : message)
            : [...prev, { id, role: 'ai', text: '', partial: true }])
        },
        onDelta: ({ text }) => {
          if (!messageId) return
          setMessages((prev) => prev.map((message) => message.id === messageId
            ? { ...message, text: message.text + text, partial: true }
            : message))
        },
        onStatus: ({ message }) => setStreamStatus(message),
        onToolEvent: ({ kind }) => setStreamStatus(toolEventStatus(kind)),
        onDone: applyDone,
        onError: (error) => {
          terminal = true
          setStreamStatus(null)
          setStreamError(error)
          if (messageId) {
            setMessages((prev) => prev.map((message) => message.id === messageId
              ? { ...message, partial: false, interrupted: true }
              : message))
            retryRef.current = { request, messageId }
          }
        },
      }, controller.signal)
    } catch (error) {
      if (controller.signal.aborted) return
      let requestError = error
      if (error instanceof ChatStreamHttpError && (error.status === 404 || error.status === 405)) {
        try {
          applyDone(await chat(request.session_id, request.message, request.history, request.updates, request.images))
          return
        } catch (fallbackError) {
          requestError = fallbackError
        }
      }
      const message = requestError instanceof Error ? requestError.message : String(requestError)
      const streamFailure: StreamErrorEvent = {
        request_id: request.request_id,
        code: requestError instanceof ChatStreamInterruptedError ? 'stream_interrupted' : 'llm_unavailable',
        message,
        retryable: true,
        phase: 'transport',
      }
      terminal = true
      setStreamStatus(null)
      setStreamError(streamFailure)
      if (messageId) {
        setMessages((prev) => prev.map((item) => item.id === messageId
          ? { ...item, partial: false, interrupted: true }
          : item))
        retryRef.current = { request, messageId }
      }
    } finally {
      if (controllerRef.current === controller) controllerRef.current = null
      sendingRef.current = false
      setSending(false)
      if (!terminal) setStreamStatus(null)
    }
  }, [dispatch])

  const sendMessage = useCallback((text: string, updates?: FieldUpdate[], msgImages?: string[]) => {
    if (
      (!text && !msgImages?.length)
      || !sessionId
      || sendingRef.current
      || actionLoading
      || ended
    ) return
    const history = messages
      .filter((message) => message.text && !message.interrupted)
      .slice(-6)
      .map((message) => ({ role: message.role === 'ai' ? 'assistant' : 'user', content: message.text }))
    setDraft('')
    setImages([])
    void runRequest({
      request_id: newRequestId(),
      session_id: sessionId,
      message: text,
      history,
      updates,
      images: msgImages,
    }, { addUser: true })
  }, [sessionId, messages, runRequest, actionLoading, ended])

  const stopStreaming = useCallback(() => {
    const controller = controllerRef.current
    if (!controller) return
    controller.abort()
    controllerRef.current = null
    sendingRef.current = false
    setSending(false)
    setStreamStatus(null)
    setMessages((prev) => prev.map((message) => message.partial
      ? { ...message, partial: false, interrupted: true }
      : message))
  }, [])

  const retryStreaming = useCallback(() => {
    const retry = retryRef.current
    if (!retry || sendingRef.current) return
    void runRequest(retry.request, { addUser: false, messageId: retry.messageId })
  }, [runRequest])

  const send = useCallback(() => {
    sendMessage(draft.trim(), undefined, images)
  }, [draft, images, sendMessage])

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) return
    setImageError('')
    const selected = Array.from(files).slice(0, 5)
    const valid = selected.filter((file) => (
      file.type.startsWith('image/')
      && file.size <= 10 * 1024 * 1024
    ))
    if (valid.length !== selected.length) {
      setImageError('仅支持 10MB 以内的图片文件')
    }
    void Promise.all(valid.map((file) => new Promise<string>((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result))
      reader.onerror = () => reject(new Error('图片读取失败'))
      reader.readAsDataURL(file)
    }))).then((loadedImages) => {
      setImages((previous) => [...previous, ...loadedImages].slice(0, 5))
    }).catch(() => {
      setImageError('图片读取失败，请重新选择')
    })
  }, [])

  const removeImage = useCallback((index: number) => {
    setImages((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const toggleSpeechInput = useCallback(() => {
    setSpeechError('')

    if (listening) {
      stopListening()
      draftRef.current?.focus()
      return
    }

    speechBaseRef.current = draft.trimEnd()
    startListening()
  }, [
    draft,
    listening,
    startListening,
    stopListening,
  ])

  useEffect(() => {
    if (!onPetActivityChange) return

    if (loading) {
      onPetActivityChange('waiting')
      return
    }

    if (sending) {
      const hasPartialOutput = messages.some((message) => (
        message.role === 'ai'
        && message.partial
        && message.text.length > 0
      ))
      const isToolWaiting = streamStatus !== null && WAITING_STREAM_STATUSES.includes(streamStatus)
      onPetActivityChange(
        isToolWaiting
          ? 'waiting'
          : hasPartialOutput
            ? 'output'
            : 'thinking',
      )
      return
    }

    onPetActivityChange('idle')
  }, [loading, messages, onPetActivityChange, sending, streamStatus])

  const latestReply = messages.at(-1)?.role === 'ai' ? messages.at(-1)?.text : undefined
  const suggestion = suggestions[0]
  const quickOptions = suggestion && suggestionMatchesReply(suggestion, latestReply)
    ? suggestion.options
    : []
  const pickQuickOption = useCallback((option: SuggestionOption) => {
    if (!suggestion) return
    sendMessage(option.label, [suggestionOptionUpdate(suggestion, option)], undefined)
  }, [sendMessage, suggestion])

  const currentSection = SECTIONS.find((section) => (
    section.id === state.currentSectionId
  ))
  const currentField = currentSection?.fields.find((field) => (
    field.id === state.currentFieldId
  ))
  const canSkipField = currentField?.skippable === true
  const canSkipSection = currentSection?.skippable === true
  const hasSkipAction = canSkipField || canSkipSection

  const handleSkip = useCallback(async (scope: 'field' | 'section') => {
    if (!sessionId || sendingRef.current || actionLoading) return
    if (draft.trim() || images.length > 0) {
      setActionError('当前还有未发送的回答或图片，请先发送或清空后再跳过。')
      return
    }
    setActionLoading(true)
    setActionError('')
    const userText = scope === 'field' ? '跳过当前问题' : '跳过当前模块'
    try {
      const result = await skipCurrentQuestion(sessionId, scope)
      dispatch({ type: 'replace_state', state: result.form_state })
      setMessages((previous) => [
        ...previous,
        { id: newId(), role: 'user', text: userText },
        { id: newId(), role: 'ai', text: result.reply },
      ])
      setDraft('')
      setImages([])
      setSuggestions([])
      setFinished(result.form_complete)
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : '跳过失败，请重试')
    } finally {
      setActionLoading(false)
    }
  }, [actionLoading, dispatch, draft, images.length, sessionId])

  const handleFinishEarly = useCallback(() => {
    if (!onFinishEarly) return
    if (draft.trim() || images.length > 0) {
      setActionError('当前还有未发送的回答或图片，请先发送或清空后再提前提交。')
      return
    }
    setActionError('')
    onFinishEarly()
  }, [draft, images.length, onFinishEarly])

  return (
    <div className="h-full flex flex-col pt-1 px-2 pb-2">
      <div className="chat-surface flex-1 flex flex-col rounded-[12px] shadow-xl overflow-hidden">
        {(hasSkipAction || (canFinishEarly && onFinishEarly)) && !ended && (
          <div className="flex flex-wrap justify-end gap-2 border-b border-outline/40 px-4 py-2">
            {canSkipField && (
              <button
                type="button"
                onClick={() => void handleSkip('field')}
                disabled={loading || sending || listening || actionLoading}
                className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/60 bg-amber-400/15 px-3 py-1.5 text-xs font-semibold text-amber-700 transition hover:bg-amber-400/25 disabled:opacity-40 dark:text-amber-300"
              >
                <SkipForward size={14} aria-hidden="true" />
                跳过此题
              </button>
            )}
            {canSkipSection && (
              <button
                type="button"
                onClick={() => void handleSkip('section')}
                disabled={loading || sending || listening || actionLoading}
                className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/60 bg-amber-400/15 px-3 py-1.5 text-xs font-semibold text-amber-700 transition hover:bg-amber-400/25 disabled:opacity-40 dark:text-amber-300"
              >
                <SkipForward size={14} aria-hidden="true" />
                跳过本模块
              </button>
            )}
            {canFinishEarly && onFinishEarly && (
              <button
                type="button"
                onClick={handleFinishEarly}
                disabled={loading || sending || listening || actionLoading}
                className="rounded-full border border-outline px-3 py-1.5 text-xs font-medium text-secondary transition hover:border-danger/50 hover:text-danger disabled:opacity-40"
              >
                提前结束并提交
              </button>
            )}
          </div>
        )}
        <div ref={scrollRef} className="chat-scrollbar flex-1 overflow-y-auto p-4">
          {loading && <div className="text-muted text-xs text-center">正在连接顾问…</div>}
          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role} text={m.text} aiAvatarSrc="/logo.svg">
              {m.role === 'ai' ? (
                <div className="prose-chat" aria-live={m.partial ? 'polite' : undefined}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={CHAT_MARKDOWN_COMPONENTS}
                  >
                    {m.text}
                  </ReactMarkdown>
                  {m.interrupted && <p className="mt-2 text-xs text-muted">回复未完成</p>}
                </div>
              ) : (
                <div>
                  {m.images && m.images.length > 0 && (
                    <div className="flex gap-1.5 flex-wrap mb-1">
                      {m.images.map((uri, i) => (
                        <img key={i} src={uri} alt="" className="h-20 max-w-[160px] rounded-lg object-cover border border-outline/60" />
                      ))}
                    </div>
                  )}
                  {m.text && <div>{m.text}</div>}
                </div>
              )}
            </MessageBubble>
          ))}
          {sending && streamStatus && <div className="mt-2 text-center text-xs text-muted">{streamStatus}</div>}
          {streamError && (
            <div role="alert" className="mt-3 flex items-center justify-between gap-3 rounded-card border border-danger/40 bg-danger/10 px-3 py-2 text-xs text-danger">
              <span>{streamError.message}</span>
              {streamError.retryable && retryRef.current && (
                <button type="button" onClick={retryStreaming} className="shrink-0 font-semibold text-danger underline underline-offset-2">
                  重试
                </button>
              )}
            </div>
          )}
          {actionError && (
            <div role="alert" className="mt-3 rounded-card border border-danger/40 bg-danger/10 px-3 py-2 text-xs text-danger">
              {actionError}
            </div>
          )}
          {finished && !ended && userRole === 'guest' && (
            <div className="text-done text-xs text-center mt-2">
              ✓ 简约体验已完成，可点击右上角客户需求表查看结果；登录或注册正式账号可体验订单提交等完整功能
            </div>
          )}
          {finished && !ended && userRole !== 'guest' && (
            <div className="text-done text-xs text-center mt-2">
              ✓ 必填信息已采集完成，请查看右上角客户需求表，确认后发送订单
            </div>
          )}
          {ended && (
            <div className="mt-3 rounded-card border border-done/40 bg-done/10 px-3 py-2 text-center text-xs text-done">
              本次调研已提交，如需补充请开始新的调研。
            </div>
          )}
        </div>
        <div className="p-3 flex flex-col gap-2">
          <QuickChips
            options={quickOptions}
            onPick={pickQuickOption}
            disabled={sending || loading || listening || actionLoading || ended}
          />

          {images.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              {images.map((uri, i) => (
                <div key={i} className="relative group flex-shrink-0">
                  <img src={uri} alt="" className="h-10 w-10 rounded-lg object-cover border border-outline/60" />
                  <button
                    type="button"
                    onClick={() => removeImage(i)}
                    className="absolute -top-1.5 -right-1.5 grid h-4 w-4 place-items-center rounded-full bg-active-surface text-secondary opacity-0 group-hover:opacity-100 transition-opacity"
                    aria-label="移除图片"
                  >
                    <X size={10} />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-end gap-2">
            <div className="relative min-w-0 flex-1">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                multiple
                className="hidden"
                onChange={(event) => {
                  handleFiles(event.target.files)
                  event.target.value = ''
                  setImageMenuOpen(false)
                }}
              />
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                capture="environment"
                className="hidden"
                onChange={(event) => {
                  handleFiles(event.target.files)
                  event.target.value = ''
                  setImageMenuOpen(false)
                }}
              />
              <textarea
                ref={draftRef}
                rows={1}
                value={draft}
                onChange={(event) => {
                  setDraft(event.target.value)

                  if (speechError) {
                    setSpeechError('')
                  }
                }}
                onKeyDown={(event) => {
                  if (
                    event.key === 'Enter'
                    && !event.shiftKey
                    && !listening
                  ) {
                    event.preventDefault()
                    if (!sending) {
                      send()
                    }
                  }
                }}
                placeholder={
                  listening
                    ? '正在聆听，请再次点击麦克风结束…'
                    : sending
                      ? `${streamStatus ?? '正在处理'}，请稍候…`
                      : '输入您的回答…'
                }
                disabled={sending || loading || actionLoading || ended}
                readOnly={listening}
                className="chat-input block w-full resize-none rounded-bubble py-2.5 pl-3.5 pr-11 text-sm leading-5 text-primary placeholder:text-muted outline-none focus:ring-1 focus:ring-accent disabled:opacity-50"
              />

              {draft && !listening && (
                <button
                  type="button"
                  onClick={() => setDraft('')}
                  className="chat-clear-button"
                  aria-label="清空输入"
                  title="清空输入"
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    aria-hidden="true"
                  >
                    <path d="m7 7 10 10M17 7 7 17" />
                  </svg>
                </button>
              )}

            </div>

            <div className="relative shrink-0">
              <button
                type="button"
                onClick={() => setImageMenuOpen((open) => !open)}
                disabled={loading || sending || listening || actionLoading || ended || images.length >= 5}
                className="grid h-10 w-9 place-items-center rounded-bubble text-muted hover:text-primary disabled:opacity-30 transition-colors"
                aria-label="添加图片"
                aria-haspopup="menu"
                aria-expanded={imageMenuOpen}
                title="添加图片（拍照或从相册选择，最多 5 张）"
              >
                <ImagePlus size={18} aria-hidden="true" />
              </button>

              {imageMenuOpen && (
                <div
                  role="menu"
                  aria-label="图片添加方式"
                  className="absolute bottom-full right-0 z-20 mb-2 min-w-36 overflow-hidden rounded-card border border-outline bg-surface p-1 shadow-xl"
                >
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setImageMenuOpen(false)
                      fileInputRef.current?.click()
                    }}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs text-primary hover:bg-active-surface"
                  >
                    <ImagePlus size={16} aria-hidden="true" />
                    从相册选择
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setImageMenuOpen(false)
                      cameraInputRef.current?.click()
                    }}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs text-primary hover:bg-active-surface"
                  >
                    <Camera size={16} aria-hidden="true" />
                    拍照
                  </button>
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={toggleSpeechInput}
              disabled={
                loading
                || sending
                || actionLoading
                || ended
              }
              className={
                `voice-input-button${listening ? ' is-listening' : ''
                }`
              }
              aria-label={
                listening
                  ? '停止语音输入'
                  : '开始语音输入'
              }
              aria-pressed={listening}
              title={
                !speechSupported
                  ? '当前浏览器不支持语音输入'
                  : listening
                    ? '停止语音输入'
                    : '开始语音输入'
              }
            >
              {listening ? (
                <span
                  className="voice-listening-indicator"
                  data-testid="voice-listening-indicator"
                  aria-hidden="true"
                >
                  {VOICE_WAVE_BARS.map((height, index) => (
                    <span
                      key={height}
                      className="voice-listening-bar"
                      style={{
                        height: `${height}px`,
                        animationDelay: `${index * 0.1}s`,
                      }}
                    />
                  ))}
                </span>
              ) : (
                <Mic
                  size={18}
                  aria-hidden="true"
                />
              )}
            </button>

            <button
              type="button"
              onClick={
                sending
                  ? stopStreaming
                  : send
              }
              className="grid h-10 w-10 shrink-0 place-items-center rounded-bubble bg-accent text-white disabled:opacity-40"
              disabled={
                loading
                || listening
                || actionLoading
                || ended
                || (
                  !sending
                  && draft.trim() === ''
                  && images.length === 0
                )
              }
              aria-label={
                sending ? '停止生成' : '发送'
              }
              title={
                sending ? '停止生成' : '发送'
              }
            >
              {sending ? (
                <Square
                  size={16}
                  fill="currentColor"
                  aria-hidden="true"
                />
              ) : (
                <ArrowUp
                  size={18}
                  aria-hidden="true"
                />
              )}
            </button>
          </div>

          {listening && (
            <p
              className="voice-input-status"
              aria-live="polite"
            >
              正在收音，再次点击结束
            </p>
          )}

          {speechError && (
            <p
              role="alert"
              className="voice-input-error"
            >
              {speechError}
            </p>
          )}
          {imageError && (
            <p role="alert" className="voice-input-error">
              {imageError}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
