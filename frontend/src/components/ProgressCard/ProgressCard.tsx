import { useState } from 'react'
import { useMemo } from 'react'
import type { SectionId } from '../../types/schema'
import { SECTIONS, SECTION_ORDER } from '../../data/sections'
import { useFormState } from '../../state/FormContext'
import { filledCount } from '../../utils/summary'
import { useDraggable } from '../../hooks/useDraggable'
import { useResizable } from '../../hooks/useResizable'
import { useZStack } from '../../hooks/useZStack'
import FloatingCard from '../FloatingCard'
import SectionList from './SectionList'

interface Props {
  visible: boolean
}

// 稳定引用:避免 clampPos 依赖 [bounds] 每次渲染都重新绑定 resize 监听器
const PROGRESS_DEFAULT_SIZE = { w: 280, h: 540 }
const PROGRESS_MIN_SIZE = { w: 240, h: 260 }
const PROGRESS_MAX_SIZE = { w: 560, h: 760 }

export default function ProgressCard({ visible }: Props) {
  const { state } = useFormState()
  const [expanded, setExpanded] = useState(false)
  const { size, resizing, onResizeStart } = useResizable({
    storageKey: 'progresscard.size',
    defaultSize: PROGRESS_DEFAULT_SIZE,
    minSize: PROGRESS_MIN_SIZE,
    maxSize: PROGRESS_MAX_SIZE,
    ratio: null,
  })
  const progressBounds = useMemo(() => ({
    width: size.w,
    minHeight: size.h,
    topMargin: 48,
    margin: 8,
  }), [size.h, size.w])
  const { pos, dragging, onDragStart } = useDraggable({
    storageKey: 'progresscard.pos',
    defaultPos: { x: 16, y: 80 },
    bounds: progressBounds,
    disabled: expanded || resizing,
  })
  const { z, bringToFront } = useZStack({ id: 'progress', defaultZ: 30 })
  const [expandedSections, setExpandedSections] = useState<Set<SectionId>>(new Set())
  const [completedCollapsed, setCompletedCollapsed] = useState(true)

  if (!visible) return null

  function toggleSection(id: SectionId) {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // 统计
  let doneCount = 0
  let activeCount = 0
  let pendingCount = 0
  for (const id of SECTION_ORDER) {
    const status = state.sections[id].status
    if (status === 'complete') doneCount++
    else if (status === 'active') activeCount++
    else if (status === 'pending') pendingCount++
  }
  const totalFilled = SECTIONS.reduce((acc, def) => acc + filledCount(state.sections[def.id], def).filled, 0)
  const totalRequired = SECTIONS.reduce((acc, def) => acc + filledCount(state.sections[def.id], def).total, 0)

  return (
    <FloatingCard
      pos={pos}
      dragging={dragging}
      onDragStart={onDragStart}
      z={z}
      onBringToFront={bringToFront}
      width={size.w}
      height={expanded ? undefined : size.h}
      resizing={resizing}
      onResizeStart={expanded ? undefined : onResizeStart}
      className={`progress-card${expanded ? ' is-expanded' : ''}`}
      handleLabel={`采集进度 ${totalFilled}/${totalRequired}`}
      handleExtra={
        <>
          <button
            type="button"
            className="p-1 rounded text-muted hover:text-secondary"
            aria-label="更多操作"
            onMouseDown={(e) => e.stopPropagation()}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="5" cy="12" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="19" cy="12" r="2" />
            </svg>
          </button>
          <button
            type="button"
            className="p-1 ml-1 rounded text-muted hover:text-secondary"
            aria-label={expanded ? '收起进度' : '展开'}
            onMouseDown={(e) => e.stopPropagation()}
            onClick={() => setExpanded((value) => !value)}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3" />
            </svg>
          </button>
        </>
      }
    >
      {/* 列表 + 底部汇总:maxHeight 限定卡片可视高度,超出时内部滚动 */}
      <div className="flex flex-1 flex-col min-h-0" style={{ maxHeight: expanded ? 'none' : undefined }}>
        <SectionList
          expandedSections={expandedSections}
          onToggleSection={toggleSection}
          completedCollapsed={completedCollapsed}
          onToggleCompleted={() => setCompletedCollapsed((v) => !v)}
        />

        {/* 底部汇总 */}
        <div className="px-3 py-2 border-t border-idle/30 text-[11px] text-muted flex items-center gap-3">
          <span className="text-done">✓ {doneCount}</span>
          <span className="text-accent">◐ {activeCount}</span>
          <span>{pendingCount} 待</span>
        </div>
      </div>
    </FloatingCard>
  )
}
