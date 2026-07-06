interface Props {
  pct: number
  size?: number
}

export default function ProgressRing({ pct, size = 18 }: Props) {
  const r = 14
  const circ = 2 * Math.PI * r
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" className="-rotate-90">
      <circle cx="18" cy="18" r={r} fill="none" stroke="rgb(var(--color-idle))" strokeWidth="3" />
      <circle
        cx="18" cy="18" r={r} fill="none" stroke="rgb(var(--color-done))" strokeWidth="3"
        strokeDasharray={`${(pct / 100) * circ} ${circ}`} strokeLinecap="round"
      />
    </svg>
  )
}
