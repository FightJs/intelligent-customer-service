import type { ReactNode } from 'react'
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'

export interface Column<T> {
  /** 唯一 key，也作排序字段名（若 sortable） */
  key: string
  header: string
  /** 单元格渲染；默认取 row[key] */
  render?: (row: T) => ReactNode
  /** 该列是否可排序 */
  sortable?: boolean
  /** 单元格 className */
  className?: string
}

export interface SortState {
  sort_by: string
  order: 'asc' | 'desc'
}

interface DataTableProps<T> {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string | number
  sort?: SortState
  onSortChange?: (s: SortState) => void
  loading?: boolean
  skeletonRows?: number
  empty?: ReactNode
  /** 行点击（交付物预览等） */
  onRowClick?: (row: T) => void
}

/** 列定义驱动的通用表格：表头排序 + 骨架 + 空态。 */
export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  sort,
  onSortChange,
  loading,
  skeletonRows = 5,
  empty,
  onRowClick,
}: DataTableProps<T>) {
  function handleSort(col: Column<T>) {
    if (!col.sortable || !onSortChange || !sort) return
    // 同列：翻转方向；换列：默认 desc
    const order: 'asc' | 'desc' =
      sort.sort_by === col.key && sort.order === 'desc' ? 'asc' : 'desc'
    onSortChange({ sort_by: col.key, order })
  }

  return (
    <div className="overflow-hidden rounded-card border border-idle/40">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-active-surface/40 text-left text-secondary">
            {columns.map((col) => {
              const active = sort?.sort_by === col.key
              return (
                <th
                  key={col.key}
                  className={`px-3.5 py-2.5 first:pl-7 font-medium ${col.sortable ? 'cursor-pointer select-none hover:text-primary' : ''} ${col.className ?? ''}`}
                  onClick={() => handleSort(col)}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.header}
                    {col.sortable && (
                      <span className="text-muted">
                        {active && sort?.order === 'desc' ? (
                          <ArrowDown size={13} className="text-accent" />
                        ) : active && sort?.order === 'asc' ? (
                          <ArrowUp size={13} className="text-accent" />
                        ) : (
                          <ArrowUpDown size={13} />
                        )}
                      </span>
                    )}
                  </span>
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {loading && rows.length === 0 ? (
            Array.from({ length: skeletonRows }).map((_, i) => (
              <tr key={`sk-${i}`} className="border-t border-idle/30">
                {columns.map((col) => (
                  <td key={col.key} className="px-3.5 py-2.5 first:pl-7">
                    <div className="h-4 w-3/4 animate-pulse rounded bg-idle/30" />
                  </td>
                ))}
              </tr>
            ))
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-3.5 py-10 text-center">
                {empty ?? <span className="text-sm text-muted">暂无数据</span>}
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr
                key={rowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={`border-t border-idle/30 transition-colors ${onRowClick ? 'cursor-pointer hover:bg-active-surface/30' : ''}`}
              >
                {columns.map((col) => (
                  <td key={col.key} className={`px-3.5 py-2.5 first:pl-7 text-primary ${col.className ?? ''}`}>
                    {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? '')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
