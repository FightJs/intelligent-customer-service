import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { render } from '@testing-library/react'
import { ZStackProvider, useZStack } from '../src/hooks/useZStack'

const wrapper = ({ children }: { children: React.ReactNode }) => <ZStackProvider>{children}</ZStackProvider>

describe('useZStack', () => {
  it('默认 z=defaultZ', () => {
    const { result } = renderHook(() => useZStack({ id: 'a', defaultZ: 10 }), { wrapper })
    expect(result.current.z).toBe(10)
    expect(result.current.isTopmost).toBe(true)
  })

  it('bringToFront 把自己置顶', () => {
    const { result } = renderHook(() => useZStack({ id: 'a', defaultZ: 10 }), { wrapper })
    act(() => { result.current.bringToFront() })
    expect(result.current.z).toBeGreaterThan(10)
  })

  it('多卡片 bringToFront 交替置顶（同一 Provider 下）', () => {
    // 必须在同一个 ZStackProvider 下渲染两个卡片，bringToFront 才能让 z 超过所有现存 z（含 defaultZ）
    const refs: Record<string, { z: number; bringToFront: () => void; isTopmost: boolean }> = {}
    function Card({ id, defaultZ }: { id: string; defaultZ: number }) {
      refs[id] = useZStack({ id, defaultZ })
      return null
    }
    render(
      <ZStackProvider>
        <Card id="a" defaultZ={10} />
        <Card id="b" defaultZ={11} />
      </ZStackProvider>
    )
    // 初始：没人 bringToFront（topZ=0），所有卡片都算 topmost
    expect(refs.a.isTopmost).toBe(true)
    expect(refs.b.isTopmost).toBe(true)
    expect(refs.a.z).toBe(10)
    expect(refs.b.z).toBe(11)
    // b 置顶：b.z 必须 > a.z(10)
    act(() => { refs.b.bringToFront() })
    expect(refs.b.z).toBeGreaterThan(refs.a.z)
    expect(refs.b.isTopmost).toBe(true)
    expect(refs.a.isTopmost).toBe(false)
    // a 再置顶：a.z 必须 > b 当前 z
    act(() => { refs.a.bringToFront() })
    expect(refs.a.z).toBeGreaterThan(refs.b.z)
    expect(refs.a.isTopmost).toBe(true)
    expect(refs.b.isTopmost).toBe(false)
  })

  it('不在 Provider 内时回退 defaultZ（容错）', () => {
    const { result } = renderHook(() => useZStack({ id: 'a', defaultZ: 5 }))
    expect(result.current.z).toBe(5)
    expect(result.current.isTopmost).toBe(true)
  })
})
