import { Link } from 'react-router-dom'
import { ArrowLeft, Package, Users } from 'lucide-react'

type Tab = 'deliveries' | 'users'

interface AdminHeaderProps {
  tab: Tab
  onTabChange: (t: Tab) => void
}

const TABS: { id: Tab; label: string; icon: typeof Package }[] = [
  { id: 'deliveries', label: '交付物', icon: Package },
  { id: 'users', label: '用户', icon: Users },
]

/** 后台顶栏：标题 + tab 切换 + 返回工作台。对齐 TopBar 高度(h-12)。 */
export default function AdminHeader({ tab, onTabChange }: AdminHeaderProps) {
  return (
    <header className="flex h-12 shrink-0 items-center gap-4 border-b border-idle/40 px-5">
      <span className="text-sm font-semibold text-primary">管理后台</span>
      <nav className="ml-2 flex gap-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => onTabChange(id)}
            className={`inline-flex items-center gap-1.5 rounded-card px-3 py-1.5 text-sm transition-colors ${
              tab === id
                ? 'bg-active-surface text-primary'
                : 'text-secondary hover:text-primary'
            }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </nav>
      <div className="flex-1" />
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm text-muted hover:text-secondary"
      >
        <ArrowLeft size={14} />
        返回工作台
      </Link>
    </header>
  )
}
