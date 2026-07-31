import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useResizable } from '../src/hooks/useResizable'

const OPTS = { storageKey: 'r1', defaultSize: { w: 280, h: 498 }, minSize: { w: 200, h: 356 }, maxSize: { w: 600, h: 1067 }, ratio: 9 / 16 }

function start(result: any, x = 300, y = 500) {
  act(() => { result.current.onResizeStart({ clientX: x, clientY: y, preventDefault: () => {} } as unknown as React.MouseEvent) })
}
function drag(x: number, y: number) {
  act(() => { document.dispatchEvent(new MouseEvent('mousemove', { clientX: x, clientY: y })) })
}
function up() {
  act(() => { document.dispatchEvent(new MouseEvent('mouseup')) })
}

describe('useResizable', () => {
  it('初始尺寸=默认值', () => {
    const { result } = renderHook(() => useResizable(OPTS))
    expect(result.current.size).toEqual({ w: 280, h: 498 })
    expect(result.current.resizing).toBe(false)
  })

  it('localStorage 有值时读取持久化尺寸', () => {
    localStorage.setItem('r1', JSON.stringify({ w: 300, h: 533 }))
    const { result } = renderHook(() => useResizable(OPTS))
    expect(result.current.size).toEqual({ w: 300, h: 533 })
  })

  it('onResizeStart 后 resizing=true', () => {
    const { result } = renderHook(() => useResizable(OPTS))
    start(result)
    expect(result.current.resizing).toBe(true)
    up()
  })

  it('拖右下角增大尺寸（width 基准）', () => {
    const { result } = renderHook(() => useResizable(OPTS))
    start(result, 300, 500)
    drag(400, 600)
    expect(result.current.size.w).toBe(380)
    expect(result.current.size.h).toBeCloseTo(380 / (9 / 16), 0)
    up()
  })

  it('minSize 下限 clamp', () => {
    const { result } = renderHook(() => useResizable(OPTS))
    start(result, 300, 500)
    drag(100, 100)
    expect(result.current.size.w).toBe(200)
    expect(result.current.size.h).toBeCloseTo(200 / (9 / 16), 0)
    up()
  })

  it('maxSize 上限 clamp', () => {
    const { result } = renderHook(() => useResizable(OPTS))
    start(result, 300, 500)
    drag(2000, 2000)
    expect(result.current.size.w).toBe(600)
    expect(result.current.size.h).toBeCloseTo(600 / (9 / 16), 0)
    up()
  })

  it('ratio=null 不锁比例', () => {
    const { result } = renderHook(() => useResizable({ ...OPTS, ratio: null }))
    start(result, 300, 500)
    drag(400, 500)
    expect(result.current.size.w).toBe(380)
    expect(result.current.size.h).toBe(498)
    up()
  })

  it('mouseup 写入 localStorage 并 resizing=false', () => {
    const { result } = renderHook(() => useResizable(OPTS))
    start(result, 300, 500)
    drag(400, 600)
    up()
    expect(result.current.resizing).toBe(false)
    const saved = JSON.parse(localStorage.getItem('r1')!)
    expect(saved.w).toBe(380)
  })
})
