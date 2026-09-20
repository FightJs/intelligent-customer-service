import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Clapperboard, ShieldCheck } from 'lucide-react'
import type { Theme } from '../state/theme'
import AvatarMenu from './AvatarMenu'

interface Props {
  theme: Theme
  onToggleTheme: () => void
  onReset: () => void
  onLogout: () => void
  /** 当前用户角色，用于头像环色区分；undefined 时用默认色 */
  role?: string
  onRestoreCenterCard: () => void
}

export default function TopBar({
  theme, onToggleTheme, onReset, onLogout, role,
  onRestoreCenterCard,
}: Props) {
  const [menu, setMenu] = useState<{ x: number; y: number } | null>(null)
  const avatarRef = useRef<HTMLButtonElement>(null)

  // 管理员以盾牌角标区分；普通用户与未知账户继续使用状态环。
  const avatarClass = role === 'admin'
    ? 'border border-idle/80 hover:border-secondary'
    : `ring-1 ${role === 'user' ? 'ring-accent' : 'ring-idle'} hover:ring-2`
  const roleLabel = role === 'admin'
    ? '管理员'
    : role === 'user'
      ? '普通用户'
      : role === 'guest'
        ? '游客'
        : '账户'

  function toggleMenu() {
    if (menu) {
      setMenu(null)
      return
    }

    const rect = avatarRef.current?.getBoundingClientRect()
    if (!rect) return
    setMenu({ x: rect.left, y: rect.bottom + 6 })
  }

  return (
    <>
      <header className="top-bar h-11 flex items-center px-3 gap-2 bg-transparent sm:h-12 sm:px-5 sm:gap-3.5">
        <div className="group relative shrink-0">
          <button
            ref={avatarRef}
            type="button"
            className={`w-9 h-9 rounded-full bg-base p-0.5 cursor-pointer transition ${avatarClass}`}
            aria-label={roleLabel}
            aria-describedby={menu ? undefined : 'avatar-menu-hint'}
            aria-haspopup="menu"
            aria-expanded={menu !== null}
            aria-controls={menu ? 'avatar-menu' : undefined}
            onClick={toggleMenu}
          >
            <div className="w-full h-full rounded-full bg-active-surface flex items-center justify-center text-secondary overflow-hidden">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="8" r="4" />
                <path d="M4 20c0-4 4-6 8-6s8 2 8 6" />
              </svg>
            </div>
          </button>
          {role === 'admin' && (
            <span
              data-admin-shield-badge
              className="pointer-events-none absolute -bottom-0.5 -right-0.5 grid h-4 w-4 place-items-center rounded-full border-2 border-base bg-accent text-white"
              aria-hidden="true"
            >
              <ShieldCheck size={10} strokeWidth={2.5} />
            </span>
          )}
          {!menu && (
            <span
              id="avatar-menu-hint"
              role="tooltip"
              className="pointer-events-none absolute left-0 top-[calc(100%+6px)] z-50 whitespace-nowrap text-[11px] text-secondary opacity-0 transition-[opacity,transform] duration-150 ease-out translate-y-1 group-hover:translate-y-0 group-hover:opacity-100"
            >
              点击打开菜单
            </span>
          )}
        </div>
        <div className="flex-1" />
        <div className="flex items-center gap-2.5">
          <img src="/logo.svg" alt="logo" className="w-7 h-7" />
          <span className="top-bar-title text-secondary text-[16px] leading-6 font-medium pointer-events-none">Livestream Studio Setup Assistant</span>
        </div>
        <div className="flex-1 flex items-center justify-end gap-3.5">
          <Link
            to="/plans"
            className="top-bar-icon-button top-bar-plans-button inline-flex h-8 items-center gap-1.5 rounded-card px-2.5 text-xs text-secondary hover:bg-active-surface hover:text-primary"
            title="我的方案"
            aria-label="我的方案"
          >
            <Clapperboard size={15} aria-hidden="true" />
            <span className="hidden sm:inline">我的方案</span>
          </Link>
          <button
            type="button"
            onClick={onRestoreCenterCard}
            className="top-bar-icon-button top-bar-restore-button"
            data-icon-feedback="scale-brightness"
            aria-label="恢复问答窗口初始位置"
            title="恢复问答窗口初始大小和位置"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="11" y="4" width="11" height="16" rx="2" />
              <path d="M2 12h9M2 9l3 3-3 3" />
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
          anchorRef={avatarRef}
        />
      )}
    </>
  )
}
