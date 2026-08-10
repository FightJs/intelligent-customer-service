/// <reference types="@testing-library/jest-dom/vitest" />
import {
  fireEvent,
  render,
  screen,
} from '@testing-library/react'
import {
  describe,
  expect,
  it,
  vi,
} from 'vitest'
import BreathingScreen
  from '../src/components/BreathingScreen'

describe('BreathingScreen', () => {
  it('展示系统介绍和进入入口', () => {
    render(
      <BreathingScreen onEnter={() => {}} />,
    )

    expect(
      screen.getByText('智能客服工作台'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('智能需求采集'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('实时信息整理'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('专业方案交付'),
    ).toBeInTheDocument()

    expect(
      screen.getByRole('button', {
        name: '进入智能客服系统',
      }),
    ).toBeInTheDocument()
  })

  it('点击进入按钮触发 onEnter', () => {
    const onEnter = vi.fn()

    render(
      <BreathingScreen onEnter={onEnter} />,
    )

    fireEvent.click(
      screen.getByRole('button', {
        name: '进入智能客服系统',
      }),
    )

    expect(onEnter).toHaveBeenCalledTimes(1)
  })

  it('保留呼吸光晕动画元素', () => {
    const { container } = render(
      <BreathingScreen onEnter={() => {}} />,
    )

    expect(
      container.querySelector(
        '[data-breath-glow]',
      ),
    ).toBeInTheDocument()
  })

  it('离场时增加 is-leaving 状态', () => {
    const { container } = render(
      <BreathingScreen
        onEnter={() => {}}
        leaving
      />,
    )

    expect(
      container.querySelector(
        '.breathing-screen',
      ),
    ).toHaveClass('is-leaving')
  })
})