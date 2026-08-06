import { useState } from 'react'
import { Check, ChevronRight, X } from 'lucide-react'
import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import { filledCount, makeSummary } from '../../utils/summary'

interface OrderConfirmationModalProps {
  onClose: () => void
}

const STEPS = ['客户信息', '交付物', '确认发送']

export default function OrderConfirmationModal({ onClose }: OrderConfirmationModalProps) {
  const { state } = useFormState()
  const [step, setStep] = useState(0)
  const [sent, setSent] = useState(false)
  const customer = state.sections.customer
  const customerDef = SECTIONS.find((section) => section.id === 'customer')!
  const summaries = SECTIONS.map((def) => ({
    title: def.title,
    summary: makeSummary(state.sections[def.id], def),
  }))
  const progress = step === 0 ? 33 : step === 1 ? 66 : 100
  const { filled, total } = SECTIONS.reduce(
    (result, def) => {
      const count = filledCount(state.sections[def.id], def)
      return { filled: result.filled + count.filled, total: result.total + count.total }
    },
    { filled: 0, total: 0 },
  )

  function next() {
    if (step < STEPS.length - 1) setStep((current) => current + 1)
    else setSent(true)
  }

  return (
    <div className="order-modal-backdrop" role="presentation">
      <section className="order-modal" role="dialog" aria-modal="true" aria-labelledby="order-modal-title">
        <header className="order-modal-header">
          <div>
            <h2 id="order-modal-title">发送订单</h2>
            <p>确认需求后发送给交付方</p>
          </div>
          <button type="button" className="order-modal-close" aria-label="关闭订单确认" onClick={onClose}>
            <X size={18} />
          </button>
        </header>
        <div className="order-modal-body">
          {sent ? (
            <div className="order-modal-success">
              <span className="order-modal-success-icon"><Check size={22} /></span>
              <h3>订单已准备发送</h3>
              <p>发送接口将在后端接入后启用，当前已完成前端确认流程。</p>
              <button type="button" className="order-modal-primary" onClick={onClose}>完成</button>
            </div>
          ) : (
            <>
              <div className="order-modal-steps" aria-label="订单确认进度">
                {STEPS.map((label, index) => (
                  <span key={label} className="order-modal-step-group">
                    <span className={`order-modal-step${index <= step ? ' is-active' : ''}`}>{index < step ? <Check size={12} /> : index + 1}</span>
                    <span className={index <= step ? 'is-active' : ''}>{label}</span>
                    {index < STEPS.length - 1 && <span className="order-modal-step-line" />}
                  </span>
                ))}
              </div>
              <div className="order-modal-progress"><span style={{ width: `${progress}%` }} /></div>
              {step === 0 && (
                <>
                  <p className="order-modal-helper">客户信息已从当前需求表自动带入，请确认后继续。</p>
                  <div className="order-modal-fields">
                    {['brand', 'contact', 'phone'].map((fieldId) => {
                      const field = customerDef.fields.find((item) => item.id === fieldId)!
                      const value = customer.fields[fieldId]
                      const text = value && value.type === 'text' ? value.value : ''
                      return <div className="order-modal-field" key={fieldId}><span>{field.label}</span><strong>{text || '未填写'}</strong></div>
                    })}
                  </div>
                </>
              )}
              {step === 1 && (
                <>
                  <p className="order-modal-helper">当前需求已整理为交付物清单，共 {filled}/{total} 个必填信息已采集。</p>
                  <div className="order-modal-deliverables">
                    {['场景设计说明', '设备参数清单', '需求确认书'].map((label) => <div key={label}><span className="order-modal-file-icon">▤</span>{label}<span>待生成</span></div>)}
                  </div>
                </>
              )}
              {step === 2 && (
                <>
                  <p className="order-modal-helper">请确认以下需求概要，当前仅完成前端确认，不会调用后端发送接口。</p>
                  <div className="order-modal-summary-list">
                    {summaries.slice(0, 5).map((item) => <div key={item.title}><span>{item.title}</span><strong>{item.summary}</strong></div>)}
                  </div>
                </>
              )}
              <div className="order-modal-actions">
                <button type="button" className="order-modal-secondary" onClick={onClose}>取消</button>
                <button type="button" className="order-modal-primary" onClick={next}>{step === STEPS.length - 1 ? '确认发送' : '下一步'}<ChevronRight size={14} /></button>
              </div>
            </>
          )}
        </div>
      </section>
    </div>
  )
}
