import { useState, useRef, useEffect, useCallback } from 'react'

interface Size { w: number; h: number }

function clamp(v: number, min: number, max: number) {
  return Math.min(Math.max(v, min), max)
}

function loadInitial(storageKey: string, fallback: Size): Size {
  const raw = localStorage.getItem(storageKey)
  if (!raw) return fallback
  try {
    const s = JSON.parse(raw)
    if (typeof s.w === 'number' && typeof s.h === 'number') return s
  } catch {
    /* 非法值回退默认 */
  }
  return fallback
}

export function useResizable(opts: {
  storageKey: string
  defaultSize: Size
  minSize: Size
  maxSize: Size
  ratio: number | null
  persist?: boolean
}): { size: Size; resizing: boolean; onResizeStart: (e: React.MouseEvent) => void; resetSize: () => void } {
  const { storageKey, defaultSize, minSize, maxSize, ratio, persist = true } = opts
  const [size, setSize] = useState<Size>(() => (
    persist ? loadInitial(storageKey, defaultSize) : defaultSize
  ))
  const [resizing, setResizing] = useState(false)
  // 起始锚点:拖拽期间不再依赖 state,避免监听器身份在每次 setSize 后变化导致监听器丢失
  const startRef = useRef<{ mouseX: number; mouseY: number; w: number; h: number } | null>(null)

  // 右下角缩放:锁定比例时高度随宽度联动;否则按鼠标横纵位移独立调整。
  const onMove = useCallback((e: MouseEvent) => {
    if (!startRef.current) return
    const dw = e.clientX - startRef.current.mouseX
    const dh = e.clientY - startRef.current.mouseY
    const w = clamp(startRef.current.w + dw, minSize.w, maxSize.w)
    const h = ratio
      ? w / ratio
      : clamp(startRef.current.h + dh, minSize.h, maxSize.h)
    setSize({ w, h })
  }, [minSize.w, maxSize.w, minSize.h, maxSize.h, ratio])

  const onUp = useCallback(() => {
    if (!startRef.current) return
    startRef.current = null
    setResizing(false)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }, [onMove])

  const onResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    startRef.current = { mouseX: e.clientX, mouseY: e.clientY, w: size.w, h: size.h }
    setResizing(true)
    document.body.style.cursor = 'nwse-resize'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [size.w, size.h, onMove, onUp])

  const resetSize = useCallback(() => {
    startRef.current = null
    setResizing(false)
    setSize(defaultSize)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    if (persist) localStorage.setItem(storageKey, JSON.stringify(defaultSize))
    else localStorage.removeItem(storageKey)
  }, [defaultSize, persist, storageKey])

  // 持久化:resizing 从 true → false 时写 localStorage
  useEffect(() => {
    if (persist && !resizing) localStorage.setItem(storageKey, JSON.stringify(size))
  }, [persist, resizing, size, storageKey])

  // 卸载时清理
  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
  }, [onMove, onUp])

  return { size, resizing, onResizeStart, resetSize }
}
