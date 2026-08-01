/// <reference types="@testing-library/jest-dom/vitest" />
import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../src/App'

vi.mock('../src/components/ChatPanel/ChatPanel', () => ({
  default: () => <div>客服主界面</div>,
}))

function enterWorkbench() {
  vi.useFakeTimers()
  localStorage.setItem('ics_dev_auth', 'true')
  render(<App />)
  fireEvent.click(screen.getByText('智能客服工作台'))
  act(() => vi.advanceTimersByTime(440))
}

describe('App 工作台布局', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('进入工作台后渲染中央卡、Loader 和交付物', () => {
    enterWorkbench()
    expect(screen.getByText('客服主界面')).toBeInTheDocument()
    // Loader（含 SVG）固定右上
    expect(document.querySelector('svg')).toBeInTheDocument()
    // 交付物悬浮卡（含「交付物生成」标题）
    expect(screen.getByText(/交付物生成/)).toBeInTheDocument()
  })

  it('点击中央卡放大 → 还原按钮出现', () => {
    enterWorkbench()
    fireEvent.click(screen.getByRole('button', { name: '放大' }))
    expect(screen.getByRole('button', { name: '还原' })).toBeInTheDocument()
  })

  it('还原后放大按钮恢复', () => {
    enterWorkbench()
    fireEvent.click(screen.getByRole('button', { name: '放大' }))
    fireEvent.click(screen.getByRole('button', { name: '还原' }))
    expect(screen.getByRole('button', { name: '放大' })).toBeInTheDocument()
  })
})
