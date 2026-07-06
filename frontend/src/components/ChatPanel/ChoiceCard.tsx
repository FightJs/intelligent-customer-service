import type { FieldDef, FieldValue } from '../../types/schema'

interface Props {
  def: FieldDef
  value: FieldValue
  onCommit: (v: FieldValue) => void
}

export default function ChoiceCard({ def, value, onCommit }: Props) {
  if (def.type !== 'choice-single' && def.type !== 'choice-multi') return null
  if (value.type !== 'choice-single' && value.type !== 'choice-multi') return null
  const options = def.options ?? []
  const isMulti = def.type === 'choice-multi'

  const selected: string[] = value.type === 'choice-single'
    ? (value.value ? [value.value] : [])
    : value.value

  function toggle(optVal: string) {
    if (isMulti) {
      const set = new Set(selected)
      if (set.has(optVal)) set.delete(optVal)
      else set.add(optVal)
      onCommit({ type: 'choice-multi', value: Array.from(set) })
    } else {
      onCommit({ type: 'choice-single', value: optVal })
    }
  }

  return (
    <div className="mt-2">
      <div className="flex flex-wrap gap-1.5">
        {options.map((o) => {
          const active = selected.includes(o.value)
          return (
            <button
              key={o.value}
              type="button"
              onClick={() => toggle(o.value)}
              className={`px-3 py-1.5 text-xs rounded-pill transition-colors ${
                active ? 'bg-accent text-white' : 'bg-base text-secondary hover:bg-idle'
              }`}
            >
              {o.label}
            </button>
          )
        })}
      </div>
      {isMulti && (
        <div className="text-muted text-[10px] mt-1.5">
          已选 {selected.length} 项{isMulti ? ' · 可继续选' : ''}
        </div>
      )}
    </div>
  )
}
