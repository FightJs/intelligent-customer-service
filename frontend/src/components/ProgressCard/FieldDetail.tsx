import type { SectionDef, SectionState } from '../../types/schema'
import { valueToText, isFieldVisible } from '../../utils/summary'

interface Props {
  def: SectionDef
  section: SectionState
}

export default function FieldDetail({ def, section }: Props) {
  const visibleFields = def.fields.filter((f) => isFieldVisible(f, section))
  return (
    <div className="ml-6 px-3 py-1.5 space-y-1">
      {visibleFields.map((f) => {
        const v = section.fields[f.id]
        const text = v ? valueToText(v, f) : ''
        return (
          <div key={f.id} className="flex items-baseline gap-2 text-[12px] min-w-0">
            <span className="text-secondary shrink-0">{f.label}</span>
            <span className="flex-1 truncate text-right">
              {text ? <span className="text-primary">{text}</span> : <span className="text-muted">(未填)</span>}
            </span>
          </div>
        )
      })}
    </div>
  )
}
