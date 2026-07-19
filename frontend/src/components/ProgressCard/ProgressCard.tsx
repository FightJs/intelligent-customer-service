import { useState } from 'react'
import type { SectionId } from '../../types/schema'
import { SECTIONS, SECTION_ORDER } from '../../data/sections'
import { useFormState } from '../../state/FormContext'
import { filledCount } from '../../utils/summary'
import { useCardDrag } from './useCardDrag'
import SectionList from './SectionList'

interface Props {
  visible: boolean
}

export default function ProgressCard({ visible }: Props) {
  const { state } = useFormState()
  const { pos, dragging, onHeaderMouseDown } = useCardDrag()
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
    <div
      data-progress-card
      data-dragging={dragging}
      className={`fixed z-30 w-[280px] bg-surface/95 backdrop-blur-md rounded-xl shadow-2xl ring-1 ring-white/10 flex flex-col overflow-hidden transition-[opacity,transform] duration-100 ${
        dragging ? 'opacity-90 scale-[0.98]' : 'opacity-100'
      }`}
      style={{
        transform: `translate(${pos.x}px, ${pos.y}px)`,
        maxHeight: '70vh',
      }}
    >
      {/* Header(拖拽手柄) */}
      <div
        data-card-header
        onMouseDown={onHeaderMouseDown}
        className="flex items-center px-3 py-2.5 border-b border-idle/30 cursor-move group"
      >
        <h2 className="flex-1 text-[13px] font-medium text-secondary group-hover:text-primary transition-colors">
          采集进度 <span className="text-muted tabular-nums">{totalFilled}/{totalRequired}</span>
        </h2>
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
          aria-label="展开"
          onMouseDown={(e) => e.stopPropagation()}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3" />
          </svg>
        </button>
      </div>

      {/* 列表 */}
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
  )
}
