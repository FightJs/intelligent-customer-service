import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { Check, ChevronDown, ChevronRight, Filter, Users } from 'lucide-react'
import type { AdminUser } from '../../api/client'

type FilterPane = 'status' | 'type' | 'owner'

interface DeliveryFilterMenuProps {
  users: AdminUser[]
  value: number | ''
  onChange: (userId: number | '') => void
}

const FILTER_PANES: { id: FilterPane; label: string }[] = [
  { id: 'status', label: '交付状态' },
  { id: 'type', label: '交付类型' },
  { id: 'owner', label: '所属用户' },
]

/**
 * 交付物筛选的二级菜单。
 * 现阶段接口仅支持按所属用户筛选，其他分组保留信息架构并明确其待接入状态。
 */
export default function DeliveryFilterMenu({ users, value, onChange }: DeliveryFilterMenuProps) {
  const [open, setOpen] = useState(false)
  const [pane, setPane] = useState<FilterPane>('status')
  const [menuPosition, setMenuPosition] = useState<{ left: number; top: number; width: number }>()
  const rootRef = useRef<HTMLDivElement>(null)
  const selectedUser = users.find((user) => user.id === value)
  const label = selectedUser ? selectedUser.username : '全部交付物'

  useEffect(() => {
    function closeOnOutsidePointer(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }

    document.addEventListener('pointerdown', closeOnOutsidePointer)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsidePointer)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [])

  const updateMenuPosition = useCallback(() => {
    const rect = rootRef.current?.getBoundingClientRect()
    if (!rect) return

    const width = Math.min(320, window.innerWidth - 32)
    const leftOfTrigger = rect.left - width - 12
    const canOpenLeft = leftOfTrigger >= 16
    setMenuPosition({
      width,
      left: canOpenLeft
        ? leftOfTrigger
        : Math.min(Math.max(16, rect.right - width), window.innerWidth - width - 16),
      top: canOpenLeft ? rect.top : rect.bottom + 8,
    })
  }, [])

  useEffect(() => {
    if (!open) return
    updateMenuPosition()
    window.addEventListener('resize', updateMenuPosition)
    return () => window.removeEventListener('resize', updateMenuPosition)
  }, [open, updateMenuPosition])

  function chooseUser(userId: number | '') {
    onChange(userId)
    setOpen(false)
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => {
          if (!open) updateMenuPosition()
          setOpen((current) => !current)
        }}
        className="inline-flex h-[34px] min-w-[132px] items-center justify-between gap-2 rounded-card bg-surface px-2.5 text-sm text-secondary ring-1 ring-idle transition-colors hover:text-primary focus:outline-none focus:ring-accent"
      >
        <span className="inline-flex min-w-0 items-center gap-1.5">
          <Filter size={14} className="shrink-0 text-muted" />
          <span className="truncate">{label}</span>
        </span>
        <ChevronDown size={14} className={`shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div
          role="menu"
          aria-label="交付物筛选"
          style={menuPosition}
          className="fixed z-30 grid max-h-[min(360px,calc(100dvh-32px))] grid-cols-[112px_minmax(0,1fr)] grid-rows-[minmax(0,1fr)] overflow-hidden rounded-card border border-idle bg-surface shadow-[0_4px_8px_rgb(0_0_0_/_0.28)]"
        >
          <div className="border-r border-idle/70 bg-base/60 p-1.5">
            {FILTER_PANES.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setPane(item.id)}
                className={`flex w-full items-center justify-between rounded-card px-2 py-2 text-left text-xs transition-colors ${
                  pane === item.id
                    ? 'bg-active-surface text-primary'
                    : 'text-secondary hover:bg-active-surface/60 hover:text-primary'
                }`}
              >
                {item.label}
                <ChevronRight size={13} className="text-muted" />
              </button>
            ))}
          </div>

          <div className="min-h-0 min-w-0 overflow-y-auto p-1.5">
            {pane === 'status' && <UnavailableOptions title="交付状态" options={['全部状态', '已生成', '待生成']} />}
            {pane === 'type' && <UnavailableOptions title="交付类型" options={['场景设计说明', '设备参数清单', '需求确认书']} />}
            {pane === 'owner' && (
              <div>
                <p className="px-2 py-1.5 text-xs text-muted">所属用户</p>
                <FilterOption label="全部用户" selected={value === ''} onClick={() => chooseUser('')}>
                  <Users size={14} />
                </FilterOption>
                {users.map((user) => (
                  <FilterOption key={user.id} label={user.username} selected={value === user.id} onClick={() => chooseUser(user.id)}>
                    <Users size={14} />
                  </FilterOption>
                ))}
                {users.length === 0 && <p className="px-2 py-3 text-xs text-muted">暂无可筛选用户</p>}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function UnavailableOptions({ title, options }: { title: string; options: string[] }) {
  return (
    <div>
      <p className="px-2 py-1.5 text-xs text-muted">{title}</p>
      {options.map((option) => (
        <div key={option} className="flex items-center gap-2 px-2 py-2 text-sm text-muted">
          <span className="h-3.5 w-3.5" />
          {option}
        </div>
      ))}
      <p className="px-2 py-2 text-xs leading-5 text-muted">该属性等待交付物接口提供后启用。</p>
    </div>
  )
}

function FilterOption({
  label,
  selected,
  onClick,
  children,
}: {
  label: string
  selected: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
      role="menuitemradio"
      aria-checked={selected}
      onClick={onClick}
      className="flex w-full items-center gap-2 rounded-card px-2 py-2 text-left text-sm text-secondary transition-colors hover:bg-active-surface hover:text-primary focus:outline-none focus-visible:ring-1 focus-visible:ring-accent"
    >
      <span className="shrink-0 text-muted">{children}</span>
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {selected && <Check size={14} className="shrink-0 text-accent" />}
    </button>
  )
}
