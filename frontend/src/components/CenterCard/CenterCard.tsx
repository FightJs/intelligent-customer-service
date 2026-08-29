import { useCallback, useEffect, useRef } from 'react'
import { useCoarsePointer } from '../../hooks/useCoarsePointer'
import { useDraggable } from '../../hooks/useDraggable'
import { useResizable } from '../../hooks/useResizable'
import { useZStack } from '../../hooks/useZStack'
import {
  CENTER_BOUNDS,
  CENTER_DEFAULT_POS,
  CENTER_DEFAULT_SIZE,
  CENTER_MAX_SIZE,
  CENTER_MIN_SIZE,
  CENTER_RATIO,
} from './centerBounds'

interface CenterCardProps {
  resetToken?: number
  children?: React.ReactNode
}

// 工作台中央问答窗口：进入时使用适配三栏的初始尺寸；可拖拽、自由缩放，按钮用于一键复位。
export default function CenterCard({ resetToken = 0, children }: CenterCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const initialPosition = useCallback(() => {
    const card = cardRef.current
    const zone = card?.closest<HTMLElement>('.workbench-center-zone')
    const stage = card?.closest<HTMLElement>('.workbench-stage')
    if (!zone || !stage) return CENTER_DEFAULT_POS

    const zoneRect = zone.getBoundingClientRect()
    const stageRect = stage.getBoundingClientRect()
    const effectiveWidth = Math.min(CENTER_DEFAULT_SIZE.w, zoneRect.width)
    const zoneCenteredLeft = zoneRect.left + (zoneRect.width - effectiveWidth) / 2
    const stageCenteredLeft = stageRect.left + (stageRect.width - effectiveWidth) / 2
    return { x: Math.round(stageCenteredLeft - zoneCenteredLeft), y: 0 }
  }, [])
  const clampPosition = useCallback((next: { x: number; y: number }, current: { x: number; y: number }) => {
    const card = cardRef.current
    const stage = card?.closest<HTMLElement>('.workbench-stage')
    if (!card || !stage) return next

    const cardRect = card.getBoundingClientRect()
    const stageRect = stage.getBoundingClientRect()
    const intendedX = next.x - current.x
    const intendedY = next.y - current.y
    const minX = stageRect.left - cardRect.left
    const maxX = stageRect.right - cardRect.right
    const minY = stageRect.top - cardRect.top
    const maxY = stageRect.bottom - cardRect.bottom

    // 主卡在整个工作台内硬性限制。边界无可用空间时固定在当前位置，避免回弹。
    const constrain = (delta: number, min: number, max: number) => (
      min > max ? 0 : Math.min(Math.max(delta, min), max)
    )

    return {
      x: current.x + constrain(intendedX, minX, maxX),
      y: current.y + constrain(intendedY, minY, maxY),
    }
  }, [])
  const { pos, dragging, onDragStart, resetPosition } = useDraggable({
    storageKey: 'centercard.pos.v2',
    defaultPos: CENTER_DEFAULT_POS,
    bounds: CENTER_BOUNDS,
    clampPosition,
    persist: false,
  })
  const { size, resizing, onResizeStart, resetSize } = useResizable({
    storageKey: 'centercard.size.v2',
    defaultSize: CENTER_DEFAULT_SIZE,
    minSize: CENTER_MIN_SIZE,
    maxSize: CENTER_MAX_SIZE,
    ratio: CENTER_RATIO,
    persist: false,
  })
  // 主对话框默认高于左侧进度卡，避免输入区被覆盖后无法点击；其他卡片仍可通过交互置顶。
  const { z, bringToFront } = useZStack({ id: 'center', defaultZ: 40 })
  const coarsePointer = useCoarsePointer()

  const restoreInitialLayout = useCallback(() => {
    resetPosition(initialPosition())
    resetSize()
  }, [initialPosition, resetPosition, resetSize])

  useEffect(() => {
    const timer = window.setTimeout(restoreInitialLayout, 50)
    return () => window.clearTimeout(timer)
  }, [resetToken, restoreInitialLayout])

  return (
    <div
      ref={cardRef}
      data-center-card
      onMouseDown={bringToFront}
      onFocusCapture={bringToFront}
      className={`center-card flex flex-col overflow-hidden rounded-xl bg-surface/95 backdrop-blur-md shadow-2xl${dragging || resizing ? ' is-interacting' : ''}`}
      style={coarsePointer
        ? { inset: 0, width: '100%', height: '100%', zIndex: z }
        : {
            inset: 0,
            width: size.w,
            height: size.h,
            transform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
            zIndex: z,
            opacity: dragging || resizing ? 0.9 : 1,
          }}
    >
      <div
        data-card-handle
        onMouseDown={coarsePointer ? undefined : onDragStart}
        className={`flex ${coarsePointer ? 'cursor-default' : 'cursor-move'} items-center px-3 py-0 group`}
      >
        <div className="flex-1" aria-hidden="true" />
        <button
          type="button"
          onClick={restoreInitialLayout}
          onMouseDown={(e) => e.stopPropagation()}
          className="center-card-expand-button"
          aria-label="恢复问答窗口初始位置"
          title="恢复初始大小和位置"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
          </svg>
        </button>
      </div>
      <div className="flex-1 overflow-hidden relative">
        {children ?? (
          <div className="h-full flex items-center justify-center text-muted text-sm">
            内容占位（ChatPanel 将传入）
          </div>
        )}
        {!coarsePointer && (
          <div
            data-resize-handle
            onMouseDown={onResizeStart}
            className="center-card-resize-handle"
          />
        )}
      </div>
    </div>
  )
}
