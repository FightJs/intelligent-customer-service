import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useSpeechRecognition } from '../src/hooks/useSpeechRecognition'

type ErrorHandler = (
  event: { error: string },
) => void

type ResultHandler = (event: {
  results: {
    length: number
    [index: number]: {
      isFinal: boolean
      [index: number]: { transcript: string }
    }
  }
}) => void

class MockSpeechRecognition {
  static instances: MockSpeechRecognition[] = []

  lang = ''
  continuous = false
  interimResults = false
  maxAlternatives = 1
  onresult: ResultHandler | null = null
  onerror: ErrorHandler | null = null
  onend: (() => void) | null = null
  onstart: (() => void) | null = null
  start = vi.fn()
  stop = vi.fn()
  abort = vi.fn()

  constructor() {
    MockSpeechRecognition.instances.push(this)
  }
}

type SpeechTestWindow = Window & {
  webkitSpeechRecognition?: typeof MockSpeechRecognition
}

describe('useSpeechRecognition', () => {
  afterEach(() => {
    delete (
      window as SpeechTestWindow
    ).webkitSpeechRecognition
    MockSpeechRecognition.instances = []
    vi.useRealTimers()
  })

  it('网络错误时自动重试一次，持续失败后停止', () => {
    vi.useFakeTimers()

    const onError = vi.fn()
    const speechWindow = window as SpeechTestWindow
    speechWindow.webkitSpeechRecognition = MockSpeechRecognition

    const { result } = renderHook(() => (
      useSpeechRecognition({
        onTranscript: vi.fn(),
        onError,
      })
    ))

    act(() => {
      result.current.startListening()
    })

    expect(MockSpeechRecognition.instances).toHaveLength(1)
    expect(result.current.listening).toBe(false)

    act(() => {
      MockSpeechRecognition.instances[0].onstart?.()
    })

    expect(result.current.listening).toBe(true)

    act(() => {
      MockSpeechRecognition.instances[0].onerror?.({
        error: 'network',
      })
      vi.advanceTimersByTime(600)
    })

    expect(MockSpeechRecognition.instances).toHaveLength(2)
    expect(onError).not.toHaveBeenCalled()

    act(() => {
      MockSpeechRecognition.instances[1].onerror?.({ error: 'network' })
      vi.advanceTimersByTime(600)
      MockSpeechRecognition.instances[2].onerror?.({ error: 'network' })
    })

    expect(result.current.listening).toBe(false)
    expect(onError).toHaveBeenCalledWith(
      expect.stringContaining('仍无法连接'),
    )
  })

  it('用户停止后取消等待中的自动重试', () => {
    vi.useFakeTimers()

    const speechWindow = window as SpeechTestWindow
    speechWindow.webkitSpeechRecognition = MockSpeechRecognition

    const { result } = renderHook(() => (
      useSpeechRecognition({
        onTranscript: vi.fn(),
        onError: vi.fn(),
      })
    ))

    act(() => {
      result.current.startListening()
      MockSpeechRecognition.instances[0].onerror?.({
        error: 'network',
      })
      result.current.stopListening()
      vi.advanceTimersByTime(1000)
    })

    expect(MockSpeechRecognition.instances).toHaveLength(1)
    expect(result.current.listening).toBe(false)
  })

  it('识别器自动重启后保留前一段文字', () => {
    vi.useFakeTimers()
    const onTranscript = vi.fn()
    ;(window as SpeechTestWindow).webkitSpeechRecognition = MockSpeechRecognition

    const { result } = renderHook(() => useSpeechRecognition({
      onTranscript,
      onError: vi.fn(),
    }))

    act(() => {
      result.current.startListening()
      MockSpeechRecognition.instances[0].onstart?.()
      MockSpeechRecognition.instances[0].onresult?.({
        results: {
          0: { 0: { transcript: '第一段' }, isFinal: true },
          length: 1,
        },
      })
      MockSpeechRecognition.instances[0].onend?.()
      vi.advanceTimersByTime(300)
      MockSpeechRecognition.instances[1].onstart?.()
      MockSpeechRecognition.instances[1].onresult?.({
        results: {
          0: { 0: { transcript: '第二段' }, isFinal: true },
          length: 1,
        },
      })
    })

    expect(onTranscript).toHaveBeenLastCalledWith('第一段 第二段')
  })
})
