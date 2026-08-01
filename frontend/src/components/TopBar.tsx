import type { Theme } from '../state/theme'

interface Props {
  theme: Theme
  onToggleTheme: () => void
  onReset: () => void
  progressVisible: boolean
  deliveryOpen: boolean
  onToggleProgress: () => void
  onToggleDelivery: () => void
}

export default function TopBar({
  theme, onToggleTheme, onReset,
  progressVisible, deliveryOpen, onToggleProgress, onToggleDelivery,
}: Props) {
  const isDark = theme === 'dark'
  return (
    <header className="top-bar h-12 flex items-center px-5 gap-3.5">
      <div
        className="w-9 h-9 rounded-full bg-base ring-1 ring-idle p-0.5 shrink-0 cursor-pointer hover:ring-accent/60 transition"
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
          onClick={onToggleTheme}
          className="p-2 rounded hover:bg-active-surface text-secondary"
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
          className="text-muted text-sm hover:text-secondary"
        >
          重新开始
        </button>
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
  )
}
