import { useState, type FormEvent } from 'react'
import { X } from 'lucide-react'
import type { AdminUser, AdminUserCreate } from '../../api/client'

interface UserFormModalProps {
  onClose: () => void
  onSubmit: (values: AdminUserCreate) => Promise<void>
}

const ROLE_LABELS: Record<AdminUser['role'], string> = {
  admin: '管理员',
  user: '普通用户',
}

export default function UserFormModal({ onClose, onSubmit }: UserFormModalProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<AdminUser['role']>('user')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const normalizedUsername = username.trim()

    if (normalizedUsername.length < 2) {
      setError('用户名至少需要 2 个字符')
      return
    }
    if (password.length < 6) {
      setError('密码至少需要 6 个字符')
      return
    }

    const values: AdminUserCreate = { username: normalizedUsername, password, role }

    setSubmitting(true)
    setError('')
    try {
      await onSubmit(values)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[60] grid place-items-center bg-black/65 p-4" role="presentation" onClick={onClose}>
      <form className="w-full max-w-md rounded-card border border-idle/60 bg-surface p-5 shadow-2xl" onSubmit={submit} onClick={(event) => event.stopPropagation()}>
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-base font-semibold text-primary">新增用户</h2>
          <button type="button" onClick={onClose} className="rounded-card p-1.5 text-muted hover:bg-active-surface hover:text-primary" aria-label="关闭表单">
            <X size={17} />
          </button>
        </div>
        <div className="space-y-4">
          <label className="block text-xs text-secondary">
            用户名
            <input value={username} onChange={(event) => setUsername(event.target.value)} className="mt-1.5 w-full rounded-card bg-base px-3 py-2.5 text-sm text-primary outline-none ring-1 ring-idle focus:ring-accent" autoFocus />
          </label>
          <label className="block text-xs text-secondary">
            初始密码
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1.5 w-full rounded-card bg-base px-3 py-2.5 text-sm text-primary outline-none ring-1 ring-idle focus:ring-accent" />
          </label>
          <label className="block text-xs text-secondary">
            角色
            <select value={role} onChange={(event) => setRole(event.target.value as AdminUser['role'])} className="mt-1.5 w-full rounded-card bg-base px-3 py-2.5 text-sm text-primary outline-none ring-1 ring-idle focus:ring-accent">
              {(Object.keys(ROLE_LABELS) as AdminUser['role'][]).map((item) => <option key={item} value={item}>{ROLE_LABELS[item]}</option>)}
            </select>
          </label>
        </div>
        {error && <p className="mt-3 text-xs text-danger">{error}</p>}
        <div className="mt-6 flex justify-end gap-2">
          <button type="button" onClick={onClose} disabled={submitting} className="rounded-card px-3 py-2 text-sm text-secondary hover:bg-active-surface disabled:opacity-50">取消</button>
          <button type="submit" disabled={submitting} className="rounded-card bg-accent px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-strong disabled:opacity-50">{submitting ? '保存中…' : '创建用户'}</button>
        </div>
      </form>
    </div>
  )
}
