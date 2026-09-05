import { useEffect, useRef, type RefObject } from 'react'
import { Sun, Moon, RotateCcw, LogOut } from 'lucide-react'
import type { Theme } from '../state/theme'

interface AvatarMenuProps {
  /** 菜单左上角坐标（视窗坐标，来自头像按钮） */
  pos: { x: number; y: number }
  theme: Theme
  onToggleTheme: () => void
  onReset: () => void
  onLogout: () => void
  onClose: () => void
  anchorRef: RefObject<HTMLElement | null>
}

/**
 * 头像点击菜单：切换主题 / 重新开始 / 退出登录。
 * fixed 定位在头像下方，点击外部或 ESC 关闭。
 */
export default function AvatarMenu({
  pos,
  theme,
  onToggleTheme,
  onReset,
  onLogout,
  onClose,
  anchorRef,
}: AvatarMenuProps) {
  const ref = useRef<HTMLDivElement>(null)

  // 点击菜单外关闭；ESC 关闭
  useEffect(() => {
    function onDown(e: PointerEvent) {
      const target = e.target as Node
      if (
        ref.current
        && !ref.current.contains(target)
        && !anchorRef.current?.contains(target)
      ) onClose()
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [anchorRef, onClose])

  const isDark = theme === 'dark'

  const menuWidth = 176
  const menuHeight = 132
  const viewportPadding = 8
  const style = {
    left: Math.min(
      Math.max(viewportPadding, pos.x),
      Math.max(viewportPadding, window.innerWidth - menuWidth - viewportPadding),
    ),
    top: Math.min(
      Math.max(viewportPadding, pos.y),
      Math.max(viewportPadding, window.innerHeight - menuHeight - viewportPadding),
    ),
  }

  const items = [
    {
      icon: isDark ? <Sun size={15} /> : <Moon size={15} />,
      label: isDark ? '切换到浅色主题' : '切换到深色主题',
      onClick: onToggleTheme,
    },
    { icon: <RotateCcw size={15} />, label: '重新开始', onClick: onReset },
    { icon: <LogOut size={15} />, label: '退出登录', onClick: onLogout, danger: true },
  ]

  return (
    <div
      ref={ref}
      id="avatar-menu"
      style={style}
      className="fixed z-50 min-w-[160px] rounded-card border border-idle/50 bg-surface/95 py-1 shadow-2xl backdrop-blur-md"
      role="menu"
    >
      {items.map(({ icon, label, onClick, danger }) => (
        <button
          key={label}
          type="button"
          role="menuitem"
          onClick={() => {
            onClick()
            onClose()
          }}
          className={`flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm transition-colors hover:bg-active-surface ${
            danger ? 'text-danger' : 'text-secondary hover:text-primary'
          }`}
        >
          {icon}
          {label}
        </button>
      ))}
    </div>
  )
}
