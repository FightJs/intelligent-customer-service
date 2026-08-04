interface SkeletonProps {
  /** 行数（表格骨架用），默认 1 */
  rows?: number
  className?: string
}

/** 行骨架。复用 Loader 的 pulse 思路：idle ↔ active-surface 脉动。 */
export default function Skeleton({ rows = 1, className = '' }: SkeletonProps) {
  return (
    <div className={`space-y-2.5 ${className}`}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-8 rounded-card bg-idle/30 animate-pulse"
        />
      ))}
    </div>
  )
}
