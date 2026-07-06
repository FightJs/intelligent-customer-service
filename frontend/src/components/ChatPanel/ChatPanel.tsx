import { useState, useRef, useEffect } from 'react'
import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import {
  initialMessages, currentStep, replyToCurrentStep, type ChatMessage,
} from './chatController'
import MessageBubble from './MessageBubble'
import ChoiceCard from './ChoiceCard'
import DimensionInput from './DimensionInput'
import ImageUpload from './ImageUpload'
import type { FieldDef, FieldValue, SectionId } from '../../types/schema'

interface ChatPanelProps {
  onComplete?: () => void
}

export default function ChatPanel({
  onComplete,
}: ChatPanelProps) {
  const { state, dispatch } = useFormState()
  const [messages, setMessages] = useState<ChatMessage[]>(() => initialMessages())
  const [draft, setDraft] = useState('')
  const [finished, setFinished] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const step = currentStep(messages)
  const fieldDef: FieldDef | undefined = step
    ? SECTIONS.find((s) => s.id === step.sectionId)?.fields.find((f) => f.id === step.fieldId)
    : undefined
  const sectionId: SectionId | undefined = step?.sectionId
  const fieldId = step?.fieldId
  const currentValue: FieldValue | undefined =
    sectionId && fieldId ? state.sections[sectionId].fields[fieldId] : undefined

  function updateValue(v: FieldValue) {
    if (!step) return
    dispatch({ type: 'update_field', sectionId: step.sectionId, fieldId: step.fieldId, value: v })
  }

  function commitAndAdvance(v: FieldValue) {
    if (!step) return
    dispatch({ type: 'update_field', sectionId: step.sectionId, fieldId: step.fieldId, value: v })
    const { userMsg, aiMessages, nextStep } = replyToCurrentStep(step, v)
    setMessages((prev) => [...prev, userMsg, ...aiMessages])
    if (nextStep) dispatch({ type: 'set_active_section', sectionId: nextStep.sectionId })
    else {
      dispatch({ type: 'complete' })
      setFinished(true)
      onComplete?.()
    }
  }

  function submitDraft() {
    if (!fieldDef || fieldDef.type !== 'text' || draft.trim() === '') return
    commitAndAdvance({ type: 'text', value: draft.trim() })
    setDraft('')
  }

  return (
    <div className="h-full flex flex-col pt-1 px-2 pb-2">
      <div className="flex-1 flex flex-col bg-black rounded-[12px] shadow-xl ring-1 ring-white/10 overflow-hidden">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
          {messages.map((m) => (
            <MessageBubble key={m.id} role={m.role}>
              <div>{m.text}</div>
              {m.kind === 'field' && m.fieldRef && fieldDef && m.fieldRef.fieldId === fieldId && currentValue && !finished && (
                <FieldInput def={fieldDef} value={currentValue} updateValue={updateValue} commitAndAdvance={commitAndAdvance} />
              )}
            </MessageBubble>
          ))}
        </div>
        <div className="p-3 flex gap-2">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submitDraft() }}
            placeholder={fieldDef?.type === 'text' ? '直接输入回答…' : '点击上方选项回答'}
            className="flex-1 bg-base rounded-bubble px-3.5 py-2.5 text-sm text-primary placeholder:text-muted outline-none focus:ring-1 focus:ring-accent"
          />
          <button
            type="button"
            onClick={submitDraft}
            className="px-4 py-2.5 bg-accent text-white rounded-bubble text-sm disabled:opacity-40"
            disabled={fieldDef?.type !== 'text' || draft.trim() === ''}
          >
            发送
          </button>
        </div>
      </div>
    </div>
  )
}

function FieldInput({
  def,
  value,
  updateValue,
  commitAndAdvance,
}: {
  def: FieldDef
  value: FieldValue
  updateValue: (v: FieldValue) => void
  commitAndAdvance: (v: FieldValue) => void
}) {
  const confirmClass = 'mt-2 px-3 py-1 text-xs rounded-pill bg-accent text-white disabled:opacity-40'

  switch (def.type) {
    case 'choice-single':
      return <ChoiceCard def={def} value={value} onCommit={commitAndAdvance} />
    case 'choice-multi': {
      const empty = value.type !== 'choice-multi' || value.value.length === 0
      return (
        <div>
          <ChoiceCard def={def} value={value} onCommit={updateValue} />
          <button type="button" className={confirmClass} disabled={empty} onClick={() => commitAndAdvance(value)}>
            确认
          </button>
        </div>
      )
    }
    case 'dimension': {
      const empty = value.type !== 'dimension' || Object.values(value.value).every((v) => v.trim() === '')
      return (
        <div>
          <DimensionInput def={def} value={value} onChange={updateValue} />
          <button type="button" className={confirmClass} disabled={empty} onClick={() => commitAndAdvance(value)}>
            确认
          </button>
        </div>
      )
    }
    case 'image': {
      const empty = value.type !== 'image' || value.value.length === 0
      return (
        <div>
          <ImageUpload value={value} onChange={updateValue} />
          <button type="button" className={confirmClass} disabled={empty} onClick={() => commitAndAdvance(value)}>
            确认
          </button>
        </div>
      )
    }
    default:
      return null
  }
}
