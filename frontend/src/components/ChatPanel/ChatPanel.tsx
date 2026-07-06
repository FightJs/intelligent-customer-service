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

export default function ChatPanel() {
  const { state, dispatch } = useFormState()
  const [messages, setMessages] = useState<ChatMessage[]>(() => initialMessages())
  const [draft, setDraft] = useState('')
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

  function commit(v: FieldValue) {
    if (!step) return
    dispatch({ type: 'update_field', sectionId: step.sectionId, fieldId: step.fieldId, value: v })
    const { userMsg, aiMessages, nextStep } = replyToCurrentStep(step, v)
    setMessages((prev) => [...prev, userMsg, ...aiMessages])
    if (nextStep) dispatch({ type: 'set_active_section', sectionId: nextStep.sectionId })
    else dispatch({ type: 'complete' })
  }

  function submitDraft() {
    if (!fieldDef || fieldDef.type !== 'text' || draft.trim() === '') return
    commit({ type: 'text', value: draft.trim() })
    setDraft('')
  }

  return (
    <div className="h-full flex flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
        {messages.map((m) => (
          <MessageBubble key={m.id} role={m.role}>
            <div>{m.text}</div>
            {m.kind === 'field' && m.fieldRef && fieldDef && m.fieldRef.fieldId === fieldId && currentValue && (
              <FieldInput def={fieldDef} value={currentValue} onCommit={commit} />
            )}
          </MessageBubble>
        ))}
      </div>
      <div className="border-t border-idle p-3 flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submitDraft() }}
          placeholder={fieldDef?.type === 'text' ? '直接输入回答…' : '点击上方选项回答'}
          className="flex-1 bg-surface rounded-bubble px-3.5 py-2.5 text-sm text-primary placeholder:text-muted outline-none focus:ring-1 focus:ring-accent"
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
  )
}

function FieldInput({ def, value, onCommit }: { def: FieldDef; value: FieldValue; onCommit: (v: FieldValue) => void }) {
  switch (def.type) {
    case 'choice-single':
    case 'choice-multi':
      return <ChoiceCard def={def} value={value} onCommit={onCommit} />
    case 'dimension':
      return <DimensionInput def={def} value={value} onChange={onCommit} />
    case 'image':
      return <ImageUpload value={value} onChange={onCommit} />
    default:
      return null
  }
}
