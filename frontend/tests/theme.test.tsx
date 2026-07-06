import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useTheme } from '../src/state/theme'

describe('useTheme', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.classList.remove('light')
  })

  it('无 localStorage 时默认 dark，不加 .light 类', () => {
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('dark')
    expect(document.documentElement.classList.contains('light')).toBe(false)
  })

  it('localStorage 存 light 时初始化为 light，加 .light 类', () => {
    localStorage.setItem('theme', 'light')
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('light')
    expect(document.documentElement.classList.contains('light')).toBe(true)
  })

  it('toggleTheme 翻转主题并持久化', () => {
    const { result } = renderHook(() => useTheme())
    act(() => result.current.toggleTheme())
    expect(result.current.theme).toBe('light')
    expect(localStorage.getItem('theme')).toBe('light')
    expect(document.documentElement.classList.contains('light')).toBe(true)

    act(() => result.current.toggleTheme())
    expect(result.current.theme).toBe('dark')
    expect(localStorage.getItem('theme')).toBe('dark')
    expect(document.documentElement.classList.contains('light')).toBe(false)
  })
})
