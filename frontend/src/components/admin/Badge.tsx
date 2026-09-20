import type { ReactNode } from 'react'

type Variant = 'accent' | 'secondary' | 'done' | 'muted' | 'warning' | 'danger'

const VARIANT_CLASS: Record<Variant, string> = {
  accent: 'bg-accent/15 text-accent',
  secondary: 'bg-active-surface text-secondary',
  done: 'bg-done/15 text-done',
  muted: 'bg-idle/20 text-muted',
  warning: 'bg-warning/15 text-warning',
  danger: 'bg-danger/10 text-danger',
}

interface BadgeProps {
  variant?: Variant
  children: ReactNode
  className?: string
}

/** 状态/角色标签，药丸样式。复用 rounded-pill + 语义色透明背景。 */
export default function Badge({ variant = 'secondary', children, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-pill px-2 py-0.5 text-[11px] font-medium ${VARIANT_CLASS[variant]} ${className}`}
    >
      {children}
    </span>
  )
}
