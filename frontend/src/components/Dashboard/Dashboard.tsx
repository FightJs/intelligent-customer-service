import { useState } from 'react'
import { SECTIONS } from '../../data/sections'
import SectionCard from './SectionCard'
import CardExpanded from './CardExpanded'
import type { SectionId } from '../../types/schema'

export default function Dashboard() {
  const [expandedId, setExpandedId] = useState<SectionId | null>(null)

  return (
    <div className="h-full overflow-y-auto p-3">
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
