/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import CenterCard from '../src/components/CenterCard/CenterCard'
import { ZStackProvider } from '../src/hooks/useZStack'

describe('CenterCard', () => {
  it('默认态渲染卡片和放大按钮', () => {
    render(<CenterCard expanded={false} onToggleExpand={() => {}} />)
    const expandButton = screen.getByRole('button', { name: '放大' })
    expect(expandButton).toBeInTheDocument()
    expect(expandButton).not.toHaveClass('hover:bg-active-surface')
    expect(screen.queryByText('中央卡片 4:3')).not.toBeInTheDocument()
  })

  it('点击放大按钮触发 onToggleExpand', () => {
    const onToggleExpand = vi.fn()
    render(<CenterCard expanded={false} onToggleExpand={onToggleExpand} />)
    fireEvent.click(screen.getByRole('button', { name: '放大' }))
    expect(onToggleExpand).toHaveBeenCalled()
  })

  it('放大态显示还原按钮，不显示放大按钮', () => {
    render(<CenterCard expanded={true} onToggleExpand={() => {}} />)
    expect(screen.getByRole('button', { name: '还原' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '放大' })).not.toBeInTheDocument()
  })

  it('放大态根元素标记 data-expanded=true', () => {
    const { container } = render(<CenterCard expanded={true} onToggleExpand={() => {}} />)
    expect(container.querySelector('[data-center-card]')).toHaveAttribute('data-expanded', 'true')
  })

  it('默认态根元素标记 data-expanded=false', () => {
    const { container } = render(<CenterCard expanded={false} onToggleExpand={() => {}} />)
    expect(container.querySelector('[data-center-card]')).toHaveAttribute('data-expanded', 'false')
  })

  it('两种状态均锚定在中央 Grid 区，避免缩放时切换定位坐标系', () => {
    const { container } = render(<CenterCard expanded={false} onToggleExpand={() => {}} />)
    expect(container.querySelector('[data-center-card]')).toHaveStyle({ inset: '0' })
  })

  it('对话框内部控件获得焦点时同步置顶', () => {
    const { container } = render(
      <ZStackProvider>
        <CenterCard expanded={false} onToggleExpand={() => {}}>
          <input aria-label="对话框输入" />
        </CenterCard>
      </ZStackProvider>,
    )

    const card = container.querySelector('[data-center-card]') as HTMLElement
    const input = screen.getByRole('textbox', { name: '对话框输入' })
    const initialZ = Number.parseInt(card.style.zIndex, 10)

    expect(initialZ).toBe(40)
    fireEvent.focus(input)

    expect(Number.parseInt(card.style.zIndex, 10)).toBeGreaterThan(initialZ)
  })
})
