import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useCardDrag } from '../src/components/ProgressCard/useCardDrag'

describe('useCardDrag', () => {
  it('初始位置默认 {x:16, y:80}', () => {
    const { result } = renderHook(() => useCardDrag())
    expect(result.current.pos).toEqual({ x: 16, y: 80 })
    expect(result.current.dragging).toBe(false)
  })

  it('localStorage 有值时读取持久化位置', () => {
    localStorage.setItem('progresscard.pos', JSON.stringify({ x: 100, y: 200 }))
    const { result } = renderHook(() => useCardDrag())
    expect(result.current.pos).toEqual({ x: 100, y: 200 })
    localStorage.clear()
  })

  it('startDrag 后 dragging=true', () => {
    const { result } = renderHook(() => useCardDrag())
    act(() => {
      result.current.onHeaderMouseDown({ clientX: 50, clientY: 50, preventDefault: () => {} } as unknown as React.MouseEvent)
    })
    expect(result.current.dragging).toBe(true)
  })

  it('拖拽中 mousemove 更新位置', () => {
    const { result } = renderHook(() => useCardDrag())
    act(() => {
      result.current.onHeaderMouseDown({ clientX: 100, clientY: 100, preventDefault: () => {} } as unknown as React.MouseEvent)
    })
    act(() => {
      document.dispatchEvent(new MouseEvent('mousemove', { clientX: 150, clientY: 130 }))
    })
    expect(result.current.pos).toEqual({ x: 66, y: 110 })
    act(() => {
      document.dispatchEvent(new MouseEvent('mouseup'))
    })
  })

  it('拖拽结束 mouseup 写入 localStorage 并 dragging=false', () => {
    const { result } = renderHook(() => useCardDrag())
    act(() => {
      result.current.onHeaderMouseDown({ clientX: 100, clientY: 100, preventDefault: () => {} } as unknown as React.MouseEvent)
    })
    act(() => {
      document.dispatchEvent(new MouseEvent('mousemove', { clientX: 200, clientY: 200 }))
    })
    act(() => {
      document.dispatchEvent(new MouseEvent('mouseup'))
    })
    expect(result.current.dragging).toBe(false)
    const saved = JSON.parse(localStorage.getItem('progresscard.pos') || 'null')
    expect(saved).toEqual({ x: 116, y: 180 })
    localStorage.clear()
  })

  it('clamp 防止拖出可视区', () => {
    Object.defineProperty(window, 'innerWidth', { value: 1000, writable: true })
    Object.defineProperty(window, 'innerHeight', { value: 800, writable: true })
    const { result } = renderHook(() => useCardDrag())
    act(() => {
      result.current.onHeaderMouseDown({ clientX: 16, clientY: 80, preventDefault: () => {} } as unknown as React.MouseEvent)
    })
    act(() => {
      document.dispatchEvent(new MouseEvent('mousemove', { clientX: -9999, clientY: -9999 }))
    })
    expect(result.current.pos.x).toBe(8)
    expect(result.current.pos.y).toBe(48)
    act(() => {
      document.dispatchEvent(new MouseEvent('mouseup'))
    })
    localStorage.clear()
  })
})
