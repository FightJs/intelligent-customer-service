import { Link } from 'react-router-dom'
import { LayoutDashboard } from 'lucide-react'

/**
 * 管理后台入口：固定在视窗左下角，仅 admin 角色渲染（由父级判断）。
 * 使用图标加文字入口，悬浮时分别提升图标和文字的感知强度。
 */
export default function AdminEntryButton() {
  return (
    <Link
      to="/admin"
      className="admin-entry-button fixed bottom-4 left-4 z-40"
      data-icon-feedback="scale-brightness"
      aria-label="后台管理"
      title="后台管理"
    >
      <LayoutDashboard size={18} aria-hidden="true" />
      <span className="admin-entry-label">后台管理</span>
    </Link>
  )
}
