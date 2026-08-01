import { type ReactNode } from 'react'

interface FloatingCardProps {
  pos: { x: number; y: number }
  dragging: boolean
  onDragStart: (e: React.MouseEvent) => void
  z: number
  onBringToFront: () => void
  width: number
  height?: number
  resizing?: boolean
  onResizeStart?: (e: React.MouseEvent) => void
  handleLabel?: string
  handleExtra?: ReactNode
  children: ReactNode
  className?: string
}

// 通用浮动卡片壳:固定定位 + transform 平移 + z-index 层叠 + 拖拽手柄。
// 由 ProgressCard 等可拖拽卡片复用,统一 border/ring/shadow/backdrop-blur/rounded-xl 外观。
export default function FloatingCard({
  pos,
  dragging,
  onDragStart,
  z,
  onBringToFront,
  width,
  height,
  resizing = false,
  onResizeStart,
  handleLabel,
  handleExtra,
  children,
  className = '',
}: FloatingCardProps) {
  return (
    <div
      data-floating-card
      onMouseDown={onBringToFront}
      className={`floating-card fixed flex flex-col overflow-hidden rounded-xl bg-surface/95 backdrop-blur-md shadow-2xl ${className}`}
      style={{
        transform: `translate(${pos.x}px, ${pos.y}px)`,
        zIndex: z,
        width,
        height,
        opacity: dragging || resizing ? 0.9 : 1,
      }}
    >
      {handleLabel !== undefined && (
        <div
          data-card-handle
          onMouseDown={onDragStart}
          className="flex items-center px-3 py-2.5 border-b border-idle/30 cursor-move group"
        >
          <span className="flex-1 text-[13px] font-medium text-secondary group-hover:text-primary transition-colors">
            {handleLabel}
          </span>
          {handleExtra}
        </div>
      )}
      {children}
      {onResizeStart && (
        <div
          data-resize-handle
          onMouseDown={onResizeStart}
          className="floating-card-resize-handle"
          aria-label="调整卡片大小"
        />
      )}
    </div>
  )
}
