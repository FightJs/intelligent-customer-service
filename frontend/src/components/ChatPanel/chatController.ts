import type { FieldValue, SectionId } from '../../types/schema'
import { SCRIPTED_FLOW, stepAfter, transitionPrompt, type ScriptedStep } from '../../data/scriptedFlow'

export interface ChatMessage {
  id: string
  role: 'ai' | 'user'
  kind: 'text' | 'field'
  text?: string
  fieldRef?: { sectionId: SectionId; fieldId: string }
}

let idCounter = 0
function newId(): string {
  idCounter += 1
  return `m${Date.now()}_${idCounter}`
}

export function initialMessages(): ChatMessage[] {
  const first = SCRIPTED_FLOW[0]
  return [
    { id: newId(), role: 'ai', kind: 'text', text: '您好！我是直播间搭建顾问，接下来我会问您一系列问题，帮您梳理直播间搭建需求。右侧面板会实时显示采集进度。' },
    { id: newId(), role: 'ai', kind: 'field', text: first.prompt, fieldRef: { sectionId: first.sectionId, fieldId: first.fieldId } },
  ]
}

export function currentStep(messages: ChatMessage[]): ScriptedStep | null {
  const lastField = [...messages].reverse().find((m) => m.kind === 'field')
  if (!lastField || !lastField.fieldRef) return null
  return SCRIPTED_FLOW.find((s) => s.fieldId === lastField.fieldRef!.fieldId) ?? null
}

export function fieldToUserText(v: FieldValue): string {
  switch (v.type) {
    case 'text': return v.value
    case 'choice-single': return v.value ?? ''
    case 'choice-multi': return v.value.join(', ')
    case 'dimension':
      return Object.entries(v.value).filter(([, n]) => n !== '').map(([k, n]) => `${k}${n}`).join('×')
    case 'image': return v.value.length ? `[${v.value.length}张图]` : ''
  }
}

export function replyToCurrentStep(
  step: ScriptedStep,
  value: FieldValue,
): { userMsg: ChatMessage; aiMessages: ChatMessage[]; nextStep: ScriptedStep | null } {
  const userMsg: ChatMessage = {
    id: newId(), role: 'user', kind: 'text', text: fieldToUserText(value),
  }
  const aiMessages: ChatMessage[] = []
  aiMessages.push({ id: newId(), role: 'ai', kind: 'text', text: '收到 ✓' })

  const nextStep = stepAfter(step.fieldId)
  if (nextStep) {
    if (nextStep.sectionId !== step.sectionId) {
      aiMessages.push({ id: newId(), role: 'ai', kind: 'text', text: transitionPrompt(step.sectionId, nextStep.sectionId) })
    }
    aiMessages.push({
      id: newId(), role: 'ai', kind: 'field',
      text: nextStep.prompt, fieldRef: { sectionId: nextStep.sectionId, fieldId: nextStep.fieldId },
    })
  } else {
    aiMessages.push({ id: newId(), role: 'ai', kind: 'text', text: '信息采集完成 ✓ 您可以在右侧点击"生成方案"查看完整需求。' })
  }

  return { userMsg, aiMessages, nextStep }
}
