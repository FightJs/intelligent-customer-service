import { useState, useRef, useEffect, useCallback } from 'react'

const STORAGE_KEY = 'progresscard.pos'
const CARD_WIDTH = 280
const CARD_MIN_HEIGHT = 80
const TOPBAR_HEIGHT = 40
const MARGIN = 8

const DEFAULT_POS: Pos = { x: 16, y: 80 }

interface Pos { x: number; y: number }

function clamp(v: number, min: number, max: number) {
  return Math.min(Math.max(v, min), max)
}

function loadInitialPos(): Pos {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return DEFAULT_POS
  try {
    const p = JSON.parse(raw)
    if (typeof p.x === 'number' && typeof p.y === 'number') return p
  } catch {
    /* fall through */
  }
  return DEFAULT_POS
}

export function useCardDrag() {
  const [pos, setPos] = useState<Pos>(loadInitialPos)
  const [dragging, setDragging] = useState(false)
  const startRef = useRef<{ mouseX: number; mouseY: number; posX: number; posY: number } | null>(null)

  const clampPos = useCallback((p: Pos): Pos => {
    const maxX = window.innerWidth - CARD_WIDTH - MARGIN
    const maxY = window.innerHeight - CARD_MIN_HEIGHT - MARGIN
    return {
      x: clamp(p.x, MARGIN, Math.max(MARGIN, maxX)),
      y: clamp(p.y, TOPBAR_HEIGHT + MARGIN, Math.max(TOPBAR_HEIGHT + MARGIN, maxY)),
    }
  }, [])

  const onMove = useCallback((e: MouseEvent) => {
    if (!startRef.current) return
    const dx = e.clientX - startRef.current.mouseX
    const dy = e.clientY - startRef.current.mouseY
    const next = clampPos({
      x: startRef.current.posX + dx,
      y: startRef.current.posY + dy,
    })
    setPos(next)
  }, [clampPos])

  const onUp = useCallback(() => {
    if (!startRef.current) return
    startRef.current = null
    setDragging(false)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }, [onMove])

  const onHeaderMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    startRef.current = { mouseX: e.clientX, mouseY: e.clientY, posX: pos.x, posY: pos.y }
    setDragging(true)
    document.body.style.cursor = 'move'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [pos, onMove, onUp])

  // 持久化:dragging 从 true → false 时写 localStorage
  useEffect(() => {
    if (!dragging) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(pos))
    }
  }, [dragging, pos])

  // 窗口缩放重新 clamp
  useEffect(() => {
    function onResize() {
      setPos((p) => clampPos(p))
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [clampPos])

  // 卸载时清理
  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
  }, [onMove, onUp])

  return { pos, dragging, onHeaderMouseDown }
}
