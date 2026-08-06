import { useCallback, useRef } from 'react'
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
  expanded: boolean
  onToggleExpand: () => void
  children?: React.ReactNode
}

// 工作台中央主卡（4:3）。两态：
//   默认态：fixed 居中 + 拖拽偏移（calc(-50% + pos)），可拖可缩放，含放大按钮。
//   放大态：absolute 占中右（left:120 让出 ProgressCard 区 → right:16），锁定拖拽、隐藏缩放手柄、显示还原按钮。
// 不复用 FloatingCard：CenterCard 需 calc(-50%+pos) 居中变换，FloatingCard 仅支持 translate(pos)。
// 后续 ChatPanel（Task6）会作为 children 传入；本 task 用占位内容。
export default function CenterCard({ expanded, onToggleExpand, children }: CenterCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)
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
  const { pos, dragging, onDragStart } = useDraggable({
    storageKey: 'centercard.pos',
    defaultPos: CENTER_DEFAULT_POS,
    bounds: CENTER_BOUNDS,
    disabled: expanded,
    clampPosition,
  })
  const { size, resizing, onResizeStart } = useResizable({
    storageKey: 'centercard.size',
    defaultSize: CENTER_DEFAULT_SIZE,
    minSize: CENTER_MIN_SIZE,
    maxSize: CENTER_MAX_SIZE,
    ratio: CENTER_RATIO,
  })
  const { z, bringToFront } = useZStack({ id: 'center', defaultZ: 20 })

  return (
    <div
      ref={cardRef}
      data-center-card
      data-expanded={expanded}
      onMouseDown={bringToFront}
      onDoubleClick={expanded ? undefined : onToggleExpand}
      className={`center-card flex flex-col overflow-hidden rounded-xl bg-surface/95 backdrop-blur-md shadow-2xl${expanded ? ' is-expanded' : ''}${dragging || resizing ? ' is-interacting' : ''}`}
      style={{
        inset: 0,
        width: expanded ? '100%' : size.w,
        height: expanded ? '100%' : size.h,
        transform: `translate3d(${expanded ? 0 : pos.x}px, ${expanded ? 0 : pos.y}px, 0)`,
        zIndex: z,
        opacity: dragging || resizing ? 0.9 : 1,
      }}
    >
      <div
        data-card-handle
        onMouseDown={expanded ? undefined : onDragStart}
        className={`flex items-center px-3 py-0 group${expanded ? '' : ' cursor-move'}`}
      >
        <div className="flex-1" aria-hidden="true" />
        <button
          type="button"
          onClick={onToggleExpand}
          onMouseDown={(e) => e.stopPropagation()}
          className="center-card-expand-button"
          aria-label={expanded ? '还原' : '放大'}
          title={expanded ? '恢复默认大小' : '放大主卡'}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            {expanded ? <path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3" /> : <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />}
          </svg>
        </button>
      </div>
      <div className="flex-1 overflow-hidden relative">
        {children ?? (
          <div className="h-full flex items-center justify-center text-muted text-sm">
            内容占位（ChatPanel 将传入）
          </div>
        )}
        {!expanded && (
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
