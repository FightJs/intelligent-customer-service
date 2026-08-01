import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useDraggable } from '../src/hooks/useDraggable'

const BOUNDS = { width: 280, minHeight: 80, topMargin: 48, margin: 8 }

function startDrag(result: any, x = 100, y = 100) {
  act(() => {
    result.current.onDragStart({ clientX: x, clientY: y, preventDefault: () => {} } as unknown as React.MouseEvent)
  })
}
function move(x: number, y: number) {
  act(() => { document.dispatchEvent(new MouseEvent('mousemove', { clientX: x, clientY: y })) })
}
function up() {
  act(() => { document.dispatchEvent(new MouseEvent('mouseup')) })
}

describe('useDraggable', () => {
  it('初始位置=默认值', () => {
    const { result } = renderHook(() => useDraggable({ storageKey: 't1', defaultPos: { x: 16, y: 80 }, bounds: BOUNDS }))
    expect(result.current.pos).toEqual({ x: 16, y: 80 })
    expect(result.current.dragging).toBe(false)
  })

  it('localStorage 有值时读取持久化位置', () => {
    localStorage.setItem('t1', JSON.stringify({ x: 100, y: 200 }))
    const { result } = renderHook(() => useDraggable({ storageKey: 't1', defaultPos: { x: 16, y: 80 }, bounds: BOUNDS }))
    expect(result.current.pos).toEqual({ x: 100, y: 200 })
  })

  it('onDragStart 后 dragging=true', () => {
    const { result } = renderHook(() => useDraggable({ storageKey: 't1', defaultPos: { x: 16, y: 80 }, bounds: BOUNDS }))
    startDrag(result)
    expect(result.current.dragging).toBe(true)
    up()
  })

  it('拖拽中 mousemove 更新位置', () => {
    const { result } = renderHook(() => useDraggable({ storageKey: 't1', defaultPos: { x: 16, y: 80 }, bounds: BOUNDS }))
    startDrag(result, 100, 100)
    move(150, 130)
    expect(result.current.pos).toEqual({ x: 66, y: 110 })
    up()
  })

  it('mouseup 写入 localStorage 并 dragging=false', () => {
    const { result } = renderHook(() => useDraggable({ storageKey: 't1', defaultPos: { x: 16, y: 80 }, bounds: BOUNDS }))
    startDrag(result, 100, 100)
    move(200, 200)
    up()
    expect(result.current.dragging).toBe(false)
    expect(JSON.parse(localStorage.getItem('t1')!)).toEqual({ x: 116, y: 180 })
  })

  it('clamp 防止拖出可视区', () => {
    Object.defineProperty(window, 'innerWidth', { value: 1000, writable: true })
    Object.defineProperty(window, 'innerHeight', { value: 800, writable: true })
    const { result } = renderHook(() => useDraggable({ storageKey: 't1', defaultPos: { x: 16, y: 80 }, bounds: BOUNDS }))
    startDrag(result, 16, 80)
    move(-9999, -9999)
    expect(result.current.pos.x).toBe(8)
    expect(result.current.pos.y).toBe(48)
    up()
  })

  it('disabled=true 时 onDragStart 不响应', () => {
    const { result } = renderHook(() => useDraggable({ storageKey: 't1', defaultPos: { x: 16, y: 80 }, bounds: BOUNDS, disabled: true }))
    startDrag(result)
    expect(result.current.dragging).toBe(false)
    move(200, 200)
    expect(result.current.pos).toEqual({ x: 16, y: 80 })
  })

  it('localStorage 值非法时回退默认', () => {
    localStorage.setItem('t1', 'not-json')
    const { result } = renderHook(() => useDraggable({ storageKey: 't1', defaultPos: { x: 16, y: 80 }, bounds: BOUNDS }))
    expect(result.current.pos).toEqual({ x: 16, y: 80 })
  })

  it('clamp=false 时拖拽不受 bounds 限制（可拖到负值）', () => {
    const { result } = renderHook(() => useDraggable({ storageKey: 't1', defaultPos: { x: 0, y: 0 }, bounds: BOUNDS, clamp: false }))
    startDrag(result, 0, 0)
    move(-500, -500)
    expect(result.current.pos).toEqual({ x: -500, y: -500 })
    up()
  })

  it('clamp=false 时窗口 resize 不强制 clamp 已有位置', () => {
    const { result } = renderHook(() => useDraggable({ storageKey: 't1', defaultPos: { x: -100, y: -200 }, bounds: BOUNDS, clamp: false }))
    expect(result.current.pos).toEqual({ x: -100, y: -200 })
    act(() => { window.dispatchEvent(new Event('resize')) })
    expect(result.current.pos).toEqual({ x: -100, y: -200 })
  })
})
