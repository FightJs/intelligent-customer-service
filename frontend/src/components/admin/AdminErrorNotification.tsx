import { createPortal } from 'react-dom'
import { CircleAlert, X } from 'lucide-react'

interface AdminErrorNotificationProps {
  visible: boolean
  onDismiss: () => void
}

export default function AdminErrorNotification({ visible, onDismiss }: AdminErrorNotificationProps) {
  if (!visible) return null

  return createPortal(
    <div role="alert" className="admin-error-notification">
      <CircleAlert className="admin-error-notification__icon" size={20} aria-hidden="true" />
      <span className="admin-error-notification__title">暂不支持该类文档</span>
      <button
        type="button"
        onClick={onDismiss}
        className="admin-error-notification__close"
        aria-label="关闭提示"
      >
        <X size={20} aria-hidden="true" />
      </button>
    </div>,
    document.body,
  )
}
