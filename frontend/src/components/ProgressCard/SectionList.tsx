import type { SectionId } from '../../types/schema'
import { SECTIONS, SECTION_ORDER } from '../../data/sections'
import { useFormState } from '../../state/FormContext'
import { isFieldRequired, isFieldVisible, valueToText } from '../../utils/summary'
import SectionRow from './SectionRow'

interface Props {
  expandedSections: Set<SectionId>
  onToggleSection: (id: SectionId) => void
  completedCollapsed: boolean
  onToggleCompleted: () => void
}

export default function SectionList({
  expandedSections, onToggleSection, completedCollapsed, onToggleCompleted,
}: Props) {
  const { state } = useFormState()

  const completed = SECTION_ORDER.filter((id) => state.sections[id].status === 'complete')
  const skipped = SECTION_ORDER.filter((id) => state.sections[id].status === 'skipped')
  const active = SECTION_ORDER.filter((id) => state.sections[id].status === 'active')
  const pending = SECTION_ORDER.filter((id) => state.sections[id].status === 'pending')

  // 进行中 + 待办合并,按 SECTION_ORDER 顺序(进行中排最前)
  const todoOrder = [...active, ...pending].sort(
    (a, b) => SECTION_ORDER.indexOf(a) - SECTION_ORDER.indexOf(b)
  )

  return (
    <div className="flex-1 overflow-y-auto py-1 hide-scrollbar">
      {/* 已完成分组 */}
      {completed.length > 0 && (
        <div className="px-3">
          <button
            type="button"
            onClick={onToggleCompleted}
            className="w-full text-left py-1.5 flex items-center gap-2 text-[12px] text-muted hover:text-secondary transition-colors"
          >
            <span className="text-[10px] inline-block w-3">{completedCollapsed ? '▸' : '▾'}</span>
            <span className="text-done">✓</span>
            <span>已完成 {completed.length} 项</span>
          </button>
          {!completedCollapsed && (
            <div className="ml-2 mt-0.5 mb-1 space-y-0.5">
              {completed.map((id) => {
                const def = SECTIONS.find((s) => s.id === id)!
                return (
                  <SectionRow
                    key={id}
                    def={def}
                    state={state}
                    expanded={expandedSections.has(id)}
                    onToggle={() => onToggleSection(id)}
                  />
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* 进行中 + 待办 */}
      <div className="px-1 space-y-0.5">
        {todoOrder.map((id) => {
          const def = SECTIONS.find((s) => s.id === id)!
          const isCurrent = state.currentSectionId === id
          const isActive = state.sections[id].status === 'active'
          return (
            <div key={id}>
              <SectionRow
                def={def}
                state={state}
                expanded={expandedSections.has(id)}
                onToggle={() => onToggleSection(id)}
              />
              {isCurrent && isActive && (() => {
                const nextField = def.fields.find((f) => {
                  if (!isFieldRequired(state, id, f)) return false
                  if (!isFieldVisible(f, state.sections[id])) return false
                  const v = state.sections[id].fields[f.id]
                  return !v || valueToText(v, f) === ''
                })
                return nextField ? (
                  <div className="ml-9 px-3 text-[11px] text-accent truncate">▸ 当前在问: {nextField.label}</div>
                ) : null
              })()}
            </div>
          )
        })}
      </div>

      {/* 已跳过(skipped,平铺到末尾) */}
      {skipped.length > 0 && (
        <div className="px-1 mt-2 space-y-0.5">
          {skipped.map((id) => {
            const def = SECTIONS.find((s) => s.id === id)!
            return (
              <SectionRow
                key={id}
                def={def}
                state={state}
                expanded={expandedSections.has(id)}
                onToggle={() => onToggleSection(id)}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}
