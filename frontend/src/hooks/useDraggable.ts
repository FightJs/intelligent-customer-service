import { useState, useRef, useEffect, useCallback } from 'react'

interface Pos { x: number; y: number }
interface Bounds { width: number; minHeight: number; topMargin: number; margin: number }
type PositionClamp = (next: Pos, current: Pos) => Pos

function clamp(v: number, min: number, max: number) {
  return Math.min(Math.max(v, min), max)
}

function loadInitial(storageKey: string, fallback: Pos): Pos {
  const raw = localStorage.getItem(storageKey)
  if (!raw) return fallback
  try {
    const p = JSON.parse(raw)
    if (typeof p.x === 'number' && typeof p.y === 'number') return p
  } catch {
    /* 非法值回退默认 */
  }
  return fallback
}

export function useDraggable(opts: {
  storageKey: string
  defaultPos: Pos
  bounds: Bounds
  disabled?: boolean
  clamp?: boolean
  clampPosition?: PositionClamp
}): { pos: Pos; dragging: boolean; onDragStart: (e: React.MouseEvent) => void } {
  const { storageKey, defaultPos, bounds, disabled = false, clamp: shouldClamp = true, clampPosition } = opts
  const [pos, setPos] = useState<Pos>(() => loadInitial(storageKey, defaultPos))
  const [dragging, setDragging] = useState(false)
  const startRef = useRef<{ mouseX: number; mouseY: number; posX: number; posY: number } | null>(null)

  const clampPos = useCallback((p: Pos): Pos => {
    const maxX = window.innerWidth - bounds.width - bounds.margin
    const maxY = window.innerHeight - bounds.minHeight - bounds.margin
    return {
      x: clamp(p.x, bounds.margin, Math.max(bounds.margin, maxX)),
      y: clamp(p.y, bounds.topMargin, Math.max(bounds.topMargin, maxY)),
    }
  }, [bounds])

  const applyPos = useCallback(
    (next: Pos, current: Pos): Pos => {
      if (!shouldClamp) return next
      return clampPosition ? clampPosition(next, current) : clampPos(next)
    },
    [shouldClamp, clampPosition, clampPos],
  )

  const onMove = useCallback((e: MouseEvent) => {
    const start = startRef.current
    if (!start) return
    const dx = e.clientX - start.mouseX
    const dy = e.clientY - start.mouseY
    const next = { x: start.posX + dx, y: start.posY + dy }
    setPos((current) => applyPos(next, current))
  }, [applyPos])

  const onUp = useCallback(() => {
    if (!startRef.current) return
    startRef.current = null
    setDragging(false)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }, [onMove])

  const onDragStart = useCallback((e: React.MouseEvent) => {
    if (disabled) return
    e.preventDefault()
    startRef.current = { mouseX: e.clientX, mouseY: e.clientY, posX: pos.x, posY: pos.y }
    setDragging(true)
    document.body.style.cursor = 'move'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [disabled, pos, onMove, onUp])

  // 持久化:dragging 从 true → false 时写 localStorage
  useEffect(() => {
    if (!dragging) localStorage.setItem(storageKey, JSON.stringify(pos))
  }, [dragging, pos, storageKey])

  // 窗口缩放重新 clamp（clamp=false 时不动）
  useEffect(() => {
    if (!shouldClamp) return
    function onResize() { setPos((current) => applyPos(current, current)) }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [shouldClamp, applyPos])

  // 旧的持久化坐标也必须立即遵循当前工作区域的限制。
  useEffect(() => {
    if (!shouldClamp) return
    setPos((current) => applyPos(current, current))
  }, [shouldClamp, applyPos])

  // 卸载时清理
  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
  }, [onMove, onUp])

  return { pos, dragging, onDragStart }
}
