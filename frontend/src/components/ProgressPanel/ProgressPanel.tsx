import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import { makeSummary } from '../../utils/summary'

const STATUS_DOT: Record<string, string> = {
  pending: 'bg-idle',
  active: 'bg-accent',
  complete: 'bg-done',
}

export default function ProgressPanel() {
  const { state } = useFormState()

  return (
    <div className="h-full overflow-y-auto py-2">
      {SECTIONS.map((def) => {
        const sec = state.sections[def.id]
        const summary = makeSummary(sec, def)
        const isCurrent = state.currentSectionId === def.id
        return (
          <div
            key={def.id}
            className={`px-3 py-2 border-l-[3px] ${
              isCurrent ? 'border-accent bg-active-surface' : 'border-transparent'
            }`}
          >
            <div className="flex items-center gap-2">
              <span
                className={`inline-block w-2 h-2 rounded-full ${STATUS_DOT[sec.status]} ${
                  sec.status === 'active' ? 'animate-pulse' : ''
                }`}
              />
              <span className={`text-xs ${isCurrent ? 'text-primary' : 'text-secondary'}`}>
                {def.title}
              </span>
            </div>
            <div className={`text-[11px] mt-0.5 ml-4 truncate ${summary === '未采集' ? 'text-muted' : 'text-secondary'}`}>
              {summary}
            </div>
          </div>
        )
      })}
    </div>
  )
}
