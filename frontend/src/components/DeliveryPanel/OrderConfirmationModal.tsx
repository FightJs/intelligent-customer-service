import { useState } from 'react'
import {
  Check,
  ChevronRight,
  Loader2,
  X,
} from 'lucide-react'
import { sendOrder } from '../../api/client'
import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import {
  filledCount,
  makeSummary,
} from '../../utils/summary'

interface OrderConfirmationModalProps {
  onClose: () => void
  onSent: () => void
}

const STEPS = [
  '客户信息',
  '结构化内容',
  '确认发送',
]

export default function OrderConfirmationModal({
  onClose,
  onSent,
}: OrderConfirmationModalProps) {
  const { state } = useFormState()
  const [step, setStep] = useState(0)
  const [sent, setSent] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState(
    '订单发送成功',
  )

  const customer = state.sections.customer
  const customerDefinition = SECTIONS.find(
    (section) => section.id === 'customer',
  )!

  const summaries = SECTIONS.map((definition) => ({
    title: definition.title,
    summary: makeSummary(
      state.sections[definition.id],
      definition,
    ),
  }))

  const progress = (
    step === 0
      ? 33
      : step === 1
        ? 66
        : 100
  )

  const counts = SECTIONS.reduce(
    (result, definition) => {
      const current = filledCount(
        state,
        definition,
      )

      return {
        filled: result.filled + current.filled,
        total: result.total + current.total,
      }
    },
    {
      filled: 0,
      total: 0,
    },
  )

  async function next() {
    if (step < STEPS.length - 1) {
      setStep((current) => current + 1)
      setError('')
      return
    }

    const sessionId = sessionStorage.getItem(
      'ics_session_id',
    )

    if (!sessionId) {
      setError('未找到当前会话，请重新开始对话')
      return
    }

    setSending(true)
    setError('')

    try {
      const result = await sendOrder(sessionId)

      setSuccessMessage(result.message)
      setSent(true)
      onSent()
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : '订单发送失败',
      )
    } finally {
      setSending(false)
    }
  }

  return (
    <div
      className="order-modal-backdrop"
      role="presentation"
    >
      <section
        className="order-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="order-modal-title"
      >
        <header className="order-modal-header">
          <div>
            <h2 id="order-modal-title">
              发送订单
            </h2>
            <p>
              确认需求后发送至管理员后台
            </p>
          </div>

          <button
            type="button"
            className="order-modal-close"
            aria-label="关闭订单确认"
            onClick={onClose}
            disabled={sending}
          >
            <X size={18} />
          </button>
        </header>

        <div className="order-modal-body">
          {sent ? (
            <div className="order-modal-success">
              <span className="order-modal-success-icon">
                <Check size={22} />
              </span>

              <h3>{successMessage}</h3>

              <p>
                需求及三类结构化内容已统一提交，
                管理员现在可以在后台交付物列表中查看。
              </p>

              <button
                type="button"
                className="order-modal-primary"
                onClick={onClose}
              >
                完成
              </button>
            </div>
          ) : (
            <>
              <div
                className="order-modal-steps"
                aria-label="订单确认进度"
              >
                {STEPS.map((label, index) => (
                  <span
                    key={label}
                    className="order-modal-step-group"
                  >
                    <span
                      className={
                        `order-modal-step${
                          index <= step
                            ? ' is-active'
                            : ''
                        }`
                      }
                    >
                      {index < step
                        ? <Check size={12} />
                        : index + 1}
                    </span>

                    <span
                      className={
                        index <= step
                          ? 'is-active'
                          : ''
                      }
                    >
                      {label}
                    </span>

                    {index < STEPS.length - 1 && (
                      <span className="order-modal-step-line" />
                    )}
                  </span>
                ))}
              </div>

              <div className="order-modal-progress">
                <span
                  style={{
                    width: `${progress}%`,
                  }}
                />
              </div>

              {step === 0 && (
                <>
                  <p className="order-modal-helper">
                    客户信息已从实时需求表自动带入，
                    请确认后继续。
                  </p>

                  <div className="order-modal-fields">
                    {[
                      'brand',
                      'contact',
                      'phone',
                    ].map((fieldId) => {
                      const definition = (
                        customerDefinition.fields.find(
                          (field) => field.id === fieldId,
                        )!
                      )

                      const value = customer.fields[fieldId]
                      const text = (
                        value
                        && value.type === 'text'
                          ? value.value
                          : ''
                      )

                      return (
                        <div
                          className="order-modal-field"
                          key={fieldId}
                        >
                          <span>{definition.label}</span>
                          <strong>
                            {text || '未填写'}
                          </strong>
                        </div>
                      )
                    })}
                  </div>
                </>
              )}

              {step === 1 && (
                <>
                  <p className="order-modal-helper">
                    当前需求已整理完成，共采集
                    {' '}
                    {counts.filled}/{counts.total}
                    {' '}
                    个必填信息。
                  </p>

                  <div className="order-modal-deliverables">
                    {[
                      '场景设计说明',
                      '设备参数清单',
                      '需求确认书',
                    ].map((label) => (
                      <div key={label}>
                        <span className="order-modal-file-icon">
                          ▤
                        </span>
                        {label}
                        <span>已整理</span>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {step === 2 && (
                <>
                  <p className="order-modal-helper">
                    确认发送后，管理员后台会新增一条综合交付记录。
                  </p>

                  <div className="order-modal-summary-list">
                    {summaries.slice(0, 5).map((item) => (
                      <div key={item.title}>
                        <span>{item.title}</span>
                        <strong>{item.summary}</strong>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {error && (
                <p
                  className="mt-3 text-sm text-danger"
                  role="alert"
                >
                  {error}
                </p>
              )}

              <div className="order-modal-actions">
                <button
                  type="button"
                  className="order-modal-secondary"
                  onClick={onClose}
                  disabled={sending}
                >
                  取消
                </button>

                <button
                  type="button"
                  className="order-modal-primary"
                  onClick={() => void next()}
                  disabled={sending}
                >
                  {sending ? (
                    <>
                      <Loader2
                        size={14}
                        className="animate-spin"
                      />
                      发送中
                    </>
                  ) : step === STEPS.length - 1 ? (
                    '确认发送'
                  ) : (
                    <>
                      下一步
                      <ChevronRight size={14} />
                    </>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </section>
    </div>
  )
}
