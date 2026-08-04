import { Link } from 'react-router-dom'
import { LayoutDashboard } from 'lucide-react'

/**
 * 管理后台入口：固定在视窗左下角，仅 admin 角色渲染（由父级判断）。
 * fixed 定位脱离工作台布局，hover 高亮。
 */
export default function AdminEntryButton() {
  return (
    <Link
      to="/admin"
      className="fixed bottom-4 left-4 z-40 inline-flex items-center gap-1.5 rounded-card border border-idle/50 bg-surface/90 px-3 py-2 text-xs text-secondary shadow-lg backdrop-blur-sm transition-colors hover:border-done/60 hover:text-primary"
    >
      <LayoutDashboard size={14} />
      管理后台
    </Link>
  )
}
