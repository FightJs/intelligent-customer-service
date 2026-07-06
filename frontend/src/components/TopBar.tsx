import { useFormState } from '../state/FormContext'
import { SECTIONS } from '../data/sections'
import { filledCount } from '../utils/summary'

export default function TopBar({ onReset }: { onReset: () => void }) {
  const { state } = useFormState()
  let filled = 0, total = 0
  for (const def of SECTIONS) {
    const r = filledCount(state.sections[def.id], def)
    filled += r.filled
    total += r.total
  }
  const pct = total === 0 ? 0 : Math.round((filled / total) * 100)

  return (
    <div className="h-14 border-b border-idle flex items-center justify-between px-5 bg-surface">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center text-white text-sm font-bold">直</div>
        <span className="text-primary text-sm font-semibold">直播间视觉向量化智能客服</span>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <svg width="32" height="32" viewBox="0 0 36 36" className="-rotate-90">
            <circle cx="18" cy="18" r="14" fill="none" stroke="#475569" strokeWidth="3" />
            <circle
              cx="18" cy="18" r="14" fill="none" stroke="#34d399" strokeWidth="3"
              strokeDasharray={`${(pct / 100) * 88} 88`} strokeLinecap="round"
            />
          </svg>
          <span className="text-secondary text-xs">{filled}/{total} 已采集</span>
        </div>
        <button
          type="button"
          onClick={onReset}
          className="text-muted text-xs hover:text-secondary"
        >
          重新开始
        </button>
      </div>
    </div>
  )
}
