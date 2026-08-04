import type { ReactNode } from 'react'

interface StatCardProps {
  label: string
  value: ReactNode
  icon?: ReactNode
}

/** 数据统计小卡片。复用交付物概要卡的范式。 */
export default function StatCard({ label, value, icon }: StatCardProps) {
  return (
    <div className="flex items-center gap-3 rounded-card border border-idle/50 bg-surface px-3.5 py-2.5">
      {icon && <div className="text-accent">{icon}</div>}
      <div>
        <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
        <div className="text-sm font-semibold text-primary">{value}</div>
      </div>
    </div>
  )
}
