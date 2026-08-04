import { Users as UsersIcon } from 'lucide-react'
import { adminListUsers, type AdminUser } from '../../api/client'
import { useAdminList } from '../../hooks/useAdminList'
import DataTable, { type Column } from '../../components/admin/DataTable'
import Pagination from '../../components/admin/Pagination'
import SearchInput from '../../components/admin/SearchInput'
import StatCard from '../../components/admin/StatCard'
import Badge from '../../components/admin/Badge'
import EmptyState from '../../components/admin/EmptyState'

const COLUMNS: Column<AdminUser>[] = [
  {
    key: 'id',
    header: 'ID',
    sortable: true,
    className: 'w-16 text-muted',
  },
  { key: 'username', header: '用户名', sortable: true },
  {
    key: 'role',
    header: '角色',
    render: (u) =>
      u.role === 'admin' ? (
        <Badge variant="accent">admin</Badge>
      ) : (
        <Badge variant="secondary">user</Badge>
      ),
  },
  {
    key: 'created_at',
    header: '注册时间',
    sortable: true,
    render: (u) => <span className="text-muted">{new Date(u.created_at).toLocaleString('zh-CN')}</span>,
  },
]

export default function UsersTab() {
  const list = useAdminList<AdminUser>({
    fetcher: adminListUsers,
    initialSort: { sort_by: 'id', order: 'asc' },
    initialSize: 20,
  })

  const adminCount = list.data?.items.filter((u) => u.role === 'admin').length ?? 0

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <StatCard label="用户总数" value={list.data?.total ?? '—'} icon={<UsersIcon size={16} />} />
        <StatCard label="管理员" value={adminCount} />
        <div className="flex-1" />
        <div className="min-w-[240px]">
          <SearchInput value={list.search} onChange={list.onSearch} placeholder="搜索用户名…" />
        </div>
      </div>

      {list.error && <p className="text-sm text-red-400">{list.error}</p>}

      <DataTable<AdminUser>
        columns={COLUMNS}
        rows={list.data?.items ?? []}
        rowKey={(u) => u.id}
        sort={list.sort}
        onSortChange={list.onSortChange}
        loading={list.loading}
        empty={<EmptyState title="暂无用户" />}
      />

      {list.data && list.data.total > 0 && (
        <Pagination
          page={list.page}
          size={list.size}
          total={list.data.total}
          onPageChange={list.onPageChange}
        />
      )}
    </div>
  )
}
