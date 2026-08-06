/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import OrderConfirmationModal from '../src/components/DeliveryPanel/OrderConfirmationModal'
import { FormProvider } from '../src/state/FormContext'

describe('OrderConfirmationModal', () => {
  it('显示分步确认的客户信息并提供下一步操作', () => {
    render(
      <FormProvider>
        <OrderConfirmationModal onClose={vi.fn()} />
      </FormProvider>,
    )

    expect(screen.getByRole('dialog', { name: '发送订单' })).toBeInTheDocument()
    expect(screen.getByText('客户信息')).toBeInTheDocument()
    expect(screen.getAllByText('未填写')).toHaveLength(3)
    expect(screen.getByRole('button', { name: '下一步' })).toBeInTheDocument()
  })

  it('点击关闭按钮触发关闭回调', () => {
    const onClose = vi.fn()
    render(
      <FormProvider>
        <OrderConfirmationModal onClose={onClose} />
      </FormProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: '关闭订单确认' }))

    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
