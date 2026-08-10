/// <reference types="@testing-library/jest-dom/vitest" />
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ChatPanel, { suggestionMatchesReply, toolEventStatus } from '../src/components/ChatPanel/ChatPanel'
import { FormProvider } from '../src/state/FormContext'
import { SECTIONS } from '../src/data/sections'
import { streamChat } from '../src/api/chatStream'

vi.mock('../src/api/client', () => ({
  createSession: () => Promise.resolve({
    session_id: 'session-1',
    form_state: {},
    greeting: '你好',
  }),
  chat: vi.fn(),
}))

vi.mock('../src/api/chatStream', () => ({
  ChatStreamHttpError: class ChatStreamHttpError extends Error { },
  ChatStreamInterruptedError: class ChatStreamInterruptedError extends Error { },
  streamChat: vi.fn(),
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

  it('将流式 delta 汇聚到一个 AI 气泡，并由 done 覆盖最终文本', async () => {
    vi.mocked(streamChat).mockImplementation(async (_request, handlers) => {
      handlers.onStart({ request_id: 'request-1', status: 'started' })
      handlers.onStatus({ phase: 'generating', message: '正在生成回复' })
      handlers.onDelta({ text: '临时' })
      handlers.onDone({
        request_id: 'request-1',
        reply: '最终回复',
        tool_events: [],
        form_state: { sections: {}, currentSectionId: 'customer', completed: false } as any,
        form_complete: false,
        suggestions: [],
        assistant_message_id: 1,
      })
      it('开始和停止语音并写入识别文字', async () => {
        type MockSpeechResultEvent = {
          results: {
            length: number
            [index: number]: {
              length: number
              isFinal: boolean
              [index: number]: {
                transcript: string
              }
            }
          }
        }

        let recognition!: MockSpeechRecognition

        class MockSpeechRecognition {
          lang = ''
          continuous = false
          interimResults = false
          maxAlternatives = 1

          onresult:
            | ((
              event: MockSpeechResultEvent,
            ) => void)
            | null = null

          onerror:
            | ((
              event: { error: string },
            ) => void)
            | null = null

          onend: (() => void) | null = null

          start = vi.fn()

          stop = vi.fn(() => {
            this.onend?.()
          })

          abort = vi.fn()

          constructor() {
            recognition = this
          }
        }

        const speechWindow =
          window as typeof window & {
            webkitSpeechRecognition?:
            new () => MockSpeechRecognition
          }

        speechWindow.webkitSpeechRecognition =
          MockSpeechRecognition

        render(
          <FormProvider>
            <ChatPanel />
          </FormProvider>,
        )

        const input =
          await screen.findByPlaceholderText(
            '输入您的回答…',
          )

        fireEvent.click(
          screen.getByRole('button', {
            name: '开始语音输入',
          }),
        )

        expect(
          recognition.start,
        ).toHaveBeenCalledTimes(1)

        expect(
          screen.getByText(
            '正在聆听，再次点击麦克风结束',
          ),
        ).toBeInTheDocument()

        act(() => {
          recognition.onresult?.({
            results: {
              0: {
                0: {
                  transcript:
                    '我需要搭建女装直播间',
                },
                length: 1,
                isFinal: true,
              },
              length: 1,
            },
          })
        })

        expect(input).toHaveValue(
          '我需要搭建女装直播间',
        )

        fireEvent.click(
          screen.getByRole('button', {
            name: '停止语音输入',
          }),
        )

        expect(
          recognition.stop,
        ).toHaveBeenCalledTimes(1)

        expect(
          screen.getByRole('button', {
            name: '开始语音输入',
          }),
        ).toBeInTheDocument()

        delete (
          speechWindow.webkitSpeechRecognition
        )
      })
    })

    render(
      <FormProvider>
        <ChatPanel />
      </FormProvider>,
    )

    const input = await screen.findByPlaceholderText('输入您的回答…')
    fireEvent.change(input, { target: { value: '品牌名是云裳' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    await waitFor(() => expect(screen.getByText('最终回复')).toBeInTheDocument())
    expect(screen.queryByText('临时')).not.toBeInTheDocument()
    expect(screen.getAllByText('最终回复')).toHaveLength(1)
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

describe('toolEventStatus', () => {
  it('仅为工具事件显示安全的阶段提示', () => {
    expect(toolEventStatus('fill')).toBe('正在更新表单')
    expect(toolEventStatus('skip')).toBe('正在整理需求')
    expect(toolEventStatus('deliverable')).toBe('正在生成交付物')
  })
})
