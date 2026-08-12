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

vi.mock('../src/screens/MarketingScreen', () => ({
  default: () => <div>介绍页</div>,
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

  it('未登录访问 /welcome 可通过呼吸页跳转到 /login 登录页', () => {
    vi.useFakeTimers()
    authState.user = null
    renderAt('/welcome')

    fireEvent.click(screen.getByRole('button', { name: '进入呼吸页' }))
    act(() => vi.advanceTimersByTime(440))

    expect(screen.getByText('登录页')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/login')
  })

  it('未登录访问受保护路由会回到 /login', () => {
    authState.user = null
    renderAt('/workbench')

    expect(screen.getByText('登录页')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/login')
  })

  it('已登录访问登录页会回到工作台', () => {
    renderAt('/login')

    expect(screen.getByText('工作台')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/workbench')
  })

  it('首页展示公开介绍页', () => {
    renderAt('/')

    expect(screen.getByText('介绍页')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/')
  })

  it('旧 breathing 路径重定向到登录页', () => {
    authState.user = null
    renderAt('/breathing')

    expect(screen.getByText('登录页')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/login')
  })
})
