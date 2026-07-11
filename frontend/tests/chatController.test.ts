import { describe, it, expect } from 'vitest'
import { initialMessages, currentStep, replyToCurrentStep, fieldToUserText } from '../src/components/ChatPanel/chatController'
import { visibleSteps } from '../src/data/scriptedFlow'
import { createInitialState } from '../src/state/initialState'
import type { StudioFormState } from '../src/types/schema'

function freshState(): StudioFormState {
  return createInitialState()
}

describe('initialMessages', () => {
  it('首条是文字开场白，第二条是第一个 field', () => {
    const state = freshState()
    const msgs = initialMessages(state)
    expect(msgs).toHaveLength(2)
    expect(msgs[0].role).toBe('ai')
    expect(msgs[0].kind).toBe('text')
    expect(msgs[1].kind).toBe('field')
    expect(msgs[1].fieldRef?.fieldId).toBe('brand')
  })
})

describe('currentStep', () => {
  it('返回最后一条 field 消息对应的 step', () => {
    const state = freshState()
    const msgs = initialMessages(state)
    const step = currentStep(msgs, state)
    expect(step?.fieldId).toBe('brand')
  })
})

describe('replyToCurrentStep', () => {
  it('回答后生成 user 消息 + AI 确认 + 下一个 field', () => {
    const state = freshState()
    const steps = visibleSteps(state)
    const step = steps[0]  // brand
    const value = { type: 'text' as const, value: '云裳' }
    const { userMsg, aiMessages, nextField } = replyToCurrentStep(step, value, state)
    expect(userMsg.role).toBe('user')
    expect(userMsg.text).toBe('云裳')
    expect(aiMessages.length).toBeGreaterThanOrEqual(2)
    expect(aiMessages[0].text).toBe('收到 ✓')
    expect(nextField?.fieldId).toBe('contact')  // brand 后是 contact
  })

  it('跨节时 AI 有过渡语', () => {
    const state = freshState()
    const steps = visibleSteps(state)
    // customer 最后一个必填字段是 source（第7个字段），下一个进 industry
    const customerLastStep = steps.filter((s) => s.sectionId === 'customer').slice(-1)[0]
    const value = { type: 'choice-single' as const, value: 'douyin' }
    const { aiMessages } = replyToCurrentStep(customerLastStep, value, state)
    const hasTransition = aiMessages.some((m) => m.text?.includes('行业与品类'))
    expect(hasTransition).toBe(true)
  })

  it('最后一个字段回答后 nextField 为 null', () => {
    const state = freshState()
    const steps = visibleSteps(state)
    const last = steps[steps.length - 1]
    const value = { type: 'text' as const, value: '无' }
    const { nextField } = replyToCurrentStep(last, value, state)
    expect(nextField).toBeNull()
  })
})

describe('fieldToUserText', () => {
  it('choice-single 显示 value', () => {
    expect(fieldToUserText({ type: 'choice-single', value: 'women' })).toBe('women')
  })
  it('dimension 拼接', () => {
    expect(fieldToUserText({ type: 'dimension', value: { 宽: '4', 深: '5', 高: '' } })).toBe('宽4×深5')
  })
})
