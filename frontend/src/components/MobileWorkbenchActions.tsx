import { CheckCircle2, ClipboardList, LayoutDashboard, Send } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useFormState } from '../state/FormContext'

interface MobileWorkbenchActionsProps {
  role?: string
  previewOpen: boolean
  orderSent: boolean
  onPreview: () => void
  onSendOrder: () => void
}

export default function MobileWorkbenchActions({
  role,
  previewOpen,
  orderSent,
  onPreview,
  onSendOrder,
}: MobileWorkbenchActionsProps) {
  const { state } = useFormState()
  const isGuest = role === 'guest'
  const submitted = orderSent || state.completed
  const canSend = state.currentFieldId === '' && !submitted

  return (
    <nav className="mobile-workbench-actions" aria-label="手机端工作台快捷操作">
      <button
        type="button"
        className={previewOpen ? 'is-active' : ''}
        onClick={onPreview}
        aria-pressed={previewOpen}
      >
        <ClipboardList size={16} aria-hidden="true" />
        需求表
      </button>

      {!isGuest && (
        <button
          type="button"
          onClick={onSendOrder}
          disabled={!canSend}
          title={canSend ? '确认并发送订单' : '完成必填信息后可发送订单'}
        >
          {submitted
            ? <CheckCircle2 size={16} aria-hidden="true" />
            : <Send size={16} aria-hidden="true" />}
          {submitted ? '已发送' : canSend ? '发送订单' : '完成后发送'}
        </button>
      )}

      {role === 'admin' && (
        <Link to="/admin">
          <LayoutDashboard size={16} aria-hidden="true" />
          管理后台
        </Link>
      )}
    </nav>
  )
}
