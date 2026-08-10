/// <reference types="@testing-library/jest-dom/vitest" />
import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../src/App'

const authState = vi.hoisted(() => ({
  user: { id: 1, username: 'tester', role: 'user' as const },
  loading: false,
}))

vi.mock('../src/state/AuthContext', () => ({
  useAuth: () => authState,
}))

vi.mock('../src/screens/AuthScreen', () => ({
  default: () => <div>登录页</div>,
}))

vi.mock('../src/screens/Workbench', () => ({
  default: () => <div>工作台</div>,
}))

vi.mock('../src/screens/AdminScreen', () => ({
  default: () => <div>管理后台</div>,
}))

vi.mock('../src/components/BreathingScreen', () => ({
  default: ({ onEnter }: { onEnter: () => void }) => (
    <button type="button" onClick={onEnter}>进入呼吸页</button>
  ),
}))

function LocationProbe() {
  return <output data-testid="location"><LocationText /></output>
}

function LocationText() {
  return useLocation().pathname
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
      <LocationProbe />
    </MemoryRouter>,
  )
}

describe('App 路由同步', () => {
  afterEach(() => {
    authState.user = { id: 1, username: 'tester', role: 'user' }
    vi.useRealTimers()
  })

  it('已登录访问 /workbench 直接显示工作台', () => {
    renderAt('/workbench')

    expect(screen.getByText('工作台')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/workbench')
  })

  it('未登录访问 /login 可通过加载页跳转到 /breathing 登录页', () => {
    vi.useFakeTimers()
    authState.user = null
    renderAt('/login')

    fireEvent.click(screen.getByRole('button', { name: '进入呼吸页' }))
    act(() => vi.advanceTimersByTime(440))

    expect(screen.getByText('登录页')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/breathing')
  })

  it('未登录访问受保护路由会回到 /login', () => {
    authState.user = null
    renderAt('/workbench')

    expect(screen.getByRole('button', { name: '进入呼吸页' })).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/login')
  })

  it('已登录访问登录页会回到工作台', () => {
    renderAt('/breathing')

    expect(screen.getByText('工作台')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/workbench')
  })
})
