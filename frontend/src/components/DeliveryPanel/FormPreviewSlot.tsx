import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import { filledCount, makeSummary } from '../../utils/summary'

interface FormPreviewSlotProps {
  onPreview?: () => void
}

export default function FormPreviewSlot({ onPreview }: FormPreviewSlotProps) {
  const { state } = useFormState()
  const previewSections = SECTIONS.slice(0, 5)
  const progress = SECTIONS.reduce(
    (result, def) => {
      const count = filledCount(state.sections[def.id], def)
      return { filled: result.filled + count.filled, total: result.total + count.total }
    },
    { filled: 0, total: 0 },
  )

  return (
    <button
      type="button"
      className="form-preview-content form-preview-trigger"
      aria-label="预览需求表"
      onClick={onPreview}
    >
      <span className="requirement-preview" aria-hidden="true">
        <span className="requirement-preview-header">
          <span>需求表预览</span>
          <span>{progress.filled}/{progress.total}</span>
        </span>
        <span className="requirement-preview-table">
          {previewSections.map((def) => {
            const title = def.title.split('、')[1] ?? def.title
            return (
              <span className="requirement-preview-row" key={def.id}>
                <span>{title}</span>
                <span>{makeSummary(state.sections[def.id], def)}</span>
              </span>
            )
          })}
        </span>
        <span className="requirement-preview-footer">点击查看完整需求表</span>
      </span>
      <span className="sr-only">预览需求表</span>
    </button>
  )
}
