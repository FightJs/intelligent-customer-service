/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ChatPanel, { suggestionMatchesReply } from '../src/components/ChatPanel/ChatPanel'
import { FormProvider } from '../src/state/FormContext'
import { SECTIONS } from '../src/data/sections'

vi.mock('../src/api/client', () => ({
  createSession: () => Promise.resolve({
    session_id: 'session-1',
    form_state: {},
    greeting: '你好',
  }),
  chat: vi.fn(),
}))

Object.defineProperty(HTMLElement.prototype, 'scrollTo', {
  value: vi.fn(),
  writable: true,
})

describe('ChatPanel 输入框', () => {
  it('使用多行输入框并允许清空草稿', async () => {
    render(
      <FormProvider>
        <ChatPanel />
      </FormProvider>,
    )

    const input = await screen.findByPlaceholderText('输入您的回答…')
    expect(input.tagName).toBe('TEXTAREA')

    fireEvent.change(input, { target: { value: '第一行\n第二行' } })
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true })
    expect(screen.getByRole('button', { name: '清空输入' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '清空输入' }))
    expect(input).toHaveValue('')
  })
})

describe('suggestionMatchesReply', () => {
  // 取真实字段构造 suggestion：customer.brand（label "品牌名称"）
  const suggestion = {
    section_id: 'customer',
    field_id: 'brand',
    prompt: '品牌?',
    options: [{ label: '选项甲', value: 'a' }, { label: '选项乙', value: 'b' }],
  }

  it('回复命中字段实义关键词时匹配', () => {
    // label「客户名称/品牌名」整个作为关键词保留（GENERIC 只排除「客户」单字）
    expect(suggestionMatchesReply(suggestion as any, '我的客户名称/品牌名是云裳')).toBe(true)
  })

  it('回复为空或不相关时不匹配', () => {
    expect(suggestionMatchesReply(suggestion as any, undefined)).toBe(false)
    expect(suggestionMatchesReply(suggestion as any, '今天天气不错')).toBe(false)
  })

  it('回复同时命中 ≥2 个选项 label 时匹配', () => {
    const s = { ...suggestion, options: [{ label: '选项甲', value: 'a' }, { label: '选项乙', value: 'b' }] }
    expect(suggestionMatchesReply(s as any, '我想要选项甲和选项乙')).toBe(true)
    expect(suggestionMatchesReply(s as any, '只要选项甲')).toBe(false)
  })
})
