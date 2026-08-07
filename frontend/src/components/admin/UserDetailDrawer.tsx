import { useEffect, useState, type ReactNode } from 'react'
import { KeyRound, Package, UserRound, X } from 'lucide-react'
import type { AdminUser, AdminUserDetail, AdminUserUpdate } from '../../api/client'
import Badge from './Badge'

interface UserDetailDrawerProps {
  user: AdminUserDetail
  isLastAdmin?: boolean
  startResetPassword?: boolean
  startEditing?: boolean
  onClose: () => void
  onUpdateUser: (changes: AdminUserUpdate) => Promise<void>
  onResetPassword: (password: string) => Promise<void>
  onViewDeliveries: () => void
}

export default function UserDetailDrawer({ user, isLastAdmin = false, startResetPassword = false, startEditing = false, onClose, onUpdateUser, onResetPassword, onViewDeliveries }: UserDetailDrawerProps) {
  const [editingProfile, setEditingProfile] = useState(startEditing)
  const [draftUsername, setDraftUsername] = useState(user.username)
  const [draftRole, setDraftRole] = useState<AdminUser['role']>(user.role)
  const [profileError, setProfileError] = useState('')
  const [savingProfile, setSavingProfile] = useState(false)
  const [resettingPassword, setResettingPassword] = useState(startResetPassword)
  const [password, setPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [savingPassword, setSavingPassword] = useState(false)

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose])

  useEffect(() => {
    setEditingProfile(startEditing)
    setDraftUsername(user.username)
    setDraftRole(user.role)
    setProfileError('')
    setResettingPassword(startResetPassword)
    setPassword('')
    setPasswordError('')
  }, [user.id, user.username, user.role, startEditing, startResetPassword])

  function beginProfileEdit() {
    setEditingProfile((current) => !current)
    setDraftUsername(user.username)
    setDraftRole(user.role)
    setProfileError('')
  }

  async function saveProfile() {
    const username = draftUsername.trim()
    if (username.length < 2) {
      setProfileError('用户名至少需要 2 个字符')
      return
    }
    setSavingProfile(true)
    setProfileError('')
    try {
      await onUpdateUser({ username, role: draftRole })
      setEditingProfile(false)
    } catch (cause) {
      setProfileError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setSavingProfile(false)
    }
  }

  function beginPasswordReset() {
    setResettingPassword((current) => !current)
    setPassword('')
    setPasswordError('')
  }

  async function savePassword() {
    if (password.length < 6) {
      setPasswordError('密码至少需要 6 个字符')
      return
    }
    setSavingPassword(true)
    setPasswordError('')
    try {
      await onResetPassword(password)
      setResettingPassword(false)
      setPassword('')
    } catch (cause) {
      setPasswordError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setSavingPassword(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/55" onClick={onClose} role="presentation">
      <aside className="flex h-full w-full max-w-[492px] flex-col border-l border-idle/60 bg-surface shadow-2xl" onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true" aria-label="用户详情">
        <header className="flex items-center justify-between border-b border-idle/50 px-5 py-3">
          <h2 className="text-base font-semibold text-primary">用户详情</h2>
          <button type="button" onClick={onClose} className="rounded-card p-2 text-muted hover:bg-active-surface hover:text-primary" aria-label="关闭用户详情"><X size={18} /></button>
        </header>

        <div className="flex-1 overflow-y-auto">
          <section className="flex items-center gap-3 border-b border-idle/50 px-5 py-4">
            <div className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-accent text-lg font-semibold text-white">{user.username[0].toUpperCase()}</div>
            <div className="min-w-0 flex-1"><h3 className="truncate text-base font-semibold text-primary">{user.username}</h3><p className="text-xs text-secondary">用户 ID：{user.id}</p></div>
            <Badge variant={user.role === 'admin' ? 'accent' : 'secondary'}>{user.role === 'admin' ? '管理员' : '普通用户'}</Badge>
          </section>

          <section className="border-b border-idle/50 px-5 py-3.5">
            <h3 className="mb-3 text-sm font-medium text-primary">账号信息</h3>
            <dl className="space-y-2.5 text-sm">
              <InfoRow label="账号" value={editingProfile ? <input value={draftUsername} onChange={(event) => setDraftUsername(event.target.value)} className="w-44 rounded-card bg-base px-2.5 py-1.5 text-right text-xs text-primary outline-none ring-1 ring-idle focus:ring-accent" autoFocus /> : user.username} />
              <InfoRow label="注册时间" value={new Date(user.created_at).toLocaleString('zh-CN')} />
              <InfoRow label="账号角色" value={editingProfile ? <select value={draftRole} onChange={(event) => setDraftRole(event.target.value as AdminUser['role'])} className="w-44 rounded-card bg-base px-2.5 py-1.5 text-right text-xs text-primary outline-none ring-1 ring-idle focus:ring-accent"><option value="user">普通用户</option><option value="admin">管理员</option></select> : user.role === 'admin' ? '管理员' : '普通用户'} />
              <InfoRow label="账号密码" value={resettingPassword ? <div className="flex max-w-[250px] flex-col items-end gap-1.5"><div className="flex items-center gap-1.5"><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="输入新密码" autoFocus className="w-36 rounded-card bg-base px-2.5 py-1.5 text-right text-xs text-primary outline-none ring-1 ring-idle focus:ring-accent" /><button type="button" onClick={() => void savePassword()} disabled={savingPassword} className="rounded-card bg-accent px-2.5 py-1.5 text-xs text-white hover:bg-blue-400 disabled:opacity-50">{savingPassword ? '保存中…' : '保存'}</button><button type="button" onClick={beginPasswordReset} disabled={savingPassword} className="rounded-card px-1.5 py-1.5 text-xs text-muted hover:bg-active-surface hover:text-primary">取消</button></div>{passwordError && <span className="text-xs text-red-300">{passwordError}</span>}</div> : <span aria-label="密码已设置，不可查看" title="密码不可查看，只能重置">••••••••</span>} />
              <InfoRow label="交付物" value={`${user.delivery_count} 个`} />
            </dl>
            {editingProfile && <div className="mt-3 space-y-2"><div className="flex justify-end gap-2"><button type="button" onClick={beginProfileEdit} disabled={savingProfile} className="rounded-card px-2.5 py-1.5 text-xs text-secondary hover:bg-active-surface">取消</button><button type="button" onClick={() => void saveProfile()} disabled={savingProfile} className="rounded-card bg-accent px-2.5 py-1.5 text-xs text-white hover:bg-blue-400 disabled:opacity-50">{savingProfile ? '保存中…' : '保存修改'}</button></div>{profileError && <p className="text-right text-xs text-red-300">{profileError}</p>}</div>}
            <button type="button" onClick={onViewDeliveries} className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-card bg-accent px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"><Package size={15} /> 查看交付物</button>
          </section>

          <section className="px-5 py-3.5">
            <h3 className="mb-2.5 text-sm font-medium text-primary">账号操作</h3>
            {isLastAdmin && <p className="mb-2.5 text-xs leading-5 text-amber-200">当前用户为最后一名管理员，修改角色会由服务端拒绝。</p>}
            <div className="grid gap-2 sm:grid-cols-2"><ActionButton icon={<UserRound size={15} />} label={editingProfile ? '取消编辑' : '编辑用户'} onClick={beginProfileEdit} /><ActionButton icon={<KeyRound size={15} />} label={resettingPassword ? '取消重置' : '重置密码'} onClick={beginPasswordReset} /></div>
          </section>
        </div>
      </aside>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: ReactNode }) {
  return <div className="flex items-start justify-between gap-4"><dt className="shrink-0 text-secondary">{label}</dt><dd className="text-right text-primary">{value}</dd></div>
}

function ActionButton({ icon, label, onClick }: { icon: ReactNode; label: string; onClick: () => void }) {
  return <button type="button" onClick={onClick} className="inline-flex items-center justify-center gap-1.5 rounded-card bg-active-surface px-2.5 py-2 text-xs text-secondary transition-colors hover:bg-idle hover:text-primary">{icon}{label}</button>
}
