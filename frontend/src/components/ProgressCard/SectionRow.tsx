import type { SectionDef, SectionState } from '../../types/schema'
import { filledCount } from '../../utils/summary'
import StatusIcon from './StatusIcon'
import FieldDetail from './FieldDetail'

interface Props {
  def: SectionDef
  section: SectionState
  expanded: boolean
  onToggle: () => void
}

export default function SectionRow({ def, section, expanded, onToggle }: Props) {
  const { filled, total } = filledCount(section, def)
  return (
    <div
      data-section-row
      onClick={onToggle}
      className="rounded-md cursor-pointer"
    >
      <div className="w-full text-left px-3 py-2 rounded-md hover:bg-base/50 transition-colors flex items-center gap-2">
        <StatusIcon status={section.status} />
        <span className="flex-1 text-[13px] text-primary truncate">{def.title}</span>
        <span className="text-[11px] text-muted tabular-nums">{filled}/{total}</span>
      </div>
      {expanded && (
        <div data-field-detail>
          <FieldDetail def={def} section={section} />
        </div>
      )}
    </div>
  )
}
