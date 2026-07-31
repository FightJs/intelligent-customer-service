/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import FloatingCard from '../src/components/FloatingCard'

describe('FloatingCard', () => {
  it('渲染 children 并应用 pos 到 transform', () => {
    render(
      <FloatingCard pos={{ x: 10, y: 20 }} dragging={false} onDragStart={() => {}} z={30} onBringToFront={() => {}} width={280}>
        <div>卡片内容</div>
      </FloatingCard>
    )
    expect(screen.getByText('卡片内容')).toBeInTheDocument()
    expect(screen.getByText('卡片内容').closest('[data-floating-card]')).toHaveStyle({ transform: 'translate(10px, 20px)' })
  })

  it('handle onMouseDown 触发 onDragStart', () => {
    const onDragStart = vi.fn()
    render(
      <FloatingCard pos={{ x: 0, y: 0 }} dragging={false} onDragStart={onDragStart} z={30} onBringToFront={() => {}} width={280} handleLabel="标题">
        <div>x</div>
      </FloatingCard>
    )
    fireEvent.mouseDown(screen.getByText('标题'))
    expect(onDragStart).toHaveBeenCalled()
  })

  it('容器 mousedown 触发 onBringToFront', () => {
    const onBringToFront = vi.fn()
    const { container } = render(
      <FloatingCard pos={{ x: 0, y: 0 }} dragging={false} onDragStart={() => {}} z={30} onBringToFront={onBringToFront} width={280}>
        <div>x</div>
      </FloatingCard>
    )
    fireEvent.mouseDown(container.querySelector('[data-floating-card]')!)
    expect(onBringToFront).toHaveBeenCalled()
  })
})
