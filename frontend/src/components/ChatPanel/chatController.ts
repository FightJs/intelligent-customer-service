import type { FieldValue, SectionId, StudioFormState } from '../../types/schema'
import {
  visibleSteps, nextStep, transitionPrompt, firstStep, type ScriptedStep,
} from '../../data/scriptedFlow'

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

export function initialMessages(state: StudioFormState): ChatMessage[] {
  const first = firstStep(state)
  if (!first) {
    return [{ id: newId(), role: 'ai', kind: 'text', text: '所有信息已采集完成 ✓' }]
  }
  return [
    {
      id: newId(), role: 'ai', kind: 'text',
      text: '您好！我是直播间搭建顾问，接下来我会问您一系列问题，帮您梳理直播间搭建需求。右侧面板会实时显示采集进度。',
    },
    {
      id: newId(), role: 'ai', kind: 'field', text: first.prompt,
      fieldRef: { sectionId: first.sectionId, fieldId: first.fieldId },
    },
  ]
}

export function currentStep(messages: ChatMessage[], state: StudioFormState): ScriptedStep | null {
  const lastField = [...messages].reverse().find((m) => m.kind === 'field')
  if (!lastField || !lastField.fieldRef) return null
  const steps = visibleSteps(state)
  return steps.find((s) => s.fieldId === lastField.fieldRef!.fieldId) ?? null
}

export function fieldToUserText(v: FieldValue): string {
  switch (v.type) {
    case 'text': return v.value
    case 'choice-single': return v.value ?? ''
    case 'choice-multi': return v.value.join(', ')
    case 'dimension':
      return Object.entries(v.value).filter(([, n]) => n !== '').map(([k, n]) => `${k}${n}`).join('×')
    case 'image': return v.value.length ? `[${v.value.length}张图]` : ''
    case 'table': return v.value.length ? `[${v.value.length}行设备]` : ''
  }
}

export function replyToCurrentStep(
  step: ScriptedStep,
  value: FieldValue,
  state: StudioFormState,
): { userMsg: ChatMessage; aiMessages: ChatMessage[]; nextField: ScriptedStep | null } {
  const userMsg: ChatMessage = {
    id: newId(), role: 'user', kind: 'text', text: fieldToUserText(value),
  }
  const aiMessages: ChatMessage[] = []
  aiMessages.push({ id: newId(), role: 'ai', kind: 'text', text: '收到 ✓' })

  const ns = nextStep(step.fieldId, state)
  if (ns) {
    if (ns.sectionId !== step.sectionId) {
      aiMessages.push({
        id: newId(), role: 'ai', kind: 'text',
        text: transitionPrompt(step.sectionId, ns.sectionId),
      })
    }
    aiMessages.push({
      id: newId(), role: 'ai', kind: 'field', text: ns.prompt,
      fieldRef: { sectionId: ns.sectionId, fieldId: ns.fieldId },
    })
  } else {
    aiMessages.push({
      id: newId(), role: 'ai', kind: 'text',
      text: '信息采集完成 ✓ 您可以在右侧点击"生成方案"查看完整需求。',
    })
  }

  return { userMsg, aiMessages, nextField: ns }
}
