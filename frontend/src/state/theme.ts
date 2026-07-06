import { useState, useEffect, useCallback } from 'react'

export type Theme = 'dark' | 'light'

export function useTheme(): { theme: Theme; toggleTheme: () => void } {
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

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }, [])

  return { theme, toggleTheme }
}
