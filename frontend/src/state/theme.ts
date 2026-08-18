import { useState, useEffect, useCallback, useRef } from 'react'

export type Theme = 'dark' | 'light'

const THEME_MIGRATION_KEY = 'theme-preference-v2'

export function useTheme(): { theme: Theme; toggleTheme: () => void } {
  const transitionTimerRef = useRef<number | null>(null)
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('theme')
    const migrated = localStorage.getItem(THEME_MIGRATION_KEY) === '1'
    return migrated && saved === 'dark' ? 'dark' : 'light'
  })

  useEffect(() => {
    const root = document.documentElement
    root.classList.toggle('light', theme === 'light')
    root.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('theme', theme)
    localStorage.setItem(THEME_MIGRATION_KEY, '1')
  }, [theme])

  useEffect(() => () => {
    if (transitionTimerRef.current !== null) window.clearTimeout(transitionTimerRef.current)
  }, [])

  const toggleTheme = useCallback(() => {
    const root = document.documentElement
    if (transitionTimerRef.current !== null) window.clearTimeout(transitionTimerRef.current)
    root.classList.add('theme-transition')
    transitionTimerRef.current = window.setTimeout(() => {
      root.classList.remove('theme-transition')
      transitionTimerRef.current = null
    }, 300)
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }, [])

  return { theme, toggleTheme }
}
