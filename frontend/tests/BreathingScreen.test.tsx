/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import BreathingScreen from '../src/components/BreathingScreen'

describe('BreathingScreen', () => {
  it('渲染 logo 和标题文案', () => {
    render(<BreathingScreen onEnter={() => {}} />)
    expect(screen.getByText('智能客服工作台')).toBeInTheDocument()
    expect(screen.getByText('点击进入系统')).toBeInTheDocument()
  })

  it('点击触发 onEnter', () => {
    const onEnter = vi.fn()
    render(<BreathingScreen onEnter={onEnter} />)
    fireEvent.click(screen.getByText('智能客服工作台'))
    expect(onEnter).toHaveBeenCalledTimes(1)
  })

  it('有呼吸光晕元素（动画存在）', () => {
    const { container } = render(<BreathingScreen onEnter={() => {}} />)
    const glow = container.querySelector('[data-breath-glow]')
    expect(glow).toBeInTheDocument()
  })
})
