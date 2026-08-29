import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useCoarsePointer } from '../src/hooks/useCoarsePointer'

type ChangeListener = () => void

interface MockMediaQueryList {
  matches: boolean
  addEventListener: (type: string, listener: ChangeListener) => void
  removeEventListener: (type: string, listener: ChangeListener) => void
}

function mockMatchMedia(initialMatches: boolean) {
  const listeners = new Set<ChangeListener>()
  const media: MockMediaQueryList = {
    matches: initialMatches,
    addEventListener: (_type, listener) => { listeners.add(listener) },
    removeEventListener: (_type, listener) => { listeners.delete(listener) },
  }
  window.matchMedia = vi.fn(
    () => media,
  ) as unknown as typeof window.matchMedia

  return {
    setMatches(next: boolean) {
      media.matches = next
      for (const listener of [...listeners]) {
        listener()
      }
    },
  }
}

describe('useCoarsePointer', () => {
  afterEach(() => {
    delete (window as Partial<Window>).matchMedia
  })

  it('无 matchMedia 的环境（jsdom 默认）返回 false', () => {
    delete (window as Partial<Window>).matchMedia

    const { result } = renderHook(() => useCoarsePointer())

    expect(result.current).toBe(false)
  })

  it('触屏设备返回 true，指针类型变化时同步更新', () => {
    const media = mockMatchMedia(true)

    const { result } = renderHook(() => useCoarsePointer())
    expect(result.current).toBe(true)

    act(() => media.setMatches(false))
    expect(result.current).toBe(false)
  })

  it('卸载后移除 change 监听', () => {
    mockMatchMedia(false)
    const removeSpy = vi.spyOn(
      window.matchMedia('(pointer: coarse)'),
      'removeEventListener',
    )

    const { unmount } = renderHook(() => useCoarsePointer())
    unmount()

    expect(removeSpy).toHaveBeenCalled()
  })
})
