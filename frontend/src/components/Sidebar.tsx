import { useRef, type ReactNode } from 'react'

interface SidebarProps {
  side: 'left' | 'right'
  open: boolean
  title: string
  width: number
  onWidthChange: (w: number) => void
  minWidth?: number
  maxWidth?: number
  children: ReactNode
  headerExtra?: ReactNode
}

function clamp(v: number, min: number, max: number) {
  return Math.min(Math.max(v, min), max)
}

export default function Sidebar({
  side, open, title, width, onWidthChange,
  minWidth = 240, maxWidth = 560, children, headerExtra,
}: SidebarProps) {
  const isLeft = side === 'left'
  const hiddenTransform = isLeft ? '-translate-x-full' : 'translate-x-full'
  const startRef = useRef<{ x: number; w: number } | null>(null)

  function startResize(e: React.MouseEvent) {
    e.preventDefault()
    startRef.current = { x: e.clientX, w: width }
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }
  function onMove(e: MouseEvent) {
    if (!startRef.current) return
    const delta = e.clientX - startRef.current.x
    const next = isLeft ? startRef.current.w + delta : startRef.current.w - delta
    onWidthChange(clamp(next, minWidth, maxWidth))
  }
  function onUp() {
    startRef.current = null
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  return (
    <div
      className={`absolute top-1 bottom-2 ${isLeft ? 'left-2' : 'right-2'} flex flex-col bg-surface rounded-[12px] shadow-xl ring-1 ring-white/10 transition-transform duration-300 ${
        open ? 'translate-x-0 opacity-100' : `${hiddenTransform} opacity-0 pointer-events-none`
      }`}
      style={{ width }}
    >
      <div className="flex items-center justify-center px-4 py-3 border-b border-idle gap-2">
        <h2 className="text-sm font-semibold text-primary">{title}</h2>
        {headerExtra}
      </div>
      <div className="flex-1 hide-scrollbar">
        {children}
      </div>
      <div
        onMouseDown={startResize}
        className={`absolute top-0 bottom-0 w-1 cursor-col-resize hover:bg-accent/40 transition-colors ${
          isLeft ? 'right-0 translate-x-1/2' : 'left-0 -translate-x-1/2'
        }`}
      />
    </div>
  )
}
