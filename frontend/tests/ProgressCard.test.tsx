import { describe, it, expect } from 'vitest'
import { act, render, fireEvent } from '@testing-library/react'
import ProgressCard from '../src/components/ProgressCard/ProgressCard'
import { FormProvider } from '../src/state/FormContext'

function renderCard(props: Partial<React.ComponentProps<typeof ProgressCard>> = {}) {
  return render(
    <FormProvider>
      <ProgressCard visible={true} {...props} />
    </FormProvider>
  )
}

describe('ProgressCard', () => {
  it('visible=false 不渲染卡片', () => {
    const { container } = renderCard({ visible: false })
    expect(container.querySelector('[data-floating-card]')).toBeNull()
  })

  it('visible=true 渲染卡片 + 标题', () => {
    const { container, getByText } = renderCard()
    expect(container.querySelector('[data-floating-card]')).toBeTruthy()
    expect(getByText(/采集进度/)).toBeTruthy()
  })

  it('默认位置下移至 y=96，为上移保留更多空间', () => {
    const { container } = renderCard()
    expect(container.querySelector('[data-floating-card]')).toHaveStyle({
      transform: 'translate(16px, 96px)',
    })
  })

  it('初始状态(全 pending)显示所有章节,无已完成分组', () => {
    const { queryByText, getByText } = renderCard()
    expect(queryByText(/已完成/)).toBeNull()
    // 当前章节是 customer(初始 currentSectionId);标题为「一、客户基础信息」,用子串匹配
    expect(getByText(/客户基础信息/)).toBeTruthy()
  })

  it('header 有拖拽手柄区', () => {
    const { container } = renderCard()
    const header = container.querySelector('[data-card-handle]') as HTMLElement
    expect(header).toBeTruthy()
  })

  it('默认态提供右下角缩放手柄', () => {
    const { container } = renderCard()
    expect(container.querySelector('[data-resize-handle]')).toBeTruthy()
  })

  it('底部汇总显示计数', () => {
    const { getByText } = renderCard()
    // 全 pending 状态:0 完成 0 进行 10 待
    expect(getByText(/待/)).toBeTruthy()
  })

  it('点未完成章节展开 FieldDetail', () => {
    const { container, getByText } = renderCard()
    const row = getByText(/客户基础信息/).closest('[data-section-row]') as HTMLElement
    fireEvent.click(row)
    expect(container.querySelector('[data-field-detail]')).toBeTruthy()
  })

  it('向上拖拽时贴齐工作台顶部，不越过导航栏', () => {
    const { container } = renderCard()
    const header = container.querySelector('[data-card-handle]') as HTMLElement
    const card = container.querySelector('[data-floating-card]') as HTMLElement

    fireEvent.mouseDown(header, { clientX: 50, clientY: 96 })
    act(() => {
      document.dispatchEvent(new MouseEvent('mousemove', { clientX: 50, clientY: -1000 }))
    })

    expect(card.style.transform).toBe('translate(16px, 0px)')

    act(() => {
      document.dispatchEvent(new MouseEvent('mouseup'))
    })
  })

  it('拖拽 header 改变 transform', () => {
    const { container } = renderCard()
    const header = container.querySelector('[data-card-handle]') as HTMLElement
    fireEvent.mouseDown(header, { clientX: 50, clientY: 50 })
    document.dispatchEvent(new MouseEvent('mousemove', { clientX: 100, clientY: 80 }))
    const card = container.querySelector('[data-floating-card]') as HTMLElement
    // pos 从 (16, 96) → (16+50, 96+30) = (66, 126)
    expect(card.style.transform).toContain('translate')
  })
})
