/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import MarketingScreen from '../src/screens/MarketingScreen'

function LocationProbe() {
  return <output data-testid="location"><LocationText /></output>
}

function LocationText() {
  return useLocation().pathname
}

describe('MarketingScreen', () => {
  it('展示 demo 版介绍页的首屏主张和瀑布视觉', () => {
    render(<MemoryRouter><MarketingScreen /></MemoryRouter>)

    expect(screen.getByRole('heading', { name: '让每一条需求，汇成可执行的直播间。' })).toBeInTheDocument()
    expect(screen.getByTestId('waterfall-hero')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: '开始咨询' })).not.toHaveLength(0)
  })

  it('所有开始咨询入口都导航到登录页', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <MarketingScreen />
        <LocationProbe />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getAllByRole('button', { name: '开始咨询' })[0])

    expect(screen.getByTestId('location')).toHaveTextContent('/login')
  })

  it('导航菜单用锚点指向能力、交付物和场景区', () => {
    render(<MemoryRouter><MarketingScreen /></MemoryRouter>)

    expect(screen.getByRole('link', { name: '能力' })).toHaveAttribute('href', '#capabilities')
    expect(screen.getByRole('link', { name: '交付' })).toHaveAttribute('href', '#deliverables')
    expect(screen.getByRole('link', { name: '场景' })).toHaveAttribute('href', '#scenarios')
  })

  it('展示完整项目介绍所需的价值、指标、对照和 FAQ 内容', () => {
    render(<MemoryRouter><MarketingScreen /></MemoryRouter>)

    expect(screen.getByRole('heading', { name: '把反复确认，变成一次有方向的对话。' })).toBeInTheDocument()
    expect(screen.getByText('47 个关键字段')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '同一段对话，交付前后是两种状态。' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '常见问题' })).toBeInTheDocument()
    expect(screen.getByText('AI 会替代人工交付吗？')).toBeInTheDocument()
  })

  it('滚动显隐元素保持可往返的动画状态', () => {
    render(<MemoryRouter><MarketingScreen /></MemoryRouter>)

    const reveal = screen.getByText('FROM CONVERSATION TO DELIVERY')
    expect(reveal).toHaveClass('marketing-reveal')

    reveal.classList.add('is-visible')
    expect(reveal).toHaveClass('is-visible')

    reveal.classList.remove('is-visible')
    expect(reveal).not.toHaveClass('is-visible')
  })
})
