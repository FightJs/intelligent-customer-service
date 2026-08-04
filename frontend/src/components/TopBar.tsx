import { useState } from 'react'
import type { Theme } from '../state/theme'
import AvatarMenu from './AvatarMenu'

interface Props {
  theme: Theme
  onToggleTheme: () => void
  onReset: () => void
  onLogout: () => void
  /** 当前用户角色，用于头像环色区分；undefined 时用默认色 */
  role?: string
  progressVisible: boolean
  deliveryOpen: boolean
  onToggleProgress: () => void
  onToggleDelivery: () => void
}

export default function TopBar({
  theme, onToggleTheme, onReset, onLogout, role,
  progressVisible, deliveryOpen, onToggleProgress, onToggleDelivery,
}: Props) {
  const [menu, setMenu] = useState<{ x: number; y: number } | null>(null)

  // 头像环色：admin=done(绿)，user=accent(蓝)，未知=idle(灰)
  const ringClass = role === 'admin' ? 'ring-done' : role === 'user' ? 'ring-accent' : 'ring-idle'
  const roleLabel = role === 'admin' ? '管理员' : role === 'user' ? '普通用户' : '账户'

  function handleContextMenu(e: React.MouseEvent) {
    e.preventDefault()
    setMenu({ x: e.clientX, y: e.clientY })
  }

  return (
    <>
      <header className="top-bar h-12 flex items-center px-5 gap-3.5 bg-transparent">
        <div
          className={`w-9 h-9 rounded-full bg-base ring-1 ${ringClass} p-0.5 shrink-0 cursor-pointer hover:ring-2 transition`}
          aria-label={roleLabel}
          role="button"
          tabIndex={0}
          title={`${roleLabel}（右键打开菜单）`}
          onContextMenu={handleContextMenu}
        >
          <div className="w-full h-full rounded-full bg-active-surface flex items-center justify-center text-secondary overflow-hidden">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="8" r="4" />
              <path d="M4 20c0-4 4-6 8-6s8 2 8 6" />
            </svg>
          </div>
        </div>
        <button
          type="button"
          onClick={onToggleProgress}
          className="p-2 rounded hover:bg-active-surface text-secondary"
          aria-label={progressVisible ? '隐藏采集进度' : '显示采集进度'}
        >
          {progressVisible ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-10-8-10-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 10 8 10 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
              <line x1="1" y1="1" x2="23" y2="23" />
            </svg>
          )}
        </button>
        <div className="flex-1" />
        <div className="flex items-center gap-2.5">
          <img src="/lit-blue.svg" alt="logo" className="w-7 h-7" />
          <span className="text-secondary text-[16px] leading-6 font-medium pointer-events-none">Livestream Studio Setup Assistant</span>
        </div>
        <div className="flex-1 flex items-center justify-end gap-3.5">
          <button
            type="button"
            onClick={onToggleDelivery}
            className="p-2 rounded hover:bg-active-surface text-secondary"
            aria-label={deliveryOpen ? '收起交付物' : '展开交付物'}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {deliveryOpen ? (
                <>
                  <rect x="11" y="4" width="11" height="16" rx="2" />
                  <path d="M2 12h5M5 9l3 3-3 3" />
                </>
              ) : (
                <>
                  <rect x="11" y="4" width="11" height="16" rx="2" />
                  <path d="M2 12h9M2 9l3 3-3 3" />
                </>
              )}
            </svg>
          </button>
        </div>
      </header>
      {menu && (
        <AvatarMenu
          pos={menu}
          theme={theme}
          onToggleTheme={onToggleTheme}
          onReset={onReset}
          onLogout={onLogout}
          onClose={() => setMenu(null)}
        />
      )}
    </>
  )
}
