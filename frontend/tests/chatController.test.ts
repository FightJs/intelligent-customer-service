import { describe, it, expect } from 'vitest'
import { initialMessages, currentStep, replyToCurrentStep, fieldToUserText } from '../src/components/ChatPanel/chatController'
import { SCRIPTED_FLOW } from '../src/data/scriptedFlow'

describe('initialMessages', () => {
  it('首条是文字开场白，第二条是第一个 field', () => {
    const msgs = initialMessages()
    expect(msgs).toHaveLength(2)
    expect(msgs[0].role).toBe('ai')
    expect(msgs[0].kind).toBe('text')
    expect(msgs[1].kind).toBe('field')
    expect(msgs[1].fieldRef?.fieldId).toBe('brand')
  })
})

describe('currentStep', () => {
  it('返回最后一条 field 消息对应的 step', () => {
    const msgs = initialMessages()
    const step = currentStep(msgs)
    expect(step?.fieldId).toBe('brand')
  })
})

describe('replyToCurrentStep', () => {
  it('回答后生成 user 消息 + AI 确认 + 下一个 field', () => {
    const step = SCRIPTED_FLOW[0]  // brand
    const value = { type: 'text' as const, value: '云裳' }
    const { userMsg, aiMessages, nextStep } = replyToCurrentStep(step, value)
    expect(userMsg.role).toBe('user')
    expect(userMsg.text).toBe('云裳')
    expect(aiMessages.length).toBeGreaterThanOrEqual(2)
    expect(aiMessages[0].text).toBe('收到 ✓')
    expect(nextStep?.fieldId).toBe('phone')
  })

  it('跨节时 AI 有过渡语', () => {
    // phone 是 customer 最后一个，下一个是 industry
    const phoneStep = SCRIPTED_FLOW[1]
    const value = { type: 'text' as const, value: '138****' }
    const { aiMessages } = replyToCurrentStep(phoneStep, value)
    const hasTransition = aiMessages.some((m) => m.text?.includes('行业品类'))
    expect(hasTransition).toBe(true)
  })

  it('最后一个字段回答后 nextStep 为 null', () => {
    const last = SCRIPTED_FLOW[SCRIPTED_FLOW.length - 1]
    const value = { type: 'text' as const, value: '无' }
    const { nextStep } = replyToCurrentStep(last, value)
    expect(nextStep).toBeNull()
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
