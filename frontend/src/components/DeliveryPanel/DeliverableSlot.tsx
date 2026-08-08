import {
  CheckCircle2,
  FileSpreadsheet,
  FileText,
  FileType2,
  Send,
} from 'lucide-react'
import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import { filledCount } from '../../utils/summary'

const STRUCTURED_CONTENT = [
  {
    label: '场景设计说明',
    description: '直播场景与空间设计结构',
    icon: FileText,
    color: '#ef4444',
  },
  {
    label: '设备参数清单',
    description: '现有设备与推荐设备结构',
    icon: FileSpreadsheet,
    color: '#22c55e',
  },
  {
    label: '需求确认书',
    description: '客户完整需求确认结构',
    icon: FileType2,
    color: '#3b82f6',
  },
] as const

interface DeliverableSlotProps {
  orderSent?: boolean
  onSendOrder?: () => void
}

export default function DeliverableSlot({
  orderSent = false,
  onSendOrder,
}: DeliverableSlotProps) {
  const { state } = useFormState()

  let filled = 0
  let total = 0

  for (const definition of SECTIONS) {
    const progress = filledCount(
      state.sections[definition.id],
      definition,
    )

    filled += progress.filled
    total += progress.total
  }

  const canSend = (
    total > 0
    && filled === total
  )

  return (
    <section className="workbench-slot deliverable-slot">
      <div className="delivery-panel-scroll flex-1 min-h-0 overflow-y-auto space-y-4 pr-1">
        <section>
          <h3 className="text-secondary text-xs mb-2">
            AI 结构化内容（{filled}/{total}）
          </h3>

          <p className="mb-3 text-[11px] leading-5 text-muted">
            以下内容由系统根据客户需求表统一整理，无需单独操作。
          </p>

          <div className="deliverable-file-grid">
            {STRUCTURED_CONTENT.map(({
              label,
              description,
              icon: Icon,
              color,
            }) => (
              <div
                key={label}
                className="deliverable-file-row pointer-events-none select-none"
                aria-label={`${label}，由系统统一整理`}
              >
                <span className="deliverable-file-icon">
                  <Icon
                    size={19}
                    color={color}
                    aria-hidden="true"
                  />
                </span>

                <span className="min-w-0 flex-1">
                  <span className="deliverable-file-label block">
                    {label}
                  </span>

                  <span className="block truncate text-[10px] text-muted">
                    {description}
                  </span>
                </span>
              </div>
            ))}
          </div>

          <p className="mt-3 text-[11px] leading-5 text-muted">
            {canSend
              ? '请先查看右上角客户需求表，确认无误后发送订单。'
              : '完成全部必填信息后即可发送订单。'}
          </p>
        </section>
      </div>

      <button
        type="button"
        className="delivery-order-button"
        onClick={onSendOrder}
        disabled={!canSend || orderSent}
      >
        {orderSent ? (
          <>
            <CheckCircle2 size={15} />
            订单已发送
          </>
        ) : (
          <>
            <Send size={15} />
            发送订单
          </>
        )}
      </button>
    </section>
  )
}