import { useFormState } from '../../state/FormContext'
import FieldEditor from '../FieldEditor'
import type { SectionDef, FieldValue } from '../../types/schema'

interface Props {
  def: SectionDef
  onCollapse: () => void
}

export default function CardExpanded({ def, onCollapse }: Props) {
  const { state, dispatch } = useFormState()
  const sectionState = state.sections[def.id]

  function update(fieldId: string, v: FieldValue) {
    dispatch({ type: 'update_field', sectionId: def.id, fieldId, value: v })
  }

  return (
    <div className="bg-active-surface border border-accent rounded-card p-3">
      <div className="flex justify-between items-center mb-3">
        <span className="text-accent text-sm font-semibold">● {def.title} · 编辑中</span>
        <button
          type="button"
          onClick={onCollapse}
          className="text-xs bg-accent text-white px-3 py-1 rounded-pill"
        >
          完成
        </button>
      </div>
      {def.fields.map((f) => (
        <FieldEditor
          key={f.id}
          def={f}
          value={sectionState.fields[f.id]}
          onChange={(v) => update(f.id, v)}
        />
      ))}
    </div>
  )
}
