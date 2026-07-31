/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../src/App'

vi.mock('../src/components/ChatPanel/ChatPanel', () => ({
  default: () => <div>客服主界面</div>,
}))

describe('App dev 登录门禁', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('没有登录状态时只显示登录界面', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: '客户登录' }),
    ).toBeInTheDocument()
    expect(screen.queryByText('客服主界面')).not.toBeInTheDocument()
  })

  it('已有正确登录状态时先进呼吸页，点击后进入主界面', () => {
    localStorage.setItem('ics_dev_auth', 'true')

    render(<App />)

    expect(screen.getByText('智能客服工作台')).toBeInTheDocument()
    fireEvent.click(screen.getByText('智能客服工作台'))
    expect(screen.getByText('客服主界面')).toBeInTheDocument()
  })

  it('错误的 localStorage 值不能绕过登录', () => {
    localStorage.setItem('ics_dev_auth', 'false')

    render(<App />)

    expect(
      screen.getByRole('heading', { name: '客户登录' }),
    ).toBeInTheDocument()
    expect(screen.queryByText('客服主界面')).not.toBeInTheDocument()
  })

  it('正确密钥登录后写入状态，重新挂载仍保持登录', () => {
    vi.stubEnv('VITE_DEV_KEY', 'dev-secret-2026')

    const { unmount } = render(<App />)

    fireEvent.change(screen.getByLabelText('访问密钥'), {
      target: { value: 'dev-secret-2026' },
    })
    fireEvent.click(screen.getByRole('button', { name: '进入系统' }))

    expect(localStorage.getItem('ics_dev_auth')).toBe('true')
    expect(screen.getByText('智能客服工作台')).toBeInTheDocument()
    fireEvent.click(screen.getByText('智能客服工作台'))
    expect(screen.getByText('客服主界面')).toBeInTheDocument()

    unmount()
    render(<App />)

    expect(screen.getByText('智能客服工作台')).toBeInTheDocument()
  })
})