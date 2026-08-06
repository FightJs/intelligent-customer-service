import { X } from 'lucide-react'
import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import { makeSummary } from '../../utils/summary'

interface FormPreviewModalProps {
  onClose: () => void
}

export default function FormPreviewModal({ onClose }: FormPreviewModalProps) {
  const { state } = useFormState()

  return (
    <div className="form-preview-modal-backdrop" role="presentation">
      <section className="form-preview-modal" role="dialog" aria-modal="true" aria-labelledby="form-preview-title">
        <header className="form-preview-modal-header">
          <div><h2 id="form-preview-title">需求表预览</h2><p>当前会话已采集信息</p></div>
          <button type="button" className="order-modal-close" aria-label="关闭需求表预览" onClick={onClose}><X size={18} /></button>
        </header>
        <div className="form-preview-modal-body">
          {SECTIONS.map((def) => <div className="form-preview-section" key={def.id}><span>{def.title}</span><strong>{makeSummary(state.sections[def.id], def)}</strong></div>)}
        </div>
      </section>
    </div>
  )
}
