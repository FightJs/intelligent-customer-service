import { useCallback, useEffect, useState } from 'react'
import type { AdminListParams, Paged } from '../api/client'

interface UseAdminListArgs<T> {
  /** 取数函数（参数变化时重新调用） */
  fetcher: (params: AdminListParams) => Promise<Paged<T>>
  /** 初始排序 */
  initialSort?: { sort_by: string; order: 'asc' | 'desc' }
  /** 初始每页大小 */
  initialSize?: number
}

/**
 * admin 列表通用状态：data/loading/error + search/sort/page/size。
 * search 变化时回到第 1 页；fetcher 抛错只影响自身（不连累别的请求）。
 */
export function useAdminList<T>({
  fetcher,
  initialSort = { sort_by: 'id', order: 'desc' },
  initialSize = 10,
}: UseAdminListArgs<T>) {
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState(initialSort)
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(initialSize)

  const [data, setData] = useState<Paged<T> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const params: AdminListParams = {
    search: search || undefined,
    sort_by: sort.sort_by,
    order: sort.order,
    page,
    size,
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    fetcher(params)
      .then((d) => {
        if (!cancelled) setData(d)
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, sort.sort_by, sort.order, page, size])

  const onSearch = useCallback((v: string) => {
    setSearch(v)
    setPage(1)
  }, [])

  const onSortChange = useCallback((s: { sort_by: string; order: 'asc' | 'desc' }) => {
    setSort(s)
    setPage(1)
  }, [])

  return {
    data,
    loading,
    error,
    search,
    sort,
    page,
    size,
    onSearch,
    onSortChange,
    onPageChange: setPage,
    onSizeChange: (s: number) => {
      setSize(s)
      setPage(1)
    },
  }
}
