import type { Theme } from '../state/theme'

interface Props {
  theme: Theme
  onToggleTheme: () => void
  onReset: () => void
  progressOpen: boolean
  deliveryOpen: boolean
  onToggleProgress: () => void
  onToggleDelivery: () => void
}

export default function TopBar({
  theme, onToggleTheme, onReset,
  progressOpen, deliveryOpen, onToggleProgress, onToggleDelivery,
}: Props) {
  const isDark = theme === 'dark'
  return (
    <div className="h-10 flex items-center px-4 gap-3">
      <div
        className="w-8 h-8 rounded-full bg-base ring-1 ring-idle p-0.5 shrink-0 cursor-pointer hover:ring-accent/60 transition"
        aria-label="账户"
        role="button"
        tabIndex={0}
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
        className="p-1.5 rounded hover:bg-active-surface text-secondary"
        aria-label={progressOpen ? '收起采集进度' : '展开采集进度'}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          {progressOpen ? (
            <>
              <rect x="2" y="4" width="11" height="16" rx="2" />
              <path d="M22 12h-5M19 9l-3 3 3 3" />
            </>
          ) : (
            <>
              <rect x="2" y="4" width="11" height="16" rx="2" />
              <path d="M13 12h9M19 9l3 3-3 3" />
            </>
          )}
        </svg>
      </button>
      <div className="flex-1" />
      <div className="flex items-center gap-2">
        <img src={isDark ? '/lit-dark.svg' : '/lit-light.svg'} alt="logo" className="w-6 h-6 rounded-md" />
        <span className="text-secondary text-sm font-medium pointer-events-none">Livestream Studio Setup Assistant</span>
      </div>
      <div className="flex-1 flex items-center justify-end gap-4">
        <button
          type="button"
          onClick={onToggleTheme}
          className="p-1.5 rounded hover:bg-active-surface text-secondary"
          aria-label={isDark ? '切换到浅色主题' : '切换到深色主题'}
        >
          {isDark ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="5" />
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
            </svg>
          )}
        </button>
        <button
          type="button"
          onClick={onReset}
          className="text-muted text-xs hover:text-secondary"
        >
          重新开始
        </button>
        <button
          type="button"
          onClick={onToggleDelivery}
          className="p-1.5 rounded hover:bg-active-surface text-secondary"
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
    </div>
  )
}
