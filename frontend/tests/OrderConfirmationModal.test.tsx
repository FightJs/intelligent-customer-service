/// <reference types="@testing-library/jest-dom/vitest" />
import {
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'
import OrderConfirmationModal from '../src/components/DeliveryPanel/OrderConfirmationModal'
import { FormProvider } from '../src/state/FormContext'

const { sendOrderMock } = vi.hoisted(() => ({
  sendOrderMock: vi.fn(),
}))

vi.mock('../src/api/client', () => ({
  sendOrder: sendOrderMock,
}))

describe('OrderConfirmationModal', () => {
  beforeEach(() => {
    sendOrderMock.mockReset()
    sessionStorage.clear()
    sessionStorage.setItem(
      'ics_session_id',
      'session-1',
    )
  })

  it('显示订单分步确认', () => {
    render(
      <FormProvider>
        <OrderConfirmationModal
          onClose={vi.fn()}
          onSent={vi.fn()}
        />
      </FormProvider>,
    )

    expect(
      screen.getByRole(
        'dialog',
        {
          name: '发送订单',
        },
      ),
    ).toBeInTheDocument()

    expect(
      screen.getByText('客户信息'),
    ).toBeInTheDocument()

    expect(
      screen.getByRole(
        'button',
        {
          name: '下一步',
        },
      ),
    ).toBeInTheDocument()
  })

  it('最终确认时调用发送订单接口', async () => {
    sendOrderMock.mockResolvedValue({
      delivery_id: 7,
      sent: true,
      message: '订单发送成功',
    })

    const onSent = vi.fn()

    render(
      <FormProvider>
        <OrderConfirmationModal
          onClose={vi.fn()}
          onSent={onSent}
        />
      </FormProvider>,
    )

    fireEvent.click(
      screen.getByRole(
        'button',
        {
          name: '下一步',
        },
      ),
    )

    fireEvent.click(
      screen.getByRole(
        'button',
        {
          name: '下一步',
        },
      ),
    )

    fireEvent.click(
      screen.getByRole(
        'button',
        {
          name: '确认发送',
        },
      ),
    )

    await waitFor(() => {
      expect(sendOrderMock).toHaveBeenCalledWith(
        'session-1',
      )
    })

    expect(onSent).toHaveBeenCalledTimes(1)

    expect(
      await screen.findByText('订单发送成功'),
    ).toBeInTheDocument()
  })

  it('点击关闭按钮触发关闭', () => {
    const onClose = vi.fn()

    render(
      <FormProvider>
        <OrderConfirmationModal
          onClose={onClose}
          onSent={vi.fn()}
        />
      </FormProvider>,
    )

    fireEvent.click(
      screen.getByRole(
        'button',
        {
          name: '关闭订单确认',
        },
      ),
    )

    expect(onClose).toHaveBeenCalledTimes(1)
  })
})