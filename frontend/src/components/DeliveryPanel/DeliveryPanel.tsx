import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import { makeSummary } from '../../utils/summary'

const OVERVIEW_SECTION_IDS = ['customer', 'industry', 'venue', 'budget', 'goal'] as const

export default function DeliveryPanel() {
  const { state } = useFormState()
  return (
    <div className="h-full p-4 space-y-4 overflow-y-auto">
      <section>
        <h3 className="text-secondary text-xs mb-2">方案概要</h3>
        <div className="grid grid-cols-2 gap-2">
          {OVERVIEW_SECTION_IDS.map((id) => {
            const sec = state.sections[id]
            const def = SECTIONS.find((s) => s.id === id)!
            return (
              <div key={id} className="bg-surface rounded-card p-2.5">
                <div className="text-muted text-[10px]">{def.title}</div>
                <div className="text-primary text-xs truncate">
                  {makeSummary(sec, def)}
                </div>
              </div>
            )
          })}
        </div>
      </section>

    </div>
  )
}
