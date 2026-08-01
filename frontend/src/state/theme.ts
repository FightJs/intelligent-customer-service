import { useState, useEffect, useCallback, useRef } from 'react'

export type Theme = 'dark' | 'light'

export function useTheme(): { theme: Theme; toggleTheme: () => void } {
  const transitionTimerRef = useRef<number | null>(null)
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('theme')
    return saved === 'light' ? 'light' : 'dark'
  })

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'light') root.classList.add('light')
    else root.classList.remove('light')
    localStorage.setItem('theme', theme)
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
