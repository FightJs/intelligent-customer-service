/// <reference types="@testing-library/jest-dom/vitest" />
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ChatPanel, {
  suggestionMatchesReply,
  toolEventStatus,
} from '../src/components/ChatPanel/ChatPanel'
import {
  suggestionOptionUpdate,
  suggestionOptionsUpdate,
} from '../src/components/ChatPanel/suggestionUpdate'
import { FormProvider } from '../src/state/FormContext'
import { createInitialState } from '../src/state/initialState'
import { createSession, getSession, skipCurrentQuestion } from '../src/api/client'
import { streamChat } from '../src/api/chatStream'

vi.mock('../src/api/client', () => ({
  getSession: vi.fn(async () => { throw new Error('restore skipped in tests') }),
  createSession: vi.fn(),
  chat: vi.fn(),
  skipCurrentQuestion: vi.fn(),
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

function sessionData(state = createInitialState()) {
  return { session_id: 'session-1', form_state: state, greeting: '你好' }
}

function renderPanel(props: React.ComponentProps<typeof ChatPanel> = {}) {
  return render(
    <FormProvider>
      <ChatPanel {...props} />
    </FormProvider>,
  )
}

async function waitForReadyInput() {
  const input = screen.getByPlaceholderText('输入您的回答…')
  // 输入框在会话加载期间就已存在；可编辑才代表异步初始化完成。
  await waitFor(() => expect(input).toBeEnabled())
  return input
}

beforeEach(() => {
  sessionStorage.clear()
  vi.clearAllMocks()
  vi.mocked(createSession).mockResolvedValue(sessionData())
})

describe('ChatPanel 输入与流式回复', () => {
  it('保留填写说明和填写示例之间的单换行', async () => {
    vi.mocked(createSession).mockResolvedValue({
      ...sessionData(),
      greeting: (
        '更具体的细分品类是什么？\n\n'
        + '填写说明：可按实际情况补充（可跳过）\n'
        + '填写示例：高端香云纱女装、黄金珠宝'
      ),
    })

    renderPanel()

    const helpParagraph = await screen.findByText((_, element) => (
      element?.tagName === 'P'
      && element.textContent?.includes('填写说明：可按实际情况补充（可跳过）') === true
      && element.textContent?.includes('填写示例：高端香云纱女装、黄金珠宝') === true
    ))
    expect(helpParagraph).toHaveClass('whitespace-pre-line')
  })

  it('按用户隔离恢复会话，不读取旧的全局会话键', async () => {
    sessionStorage.setItem('ics_session_id', 'guest-session')
    sessionStorage.setItem('ics_session_id:42', 'user-session')

    renderPanel({ userId: 42 })
    await waitForReadyInput()

    expect(getSession).toHaveBeenCalledWith('user-session')
    expect(getSession).not.toHaveBeenCalledWith('guest-session')
  })

  it('使用多行输入框并允许清空草稿', async () => {
    renderPanel()
    const input = await waitForReadyInput()
    expect(input.tagName).toBe('TEXTAREA')
    fireEvent.change(input, { target: { value: '第一行\n第二行' } })
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true })
    fireEvent.click(screen.getByRole('button', { name: '清空输入' }))
    expect(input).toHaveValue('')
  })

  it('将流式 delta 汇聚到一个 AI 气泡，并由 done 覆盖最终文本', async () => {
    vi.mocked(streamChat).mockImplementation(async (_request, handlers) => {
      handlers.onStart({ request_id: 'request-1', status: 'started' })
      handlers.onStatus({ phase: 'generating', message: '正在生成回复' })
      handlers.onDelta({ text: '临时' })
      handlers.onDone({
        request_id: 'request-1', reply: '最终回复', tool_events: [],
        form_state: createInitialState(), form_complete: false,
        suggestions: [], assistant_message_id: 1,
      })
    })

    renderPanel()
    const input = await waitForReadyInput()
    fireEvent.change(input, { target: { value: '品牌名是云裳' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))
    await screen.findByText('最终回复')
    expect(screen.queryByText('临时')).not.toBeInTheDocument()
    expect(screen.getAllByText('最终回复')).toHaveLength(1)
  })

  it('简约版完成后引导查看右上角需求表和登录正式账号', async () => {
    vi.mocked(streamChat).mockImplementation(async (_request, handlers) => {
      handlers.onStart({ request_id: 'quick-done', status: 'started' })
      handlers.onDone({
        request_id: 'quick-done', reply: '本次采集完成', tool_events: [],
        form_state: createInitialState(), form_complete: true,
        suggestions: [], assistant_message_id: 1,
      })
    })

    renderPanel({ userRole: 'guest' })
    const input = await waitForReadyInput()
    fireEvent.change(input, { target: { value: '最后一项' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))

    expect(await screen.findByText(/简约体验已完成/)).toHaveTextContent(
      '右上角客户需求表',
    )
    expect(screen.getByText(/简约体验已完成/)).toHaveTextContent(
      '登录或注册正式账号',
    )
    expect(screen.queryByText(/确认后发送订单/)).not.toBeInTheDocument()
  })

  it('生成期间禁用输入并显示当前处理阶段', async () => {
    let finishStream!: () => void
    const pending = new Promise<void>((resolve) => { finishStream = resolve })
    vi.mocked(streamChat).mockImplementation(async (_request, handlers) => {
      handlers.onStart({ request_id: 'request-pending', status: 'started' })
      handlers.onStatus({ phase: 'generating', message: '正在生成回复' })
      await pending
      handlers.onDone({
        request_id: 'request-pending', reply: '回复完成', tool_events: [],
        form_state: createInitialState(), form_complete: false,
        suggestions: [], assistant_message_id: 1,
      })
    })

    renderPanel()
    const input = await waitForReadyInput()
    fireEvent.change(input, { target: { value: '第一条消息' } })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))
    const waitingInput = await screen.findByPlaceholderText('正在生成回复，请稍候…')
    expect(waitingInput).toBeDisabled()
    expect(screen.getByRole('button', { name: '停止生成' })).toBeEnabled()
    await act(async () => { finishStream(); await pending })
    await screen.findByText('回复完成')
    expect(waitingInput).toBeEnabled()
  })

  it('会话请求未完成时禁用图片入口，完成后才能打开菜单', async () => {
    let resolveSession!: (data: ReturnType<typeof sessionData>) => void
    const pendingSession = new Promise<ReturnType<typeof sessionData>>((resolve) => {
      resolveSession = resolve
    })
    vi.mocked(createSession).mockReturnValueOnce(pendingSession)

    renderPanel()
    const addImage = screen.getByRole('button', { name: '添加图片' })
    expect(screen.getByPlaceholderText('输入您的回答…')).toBeDisabled()
    expect(addImage).toBeDisabled()
    fireEvent.click(addImage)
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()

    await act(async () => {
      resolveSession(sessionData())
      await pendingSession
    })
    await waitForReadyInput()
    expect(addImage).toBeEnabled()
    fireEvent.click(addImage)
    expect(screen.getByRole('menuitem', { name: '拍照' })).toBeInTheDocument()
  })

  it('用单一图片入口选择相册或拍照，多图只追加一次', async () => {
    const { container } = renderPanel()
    await waitForReadyInput()
    const addImage = screen.getByRole('button', { name: '添加图片' })
    expect(addImage).toBeEnabled()
    expect(screen.queryByRole('menuitem', { name: '拍照' })).not.toBeInTheDocument()
    fireEvent.click(addImage)
    expect(screen.getByRole('menuitem', { name: '从相册选择' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: '拍照' })).toBeInTheDocument()
    const cameraInput = container.querySelector('input[type="file"][capture="environment"]')
    expect(cameraInput).toHaveAttribute(
      'accept',
      'image/png,image/jpeg,image/webp,image/gif',
    )
    const galleryInput = container.querySelector('input[type="file"][multiple]')!
    fireEvent.change(galleryInput, {
      target: {
        files: [
          new File(['one'], 'one.png', { type: 'image/png' }),
          new File(['two'], 'two.png', { type: 'image/png' }),
        ],
      },
    })
    await waitFor(() => {
      expect(container.querySelectorAll('img[src^="data:image/png"]')).toHaveLength(2)
    })
    expect(screen.queryByRole('menu', { name: '图片添加方式' })).not.toBeInTheDocument()
  })
})

describe('ChatPanel 跳过与提前结束', () => {
  it('仅在当前规则允许时显示跳过按钮并调用确定性接口', async () => {
    const state = createInitialState()
    state.currentSectionId = 'industry'
    state.currentFieldId = 'category'
    vi.mocked(createSession).mockResolvedValueOnce(sessionData(state))
    const nextState = createInitialState()
    nextState.currentSectionId = 'industry'
    nextState.currentFieldId = 'subcategory'
    vi.mocked(skipCurrentQuestion).mockResolvedValueOnce({
      reply: '已跳过“行业大类”。更具体的细分品类是什么？',
      form_state: nextState,
      form_complete: false,
    })

    renderPanel({ canFinishEarly: true, onFinishEarly: vi.fn() })
    fireEvent.click(await screen.findByRole('button', { name: '跳过此题' }))
    await waitFor(() => {
      expect(skipCurrentQuestion).toHaveBeenCalledWith('session-1', 'field')
    })
    expect(await screen.findByText(/已跳过“行业大类”/)).toBeInTheDocument()
  })

  it('核心题不显示跳过按钮，但正式用户可提前结束', async () => {
    const onFinishEarly = vi.fn()
    renderPanel({ canFinishEarly: true, onFinishEarly })
    await waitForReadyInput()
    expect(screen.queryByRole('button', { name: /跳过/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '提前结束并提交' }))
    expect(onFinishEarly).toHaveBeenCalledTimes(1)
  })

  it('可跳过题位于可跳过模块时同时提供题目和模块入口', async () => {
    const state = createInitialState()
    state.currentSectionId = 'status'
    state.currentFieldId = 'duration'
    vi.mocked(createSession).mockResolvedValueOnce(sessionData(state))

    renderPanel()

    expect(await screen.findByRole('button', { name: '跳过此题' })).toBeEnabled()
    expect(screen.getByRole('button', { name: '跳过本模块' })).toBeEnabled()
  })

  it('跳过失败不追加假的用户消息', async () => {
    const state = createInitialState()
    state.currentSectionId = 'industry'
    state.currentFieldId = 'category'
    vi.mocked(createSession).mockResolvedValueOnce(sessionData(state))
    vi.mocked(skipCurrentQuestion).mockRejectedValueOnce(new Error('服务端拒绝跳过'))

    renderPanel()
    fireEvent.click(await screen.findByRole('button', { name: '跳过此题' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('服务端拒绝跳过')
    expect(screen.queryByText('跳过当前问题')).not.toBeInTheDocument()
  })

  it('存在未发送草稿时阻止跳过和提前提交', async () => {
    const state = createInitialState()
    state.currentSectionId = 'industry'
    state.currentFieldId = 'category'
    vi.mocked(createSession).mockResolvedValueOnce(sessionData(state))
    const onFinishEarly = vi.fn()

    renderPanel({ canFinishEarly: true, onFinishEarly })
    fireEvent.change(await waitForReadyInput(), {
      target: { value: '还没发送的回答' },
    })
    fireEvent.click(screen.getByRole('button', { name: '跳过此题' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('未发送的回答或图片')
    expect(skipCurrentQuestion).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: '提前结束并提交' }))
    expect(onFinishEarly).not.toHaveBeenCalled()
  })
})

describe('ChatPanel 语音输入', () => {
  it('开始、写入识别文字并停止语音', async () => {
    type ResultEvent = {
      results: {
        length: number
        [index: number]: {
          length: number
          isFinal: boolean
          [index: number]: { transcript: string }
        }
      }
    }
    const recognitions: MockSpeechRecognition[] = []
    class MockSpeechRecognition {
      lang = ''
      continuous = false
      interimResults = false
      maxAlternatives = 1
      onresult: ((event: ResultEvent) => void) | null = null
      onerror: ((event: { error: string }) => void) | null = null
      onend: (() => void) | null = null
      onstart: (() => void) | null = null
      start = vi.fn()
      stop = vi.fn()
      abort = vi.fn()
      constructor() { recognitions.push(this) }
    }
    const speechWindow = window as typeof window & {
      webkitSpeechRecognition?: new () => MockSpeechRecognition
    }
    speechWindow.webkitSpeechRecognition = MockSpeechRecognition

    renderPanel()
    const input = await waitForReadyInput()
    fireEvent.click(screen.getByRole('button', { name: '开始语音输入' }))
    const recognition = recognitions[0]
    expect(recognition.start).toHaveBeenCalledTimes(1)
    act(() => recognition.onstart?.())
    expect(screen.getByTestId('voice-listening-indicator')).toBeInTheDocument()
    act(() => {
      recognition.onresult?.({
        results: {
          0: {
            0: { transcript: '我需要搭建女装直播间' },
            length: 1,
            isFinal: true,
          },
          length: 1,
        },
      })
    })
    expect(input).toHaveValue('我需要搭建女装直播间')
    fireEvent.click(screen.getByRole('button', { name: '停止语音输入' }))
    expect(recognition.stop).toHaveBeenCalledTimes(1)
    delete speechWindow.webkitSpeechRecognition
  })

  it('浏览器不支持时按钮仍可点击并给出明确提示', async () => {
    const speechWindow = window as typeof window & {
      SpeechRecognition?: unknown
      webkitSpeechRecognition?: unknown
    }
    delete speechWindow.SpeechRecognition
    delete speechWindow.webkitSpeechRecognition
    renderPanel()
    const button = await screen.findByRole('button', { name: '开始语音输入' })
    await waitFor(() => expect(button).toBeEnabled())
    fireEvent.click(button)
    expect(await screen.findByRole('alert')).toHaveTextContent('当前浏览器不支持语音输入')
  })
})

describe('suggestionMatchesReply', () => {
  const suggestion = {
    section_id: 'customer',
    field_id: 'brand',
    options: [{ label: '选项甲', value: 'a' }, { label: '选项乙', value: 'b' }],
  }

  it('回复命中字段实义关键词时匹配', () => {
    expect(suggestionMatchesReply(suggestion as never, '我的品牌/公司名称是云裳')).toBe(true)
  })
  it('回复为空或不相关时不匹配', () => {
    expect(suggestionMatchesReply(suggestion as never, undefined)).toBe(false)
    expect(suggestionMatchesReply(suggestion as never, '今天天气不错')).toBe(false)
  })
  it('回复同时命中两个选项时匹配', () => {
    expect(suggestionMatchesReply(suggestion as never, '我想要选项甲和选项乙')).toBe(true)
    expect(suggestionMatchesReply(suggestion as never, '只要选项甲')).toBe(false)
  })
})

describe('suggestionOptionUpdate', () => {
  it('多选快捷项提交数组，单选快捷项保持字符串', () => {
    const option = { label: '商品质感', value: 'product-quality' }
    expect(suggestionOptionUpdate({
      section_id: 'goal', field_id: 'focus', options: [option],
    }, option).value).toEqual(['product-quality'])

    expect(suggestionOptionUpdate({
      section_id: 'status', field_id: 'has_room', options: [{ label: '有', value: 'yes' }],
    }, { label: '有', value: 'yes' }).value).toBe('yes')
  })

  it('多选快捷项可以一次提交多个选项', () => {
    const options = [
      { label: '主理人（老板）', value: 'owner' },
      { label: '主播', value: 'host' },
    ]
    expect(suggestionOptionsUpdate({
      section_id: 'customer', field_id: 'identity', options,
    }, options).value).toEqual(['owner', 'host'])
  })
})

describe('toolEventStatus', () => {
  it('仅为工具事件显示安全的阶段提示', () => {
    expect(toolEventStatus('fill')).toBe('正在更新表单')
    expect(toolEventStatus('skip')).toBe('正在整理需求')
    expect(toolEventStatus('deliverable')).toBe('正在生成交付物')
  })
})

describe('ChatPanel 按住说话（触屏）', () => {
  function mockCoarsePointer() {
    window.matchMedia = vi.fn((query: string) => ({
      matches: query === '(pointer: coarse)',
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })) as unknown as typeof window.matchMedia
  }

  afterEach(() => {
    delete (window as Partial<Window>).matchMedia
  })

  it('按住开始识别、松开停止，残留 click 不重复触发', async () => {
    mockCoarsePointer()

    const recognitions: MockSpeechRecognition[] = []
    class MockSpeechRecognition {
      lang = ''
      continuous = false
      interimResults = false
      maxAlternatives = 1
      onresult: ((event: unknown) => void) | null = null
      onerror: ((event: { error: string }) => void) | null = null
      onend: (() => void) | null = null
      onstart: (() => void) | null = null
      start = vi.fn()
      stop = vi.fn()
      abort = vi.fn()
      constructor() { recognitions.push(this) }
    }
    const speechWindow = window as typeof window & {
      webkitSpeechRecognition?: new () => MockSpeechRecognition
    }
    speechWindow.webkitSpeechRecognition = MockSpeechRecognition

    renderPanel()
    await waitForReadyInput()

    const button = screen.getByRole('button', { name: '按住说话' })

    fireEvent.pointerDown(button)
    expect(recognitions).toHaveLength(1)
    expect(recognitions[0].start).toHaveBeenCalledTimes(1)

    act(() => recognitions[0].onstart?.())
    expect(screen.getByTestId('voice-listening-indicator')).toBeInTheDocument()

    fireEvent.pointerUp(button)
    expect(recognitions[0].stop).toHaveBeenCalledTimes(1)

    // 触屏按住后浏览器会补发 click，绝不能当成 toggle 重新开始
    fireEvent.click(button, { detail: 1 })
    expect(recognitions).toHaveLength(1)

    delete speechWindow.webkitSpeechRecognition
  })

  it('pointercancel 同样停止识别', async () => {
    mockCoarsePointer()

    const recognitions: MockSpeechRecognition[] = []
    class MockSpeechRecognition {
      lang = ''
      continuous = false
      interimResults = false
      maxAlternatives = 1
      onresult: ((event: unknown) => void) | null = null
      onerror: ((event: { error: string }) => void) | null = null
      onend: (() => void) | null = null
      onstart: (() => void) | null = null
      start = vi.fn()
      stop = vi.fn()
      abort = vi.fn()
      constructor() { recognitions.push(this) }
    }
    const speechWindow = window as typeof window & {
      webkitSpeechRecognition?: new () => MockSpeechRecognition
    }
    speechWindow.webkitSpeechRecognition = MockSpeechRecognition

    renderPanel()
    await waitForReadyInput()

    const button = screen.getByRole('button', { name: '按住说话' })
    fireEvent.pointerDown(button)
    act(() => recognitions[0].onstart?.())
    fireEvent.pointerCancel(button)
    expect(recognitions[0].stop).toHaveBeenCalledTimes(1)

    delete speechWindow.webkitSpeechRecognition
  })

  it('只响应发起按住的手指，并在丢失捕获时停止', async () => {
    mockCoarsePointer()

    const recognitions: MockSpeechRecognition[] = []
    class MockSpeechRecognition {
      lang = ''
      continuous = false
      interimResults = false
      maxAlternatives = 1
      onresult: ((event: unknown) => void) | null = null
      onerror: ((event: { error: string }) => void) | null = null
      onend: (() => void) | null = null
      onstart: (() => void) | null = null
      start = vi.fn()
      stop = vi.fn()
      abort = vi.fn()
      constructor() { recognitions.push(this) }
    }
    const speechWindow = window as typeof window & {
      webkitSpeechRecognition?: new () => MockSpeechRecognition
    }
    speechWindow.webkitSpeechRecognition = MockSpeechRecognition

    renderPanel()
    await waitForReadyInput()
    const button = screen.getByRole('button', { name: '按住说话' })

    fireEvent.pointerDown(button, { pointerId: 1 })
    fireEvent.pointerDown(button, { pointerId: 2 })
    expect(recognitions).toHaveLength(1)

    act(() => recognitions[0].onstart?.())
    fireEvent.pointerUp(button, { pointerId: 2 })
    expect(recognitions[0].stop).not.toHaveBeenCalled()

    fireEvent.lostPointerCapture(button, { pointerId: 1 })
    expect(recognitions[0].stop).toHaveBeenCalledTimes(1)

    delete speechWindow.webkitSpeechRecognition
  })
})
