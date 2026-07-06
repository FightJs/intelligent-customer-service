import type { FieldDef, FieldValue } from '../types/schema'
import ChoiceCard from './ChatPanel/ChoiceCard'
import DimensionInput from './ChatPanel/DimensionInput'
import ImageUpload from './ChatPanel/ImageUpload'

interface Props {
  def: FieldDef
  value: FieldValue
  onChange: (v: FieldValue) => void
}

export default function FieldEditor({ def, value, onChange }: Props) {
  function renderInput() {
    switch (def.type) {
      case 'choice-single':
      case 'choice-multi':
        return <ChoiceCard def={def} value={value} onCommit={onChange} />
      case 'dimension':
        return <DimensionInput def={def} value={value} onChange={onChange} />
      case 'image':
        return <ImageUpload value={value} onChange={onChange} />
      case 'text':
        return (
          <input
            type="text"
            value={value.type === 'text' ? value.value : ''}
            onChange={(e) => onChange({ type: 'text', value: e.target.value })}
            placeholder={def.placeholder}
            className="w-full bg-base border border-idle rounded px-3 py-2 text-sm text-primary placeholder:text-muted outline-none focus:border-accent"
          />
        )
      default:
        return null
    }
  }

  return (
    <div className="mb-3">
      <div className="text-secondary text-xs mb-1">
        {def.label}{def.required && <span className="text-accent ml-0.5">*</span>}
      </div>
      {renderInput()}
    </div>
  )
}
