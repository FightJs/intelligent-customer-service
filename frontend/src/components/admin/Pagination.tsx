import { ChevronLeft, ChevronRight } from 'lucide-react'

interface PaginationProps {
  page: number
  size: number
  total: number
  onPageChange: (page: number) => void
}

/** 分页器：上一页/下一页 + 页码 + 区间统计。 */
export default function Pagination({ page, size, total, onPageChange }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / size))
  const from = total === 0 ? 0 : (page - 1) * size + 1
  const to = Math.min(page * size, total)

  return (
    <div className="flex items-center justify-between gap-3 pt-3 text-xs text-muted">
      <span>
        共 {total} 条，{from}-{to}
      </span>
      <div className="flex items-center gap-1">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="rounded p-1 text-secondary hover:bg-active-surface disabled:cursor-not-allowed disabled:opacity-30"
          aria-label="上一页"
        >
          <ChevronLeft size={16} />
        </button>
        <span className="px-2 text-secondary">
          {page} / {totalPages}
        </span>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          className="rounded p-1 text-secondary hover:bg-active-surface disabled:cursor-not-allowed disabled:opacity-30"
          aria-label="下一页"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}
