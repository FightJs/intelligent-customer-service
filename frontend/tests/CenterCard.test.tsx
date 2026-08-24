/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import CenterCard from '../src/components/CenterCard/CenterCard'
import { ZStackProvider } from '../src/hooks/useZStack'

describe('CenterCard', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('进入界面使用适配三栏的初始尺寸和复位按钮', () => {
    const { container } = render(<CenterCard />)
    const restoreButton = screen.getByRole('button', { name: '恢复问答窗口初始位置' })
    const card = container.querySelector('[data-center-card]') as HTMLElement

    expect(restoreButton).toBeInTheDocument()
    expect(restoreButton).not.toHaveClass('hover:bg-active-surface')
    expect(card).toHaveStyle({ width: '930px', height: '800px' })
    expect(card.style.transform).toBe('translate3d(0px, 0px, 0)')
    expect(screen.queryByText('中央卡片 4:3')).not.toBeInTheDocument()
  })

  it('拖动和缩放后点击图标恢复初始大小与位置', () => {
    const { container } = render(<CenterCard />)
    const card = container.querySelector('[data-center-card]') as HTMLElement
    const handle = container.querySelector('[data-card-handle]') as HTMLElement
    const resizeHandle = container.querySelector('[data-resize-handle]') as HTMLElement

    fireEvent.mouseDown(handle, { clientX: 0, clientY: 0 })
    fireEvent.mouseMove(document, { clientX: 45, clientY: 30 })
    fireEvent.mouseUp(document)
    fireEvent.mouseDown(resizeHandle, { clientX: 0, clientY: 0 })
    fireEvent.mouseMove(document, { clientX: 80, clientY: 40 })
    fireEvent.mouseUp(document)

    expect(card.style.transform).toBe('translate3d(45px, 30px, 0)')
    expect(card).toHaveStyle({ width: '1010px', height: '840px' })

    fireEvent.click(screen.getByRole('button', { name: '恢复问答窗口初始位置' }))
    expect(card.style.transform).toBe('translate3d(0px, 0px, 0)')
    expect(card).toHaveStyle({ width: '930px', height: '800px' })
  })

  it('忽略旧缓存，每次进入均从初始布局开始', () => {
    localStorage.setItem('centercard.pos.v2', JSON.stringify({ x: 120, y: 80 }))
    localStorage.setItem('centercard.size.v2', JSON.stringify({ w: 380, h: 430 }))

    const { container } = render(<CenterCard />)
    const card = container.querySelector('[data-center-card]') as HTMLElement

    expect(card.style.transform).toBe('translate3d(0px, 0px, 0)')
    expect(card).toHaveStyle({ width: '930px', height: '800px' })
  })

  it('对话框内部控件获得焦点时同步置顶', () => {
    const { container } = render(
      <ZStackProvider>
        <CenterCard>
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
