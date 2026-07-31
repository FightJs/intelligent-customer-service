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
  const { pos, dragging, onDragStart } = useDraggable({
    storageKey: 'centercard.pos',
    defaultPos: CENTER_DEFAULT_POS,
    bounds: CENTER_BOUNDS,
    disabled: expanded,
    // 中央卡用 fixed 居中 + translate(calc(-50% + pos)) 定位，pos 是相对视口中心的偏移，
    // 与进度卡的绝对坐标 clamp 模型不兼容（会强制 pos.y>=64 导致拖不到顶部）。
    // 关闭 clamp，让卡片自由拖拽（默认居中，拖出边缘也能拖回）。
    clamp: false,
  })
  const { size, resizing, onResizeStart } = useResizable({
    storageKey: 'centercard.size',
    defaultSize: CENTER_DEFAULT_SIZE,
    minSize: CENTER_MIN_SIZE,
    maxSize: CENTER_MAX_SIZE,
    ratio: CENTER_RATIO,
  })
  const { z, bringToFront } = useZStack({ id: 'center', defaultZ: 20 })

  if (expanded) {
    // 放大态：absolute 占中右，锁定拖拽，无缩放手柄
    return (
      <div
        data-center-card
        data-expanded="true"
        onMouseDown={bringToFront}
        className="absolute flex flex-col overflow-hidden rounded-xl bg-surface ring-1 ring-white/10 shadow-2xl"
        style={{ left: 120, right: 16, top: 16, bottom: 16, zIndex: z }}
      >
        <div className="flex items-center px-3 py-0">
          <span className="flex-1 text-[11px] font-medium text-secondary">中央卡片（放大态）</span>
          <button
            type="button"
            onClick={onToggleExpand}
            className="text-muted text-xs hover:text-secondary px-2 py-1 rounded hover:bg-active-surface"
          >
            还原
          </button>
        </div>
        <div className="flex-1 overflow-hidden">
          {children ?? (
            <div className="h-full flex items-center justify-center text-muted text-sm">
              内容占位（ChatPanel 将传入）
            </div>
          )}
        </div>
      </div>
    )
  }

  // 默认态：fixed 居中 + 拖拽偏移
  // left/top 50% 把原点定在视口中心，transform calc(-50% + pos) 先把卡片回退半个自身尺寸完成居中，再加拖拽偏移 pos。
  return (
    <div
      data-center-card
      data-expanded="false"
      onMouseDown={bringToFront}
      onDoubleClick={onToggleExpand}
      className="fixed flex flex-col overflow-hidden rounded-xl bg-surface/95 backdrop-blur-md shadow-2xl ring-1 ring-white/10"
      style={{
        left: '50%',
        top: '50%',
        width: size.w,
        height: size.h,
        transform: `translate(calc(-50% + ${pos.x}px), calc(-50% + ${pos.y}px))`,
        zIndex: z,
        opacity: dragging || resizing ? 0.9 : 1,
      }}
    >
      <div
        data-card-handle
        onMouseDown={onDragStart}
        className="flex items-center px-3 py-0 cursor-move group"
      >
        <span className="flex-1 text-[11px] font-medium text-secondary group-hover:text-primary transition-colors">
          中央卡片 4:3
        </span>
        <button
          type="button"
          onClick={onToggleExpand}
          onMouseDown={(e) => e.stopPropagation()}
          className="text-muted text-xs hover:text-secondary px-2 py-1 rounded hover:bg-active-surface"
        >
          放大
        </button>
      </div>
      <div className="flex-1 overflow-hidden relative">
        {children ?? (
          <div className="h-full flex items-center justify-center text-muted text-sm">
            内容占位（ChatPanel 将传入）
          </div>
        )}
        {/* 右下角缩放手柄：4:3 ratio 由 useResizable 锁定 */}
        <div
          data-resize-handle
          onMouseDown={onResizeStart}
          className="absolute right-0 bottom-0 w-4 h-4 cursor-nwse-resize"
          style={{
            borderRight: '2px solid rgb(59 130 246)',
            borderBottom: '2px solid rgb(59 130 246)',
            borderBottomRightRadius: '12px',
          }}
        />
      </div>
    </div>
  )
}
