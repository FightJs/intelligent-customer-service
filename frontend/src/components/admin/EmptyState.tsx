import type { ReactNode } from 'react'
import { Inbox } from 'lucide-react'

interface EmptyStateProps {
  title?: string
  description?: string
  icon?: ReactNode
}

/** 统一空态。默认用 Inbox 图标。 */
export default function EmptyState({
  title = '暂无数据',
  description,
  icon,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-3 text-muted">
        {icon ?? <Inbox size={32} strokeWidth={1.5} />}
      </div>
      <p className="text-sm text-secondary">{title}</p>
      {description && <p className="mt-1 text-xs text-muted">{description}</p>}
    </div>
  )
}
