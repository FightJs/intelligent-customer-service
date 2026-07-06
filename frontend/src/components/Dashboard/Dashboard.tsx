import { useState } from 'react'
import { SECTIONS } from '../../data/sections'
import { useFormState } from '../../state/FormContext'
import SectionCard from './SectionCard'
import CardExpanded from './CardExpanded'
import type { SectionId } from '../../types/schema'

export default function Dashboard({ onGenerate }: { onGenerate?: () => void }) {
  const { state } = useFormState()
  const [expandedId, setExpandedId] = useState<SectionId | null>(null)
  const allDone = SECTIONS.every((def) => {
    if (def.id === 'notes') return true
    return state.sections[def.id].status === 'complete'
  })

  return (
    <div className="h-full overflow-y-auto p-3">
      {allDone && (
        <button
          type="button"
          onClick={onGenerate}
          className="w-full mb-3 bg-done text-base font-semibold py-2.5 rounded-card text-sm"
        >
          生成方案 ✓
        </button>
      )}
      <div className="grid grid-cols-2 gap-2">
        {SECTIONS.map((def) =>
          expandedId === def.id ? (
            <div key={def.id} className="col-span-2">
              <CardExpanded def={def} onCollapse={() => setExpandedId(null)} />
            </div>
          ) : (
            <SectionCard
              key={def.id}
              def={def}
              expanded={false}
              onToggle={() => setExpandedId(def.id)}
            />
          ),
        )}
      </div>
    </div>
  )
}
