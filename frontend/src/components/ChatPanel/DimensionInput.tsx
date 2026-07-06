import type { FieldDef, FieldValue } from '../../types/schema'

interface Props {
  def: FieldDef
  value: FieldValue
  onChange: (v: FieldValue) => void
}

export default function DimensionInput({ def, value, onChange }: Props) {
  if (value.type !== 'dimension') return null
  const dims = def.dims ?? []
  const unit = def.unit ?? ''
  const current = value.value

  function update(dim: string, v: string) {
    onChange({ type: 'dimension', value: { ...current, [dim]: v } })
  }

  return (
    <div className="mt-2 flex items-center gap-1.5 flex-wrap">
      {dims.map((d, i) => (
        <div key={d} className="flex items-center gap-1.5">
          <span className="text-secondary text-xs">{d}</span>
          <input
            type="number"
            inputMode="decimal"
            value={current[d] ?? ''}
            onChange={(e) => update(d, e.target.value)}
            placeholder="0"
            className="w-14 bg-base border border-idle rounded text-primary text-xs px-2 py-1 focus:border-accent outline-none"
          />
          {i < dims.length - 1 && <span className="text-muted text-xs">×</span>}
        </div>
      ))}
      {unit && <span className="text-muted text-xs ml-1">{unit}</span>}
    </div>
  )
}
