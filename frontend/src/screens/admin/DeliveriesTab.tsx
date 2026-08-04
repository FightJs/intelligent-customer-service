import { useEffect, useState } from 'react'
import { Package, Filter } from 'lucide-react'
import {
  adminListDeliveries,
  adminListUsers,
  adminGetDelivery,
  type AdminDeliveryListItem,
  type AdminUser,
  type AdminDeliveryDetail,
} from '../../api/client'
import { useAdminList } from '../../hooks/useAdminList'
import DataTable, { type Column } from '../../components/admin/DataTable'
import Pagination from '../../components/admin/Pagination'
import SearchInput from '../../components/admin/SearchInput'
import StatCard from '../../components/admin/StatCard'
import EmptyState from '../../components/admin/EmptyState'
import DeliveryDrawer from '../../components/admin/DeliveryDrawer'

const COLUMNS: Column<AdminDeliveryListItem>[] = [
  {
    key: 'customer_name',
    header: '客户名',
    sortable: true,
    render: (d) => d.customer_name || <span className="text-muted">（未命名）</span>,
  },
  {
    key: 'owner_username',
    header: '所属用户',
    // owner_username 非排序白名单字段，但用 key 作显示；排序仍走后端白名单
  },
  {
    key: 'created_at',
    header: '生成时间',
    sortable: true,
    render: (d) => <span className="text-muted">{new Date(d.created_at).toLocaleString('zh-CN')}</span>,
  },
]

export default function DeliveriesTab() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [filterUserId, setFilterUserId] = useState<number | ''>('')

  const [previewDetail, setPreviewDetail] = useState<AdminDeliveryDetail | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState('')

  const list = useAdminList<AdminDeliveryListItem>({
    fetcher: (params) =>
      adminListDeliveries({ ...params, user_id: filterUserId || undefined }),
    initialSort: { sort_by: 'id', order: 'desc' },
    initialSize: 10,
  })

  // 单独拉用户列表填充筛选下拉，失败不影响交付物（修复原 Promise.all 一败俱败）
  useEffect(() => {
    adminListUsers({ size: 1000 })
      .then((d) => setUsers(d.items))
      .catch(() => setUsers([]))
  }, [])

  async function openPreview(row: AdminDeliveryListItem) {
    setPreviewLoading(true)
    setPreviewError('')
    setPreviewDetail(null)
    try {
      setPreviewDetail(await adminGetDelivery(row.id))
    } catch (e) {
      setPreviewError(e instanceof Error ? e.message : String(e))
    } finally {
      setPreviewLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* 统计卡 + 筛选条 */}
      <div className="flex flex-wrap items-center gap-3">
        <StatCard
          label="交付物总数"
          value={list.data?.total ?? '—'}
          icon={<Package size={16} />}
        />
        <div className="flex flex-1 flex-wrap items-center gap-2">
          <SearchInput
            value={list.search}
            onChange={list.onSearch}
            placeholder="搜索客户名或用户名…"
          />
          <div className="inline-flex items-center gap-1.5 rounded-card bg-surface px-2.5 py-2 ring-1 ring-idle">
            <Filter size={14} className="text-muted" />
            <select
              value={filterUserId}
              onChange={(e) => {
                setFilterUserId(e.target.value ? Number(e.target.value) : '')
                list.onPageChange(1)
              }}
              className="bg-surface text-sm text-secondary outline-none"
            >
              <option value="">全部用户</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.username}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {list.error && <p className="text-sm text-red-400">{list.error}</p>}

      <DataTable<AdminDeliveryListItem>
        columns={COLUMNS}
        rows={list.data?.items ?? []}
        rowKey={(d) => d.id}
        sort={list.sort}
        onSortChange={list.onSortChange}
        loading={list.loading}
        onRowClick={openPreview}
        empty={<EmptyState title="暂无交付物" description="生成后将在此显示" />}
      />

      {list.data && list.data.total > 0 && (
        <Pagination
          page={list.page}
          size={list.size}
          total={list.data.total}
          onPageChange={list.onPageChange}
        />
      )}

      {(previewDetail || previewLoading || previewError) && (
        <DeliveryDrawer
          detail={previewDetail}
          loading={previewLoading}
          error={previewError}
          onClose={() => {
            setPreviewDetail(null)
            setPreviewError('')
          }}
        />
      )}
    </div>
  )
}
