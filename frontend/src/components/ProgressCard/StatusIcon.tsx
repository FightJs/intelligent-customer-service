import type { JSX } from 'react'
import type { SectionStatus } from '../../types/schema'

interface Props {
  status: SectionStatus
  size?: number
}

const PATHS: Record<SectionStatus, { wrap?: string; body: JSX.Element; color: string }> = {
  pending: {
    body: <circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" strokeWidth="1.5" />,
    color: 'text-idle',
  },
  active: {
    body: (
      <>
        {/* 底环:静止,极淡 */}
        <circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" strokeWidth="1.25" opacity="0.25" />
        {/* 细弧:缓慢绕环旋转,不做明暗变化 */}
        <circle
          className="status-active-arc"
          cx="7"
          cy="7"
          r="5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.25"
          strokeLinecap="round"
          strokeDasharray="8 23.4"
        />
      </>
    ),
    color: 'text-accent',
  },
  complete: {
    body: (
      <>
        <circle cx="7" cy="7" r="5" fill="currentColor" opacity="0.18" />
        <path d="M4.5 7.2 L6.2 8.8 L9.5 5.2" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </>
    ),
    color: 'text-done',
  },
  skipped: {
    wrap: 'opacity-50',
    body: (
      <>
        <circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <path d="M4.5 7 H9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </>
    ),
    color: 'text-idle',
  },
}

export default function StatusIcon({ status, size = 14 }: Props) {
  const cfg = PATHS[status]
  return (
    <span
      data-status={status}
      className={`inline-flex items-center justify-center ${cfg.color} ${cfg.wrap ?? ''}`}
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} viewBox="0 0 14 14" fill="none" data-status={status}>
        {cfg.body}
      </svg>
    </span>
  )
}
