import { useState } from 'react'
import { MoreHorizontal, Plus, Search, ShieldCheck, UserRound } from 'lucide-react'
import {
  adminCreateUser,
  adminDeleteUser,
  adminGetUser,
  adminListUsers,
  adminUpdateUser,
  type AdminUser,
  type AdminUserCreate,
  type AdminUserDetail,
  type AdminUsersPage,
  type AdminUserUpdate,
} from '../../api/client'
import { useAdminList } from '../../hooks/useAdminList'
import Badge from '../../components/admin/Badge'
import EmptyState from '../../components/admin/EmptyState'
import Pagination from '../../components/admin/Pagination'
import StatCard from '../../components/admin/StatCard'
import UserDetailDrawer from '../../components/admin/UserDetailDrawer'
import UserFormModal from '../../components/admin/UserFormModal'

interface UsersTabProps {
  onViewDeliveries: (userId: number) => void
}

export default function UsersTab({ onViewDeliveries }: UsersTabProps) {
  const list = useAdminList<AdminUser, AdminUsersPage>({
    fetcher: adminListUsers,
    initialSort: { sort_by: 'id', order: 'asc' },
    initialSize: 20,
  })
  const [selectedUser, setSelectedUser] = useState<AdminUserDetail | null>(null)
  const [resetPasswordOnOpen, setResetPasswordOnOpen] = useState(false)
  const [editUserOnOpen, setEditUserOnOpen] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [createFormOpen, setCreateFormOpen] = useState(false)
  const [menuId, setMenuId] = useState<number | null>(null)
  const [toast, setToast] = useState('')

  const users = list.data?.items ?? []
  const adminCount = list.data?.admin_count ?? users.filter((user) => user.role === 'admin').length

  function notify(message: string) {
    setToast(message)
    window.setTimeout(() => setToast(''), 2600)
  }

  async function openDetail(user: AdminUser, options: { startResetPassword?: boolean; startEditing?: boolean } = {}) {
    setMenuId(null)
    setSelectedUser(null)
    setResetPasswordOnOpen(options.startResetPassword ?? false)
    setEditUserOnOpen(options.startEditing ?? false)
    setDetailError('')
    setDetailLoading(true)
    try {
      setSelectedUser(await adminGetUser(user.id))
    } catch (cause) {
      setDetailError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setDetailLoading(false)
    }
  }

  function openCreateForm() {
    setCreateFormOpen(true)
    setMenuId(null)
  }

  async function submitUser(values: AdminUserCreate) {
    const result = await adminCreateUser(values)
    notify(`已创建用户 ${result.username}`)
    setCreateFormOpen(false)
    list.refresh()
  }

  async function deleteUser(user: AdminUser) {
    setMenuId(null)
    if (!window.confirm(`确认删除用户 ${user.username}？关联会话和交付物也会被删除。`)) return
    try {
      await adminDeleteUser(user.id)
      if (selectedUser?.id === user.id) setSelectedUser(null)
      notify(`已删除 ${user.username}`)
      list.refresh()
    } catch (cause) {
      notify(cause instanceof Error ? cause.message : String(cause))
    }
  }

  async function resetPassword(password: string) {
    if (!selectedUser) return
    const result = await adminUpdateUser(selectedUser.id, { password })
    setSelectedUser(result)
    notify(`已重置 ${result.username} 的密码`)
    list.refresh()
  }

  async function updateSelectedUser(changes: AdminUserUpdate) {
    if (!selectedUser) return
    const result = await adminUpdateUser(selectedUser.id, changes)
    setSelectedUser(result)
    notify(`已更新 ${result.username}`)
    list.refresh()
  }

  return (
    <div className="relative space-y-4" onClick={() => menuId !== null && setMenuId(null)}>
      <div className="flex flex-wrap items-center gap-3">
        <StatCard label="用户总数" value={list.data?.total ?? '—'} icon={<UserRound size={16} />} />
        <StatCard label="管理员" value={list.data ? adminCount : '—'} icon={<ShieldCheck size={16} />} />
        <StatCard label="当前页" value={list.data ? users.length : '—'} />
        <button type="button" onClick={openCreateForm} className="ml-auto inline-flex items-center gap-1.5 rounded-card bg-accent px-3 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-strong">
          <Plus size={15} /> 新增用户
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <label className="relative min-w-[240px] flex-1">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input value={list.search} onChange={(event) => list.onSearch(event.target.value)} placeholder="搜索用户名…" className="w-full rounded-card bg-surface py-2.5 pl-9 pr-3 text-sm text-primary placeholder:text-muted outline-none ring-1 ring-idle focus:ring-accent" />
        </label>
      </div>

      {list.error && <p className="text-sm text-danger">{list.error}</p>}
      {detailError && <p className="text-sm text-danger">{detailError}</p>}

      <div className="overflow-x-auto rounded-card border border-idle/40">
        <table className="w-full min-w-[680px] text-sm">
          <thead><tr className="bg-active-surface/40 text-left text-xs text-secondary"><th className="px-4 py-3 font-medium">用户</th><th className="px-4 py-3 font-medium">角色</th><th className="px-4 py-3 font-medium">注册时间</th><th className="w-14 px-4 py-3" /></tr></thead>
          <tbody>
            {list.loading && users.length === 0 && <tr><td colSpan={4} className="px-4 py-10 text-center text-sm text-muted">加载中…</td></tr>}
            {users.map((user) => (
              <tr key={user.id} className="border-t border-idle/30 transition-colors hover:bg-active-surface/30">
                <td className="px-4 py-3"><button type="button" onClick={() => void openDetail(user)} className="flex items-center gap-3 text-left"><span className={`grid h-8 w-8 place-items-center rounded-full text-xs font-semibold ${user.role === 'admin' ? 'bg-accent text-white' : 'bg-idle text-secondary'}`}>{user.username[0].toUpperCase()}</span><span><span className="block font-medium text-primary">{user.username}</span><span className="block text-xs text-muted">U-{user.id}</span></span></button></td>
                <td className="px-4 py-3"><Badge variant={user.role === 'admin' ? 'accent' : 'secondary'}>{user.role === 'admin' ? '管理员' : '普通用户'}</Badge></td>
                <td className="px-4 py-3 text-xs text-muted">{new Date(user.created_at).toLocaleString('zh-CN')}</td>
                <td className="relative px-4 py-3"><button type="button" onClick={(event) => { event.stopPropagation(); setMenuId(menuId === user.id ? null : user.id) }} className="rounded-card p-1.5 text-muted hover:bg-active-surface hover:text-primary" aria-label={`${user.username} 更多操作`}><MoreHorizontal size={17} /></button>{menuId === user.id && <UserActionMenu onDetail={() => void openDetail(user)} onViewDeliveries={() => onViewDeliveries(user.id)} onEdit={() => void openDetail(user, { startEditing: true })} onReset={() => void openDetail(user, { startResetPassword: true })} onDelete={() => void deleteUser(user)} />}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!list.loading && users.length === 0 && <div className="border-t border-idle/30 py-12"><EmptyState title="暂无用户" description="调整搜索条件或创建新用户" /></div>}
      </div>

      {list.data && list.data.total > 0 && <Pagination page={list.page} size={list.size} total={list.data.total} onPageChange={list.onPageChange} />}

      {detailLoading && <div className="fixed inset-0 z-40 grid place-items-center bg-black/30 text-sm text-primary">加载用户详情…</div>}
      {selectedUser && <UserDetailDrawer user={selectedUser} isLastAdmin={selectedUser.role === 'admin' && adminCount === 1} startResetPassword={resetPasswordOnOpen} startEditing={editUserOnOpen} onClose={() => { setSelectedUser(null); setResetPasswordOnOpen(false); setEditUserOnOpen(false) }} onUpdateUser={updateSelectedUser} onResetPassword={resetPassword} onViewDeliveries={() => onViewDeliveries(selectedUser.id)} />}
      {createFormOpen && <UserFormModal onClose={() => setCreateFormOpen(false)} onSubmit={submitUser} />}
      {toast && <div role="status" className="fixed bottom-5 left-1/2 z-[70] -translate-x-1/2 rounded-card border border-done/40 bg-done px-4 py-2.5 text-sm text-white shadow-lg">{toast}</div>}
    </div>
  )
}

function UserActionMenu({ onDetail, onViewDeliveries, onEdit, onReset, onDelete }: { onDetail: () => void; onViewDeliveries: () => void; onEdit: () => void; onReset: () => void; onDelete: () => void }) {
  return <div className="absolute right-3 top-11 z-20 w-44 overflow-hidden rounded-card border border-idle/70 bg-active-surface shadow-xl" onClick={(event) => event.stopPropagation()}><MenuItem label="查看详情" onClick={onDetail} /><MenuItem label="查看交付物" onClick={onViewDeliveries} /><MenuItem label="编辑用户" onClick={onEdit} /><MenuItem label="重置密码" onClick={onReset} /><MenuItem label="删除用户" onClick={onDelete} danger /></div>
}

function MenuItem({ label, onClick, danger }: { label: string; onClick: () => void; danger?: boolean }) {
  return <button type="button" onClick={onClick} className={`block w-full border-b border-idle/50 px-3 py-2.5 text-left text-xs last:border-b-0 hover:bg-active-surface ${danger ? 'text-danger hover:text-danger' : 'text-secondary hover:text-primary'}`}>{label}</button>
}
