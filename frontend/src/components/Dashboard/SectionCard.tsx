import type { SectionDef } from '../../types/schema'
import { useFormState } from '../../state/FormContext'
import { makeSummary, filledCount } from '../../utils/summary'

interface Props {
  def: SectionDef
  expanded: boolean
  onToggle: () => void
}

const STATUS_COLOR: Record<string, string> = {
  pending: 'bg-idle',
  active: 'bg-accent',
  complete: 'bg-done',
}

export default function SectionCard({ def, expanded: _expanded, onToggle }: Props) {
  const { state } = useFormState()
  const sec = state.sections[def.id]
  const { filled, total } = filledCount(sec, def)
  const summary = makeSummary(sec, def)
  const isCurrent = state.currentSectionId === def.id

  return (
    <button
      type="button"
      onClick={onToggle}
      className={`text-left bg-surface rounded-card p-2.5 border-l-[3px] transition-colors w-full ${
        sec.status === 'complete' ? 'border-done'
        : isCurrent ? 'border-accent'
        : 'border-idle'
      } ${sec.status === 'pending' ? 'opacity-60' : ''}`}
    >
      <div className="text-secondary text-[11px] mb-0.5">{def.title}</div>
      <div className="text-primary text-xs truncate">{summary}</div>
      <div className="flex items-center gap-1.5 mt-1.5">
        <div className={`h-1 w-6 rounded ${STATUS_COLOR[sec.status]}`} />
        <span className="text-muted text-[10px]">
          {sec.status === 'complete' ? '✓' : `缺 ${total - filled} 项`}
        </span>
      </div>
    </button>
  )
}
