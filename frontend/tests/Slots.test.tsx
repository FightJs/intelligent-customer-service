/// <reference types="@testing-library/jest-dom/vitest" />
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import FormPreviewSlot from '../src/components/DeliveryPanel/FormPreviewSlot'
import DeliverableSlot from '../src/components/DeliveryPanel/DeliverableSlot'
import { FormProvider } from '../src/state/FormContext'

describe('FormPreviewSlot', () => {
  it('渲染 Loader 动效（含 SVG）', () => {
    const { container } = render(<FormPreviewSlot />)
    expect(container.querySelector('svg')).toBeInTheDocument()
  })
  it('含流光 trace 动画路径', () => {
    const { container } = render(<FormPreviewSlot />)
    expect(container.querySelectorAll('.trace-flow').length).toBeGreaterThan(0)
  })
})

describe('DeliverableSlot', () => {
  it('渲染交付物标题', () => {
    render(
      <FormProvider>
        <DeliverableSlot />
      </FormProvider>,
    )
    // 空态下「交付物生成」标题与「请先...即可生成交付物」提示均含「交付物」，故用 getAllByText
    expect(screen.getAllByText(/交付物/).length).toBeGreaterThan(0)
  })
})
