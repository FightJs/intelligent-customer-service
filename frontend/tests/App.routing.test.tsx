/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from '../src/App'

vi.mock('../src/components/ChatPanel/ChatPanel', () => ({
  default: () => <div>客服主界面</div>,
}))

describe('App 三态路由', () => {
  it('未登录 → 显示登录界面', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: '客户登录' })).toBeInTheDocument()
  })

  it('已登录未进入 → 显示呼吸页', () => {
    localStorage.setItem('ics_dev_auth', 'true')
    render(<App />)
    expect(screen.getByText('智能客服工作台')).toBeInTheDocument()
    expect(screen.getByText('点击进入系统')).toBeInTheDocument()
    expect(screen.queryByText('客服主界面')).not.toBeInTheDocument()
  })

  it('呼吸页点击 → 进入工作台', () => {
    localStorage.setItem('ics_dev_auth', 'true')
    render(<App />)
    fireEvent.click(screen.getByText('智能客服工作台'))
    expect(screen.getByText('客服主界面')).toBeInTheDocument()
    expect(screen.queryByText('点击进入系统')).not.toBeInTheDocument()
  })
})
