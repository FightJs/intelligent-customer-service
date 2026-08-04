import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminListUsers, adminListDeliveries, adminGetDelivery, type AdminUser, type AdminDeliveryListItem, type AdminDeliveryDetail } from '../api/client'

export default function AdminScreen() {
  const [tab, setTab] = useState<'users' | 'deliveries'>('deliveries')
  const [users, setUsers] = useState<AdminUser[]>([])
  const [deliveries, setDeliveries] = useState<AdminDeliveryListItem[]>([])
  const [filterUserId, setFilterUserId] = useState<number | ''>('')
  const [preview, setPreview] = useState<AdminDeliveryDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    setLoading(true)
    setErr('')
    Promise.all([adminListUsers(), adminListDeliveries(filterUserId || undefined)])
      .then(([u, d]) => { setUsers(u); setDeliveries(d) })
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false))
  }, [filterUserId])

  async function openPreview(id: number) {
    try {
      setPreview(await adminGetDelivery(id))
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <div className="h-full flex flex-col bg-base text-primary">
      <header className="h-12 flex items-center px-5 gap-4 border-b border-idle">
        <span className="font-semibold">管理后台</span>
        <nav className="flex gap-2 ml-4">
          <button
            type="button"
            onClick={() => setTab('deliveries')}
            className={`px-3 py-1 rounded text-sm ${tab === 'deliveries' ? 'bg-active-surface text-primary' : 'text-secondary hover:text-primary'}`}
          >
            交付物
          </button>
          <button
            type="button"
            onClick={() => setTab('users')}
            className={`px-3 py-1 rounded text-sm ${tab === 'users' ? 'bg-active-surface text-primary' : 'text-secondary hover:text-primary'}`}
          >
            用户
          </button>
        </nav>
        <div className="flex-1" />
        <Link to="/" className="text-sm text-secondary hover:text-primary">← 返回工作台</Link>
      </header>

      <main className="flex-1 overflow-auto p-5">
        {err && <p className="text-sm text-red-400 mb-3">{err}</p>}
        {loading && <p className="text-sm text-muted">加载中…</p>}

        {tab === 'deliveries' && !loading && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-secondary">按用户筛选：</span>
              <select
                value={filterUserId}
                onChange={(e) => setFilterUserId(e.target.value ? Number(e.target.value) : '')}
                className="rounded bg-surface px-2 py-1 ring-1 ring-idle text-sm"
              >
                <option value="">全部</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.username}</option>
                ))}
              </select>
              <span className="text-muted">共 {deliveries.length} 条</span>
            </div>

            {deliveries.length === 0 ? (
              <p className="text-muted text-sm">暂无交付物</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-secondary text-left border-b border-idle">
                    <th className="py-2 pr-3">客户名</th>
                    <th className="py-2 pr-3">所属用户</th>
                    <th className="py-2 pr-3">生成时间</th>
                    <th className="py-2 pr-3">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {deliveries.map((d) => (
                    <tr key={d.id} className="border-b border-idle/50">
                      <td className="py-2 pr-3">{d.customer_name || '（未命名）'}</td>
                      <td className="py-2 pr-3">{d.owner_username}</td>
                      <td className="py-2 pr-3 text-muted">{new Date(d.created_at).toLocaleString('zh-CN')}</td>
                      <td className="py-2 pr-3">
                        <button
                          type="button"
                          onClick={() => openPreview(d.id)}
                          className="text-accent hover:underline"
                        >
                          预览
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {tab === 'users' && !loading && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-secondary text-left border-b border-idle">
                <th className="py-2 pr-3">ID</th>
                <th className="py-2 pr-3">用户名</th>
                <th className="py-2 pr-3">角色</th>
                <th className="py-2 pr-3">注册时间</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-idle/50">
                  <td className="py-2 pr-3 text-muted">{u.id}</td>
                  <td className="py-2 pr-3">{u.username}</td>
                  <td className="py-2 pr-3">
                    <span className={u.role === 'admin' ? 'text-accent' : 'text-secondary'}>
                      {u.role}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-muted">{new Date(u.created_at).toLocaleString('zh-CN')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </main>

      {preview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-6" onClick={() => setPreview(null)}>
          <div
            className="bg-surface rounded-card max-w-2xl w-full max-h-[80vh] overflow-auto p-6 ring-1 ring-idle"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold">{preview.customer_name || '交付物预览'}</h2>
              <button type="button" onClick={() => setPreview(null)} className="text-muted hover:text-primary">✕</button>
            </div>
            <pre className="text-xs whitespace-pre-wrap text-secondary font-mono">{preview.markdown}</pre>
          </div>
        </div>
      )}
    </div>
  )
}
