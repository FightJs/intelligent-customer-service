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
import FormPreviewSlot from '../src/components/DeliveryPanel/FormPreviewSlot'
import DeliverableSlot from '../src/components/DeliveryPanel/DeliverableSlot'
import { FormProvider } from '../src/state/FormContext'

describe('FormPreviewSlot', () => {
  it('渲染实时客户需求表入口', () => {
    const { container } = render(
      <FormProvider>
        <FormPreviewSlot />
      </FormProvider>,
    )

    expect(
      screen.getByRole(
        'button',
        {
          name: '预览需求表',
        },
      ),
    ).toBeInTheDocument()

    expect(
      screen.getByText('客户需求表'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('实时更新 · 点击查看'),
    ).toBeInTheDocument()

    expect(
      container.querySelector('.folder-card'),
    ).toBeInTheDocument()
  })

  it('点击需求表触发预览', () => {
    const onPreview = vi.fn()

    render(
      <FormProvider>
        <FormPreviewSlot onPreview={onPreview} />
      </FormProvider>,
    )

    fireEvent.click(
      screen.getByRole(
        'button',
        {
          name: '预览需求表',
        },
      ),
    )

    expect(onPreview).toHaveBeenCalledTimes(1)
  })
})

describe('DeliverableSlot', () => {
  it('三类结构化内容不可交互', () => {
    render(
      <FormProvider>
        <DeliverableSlot />
      </FormProvider>,
    )

    expect(
      screen.getByText('场景设计说明'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('设备参数清单'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('需求确认书'),
    ).toBeInTheDocument()

    expect(
      screen.queryByRole(
        'button',
        {
          name: /场景设计说明/,
        },
      ),
    ).not.toBeInTheDocument()

    expect(
      screen.queryByRole(
        'button',
        {
          name: /设备参数清单/,
        },
      ),
    ).not.toBeInTheDocument()

    expect(
      screen.queryByRole(
        'button',
        {
          name: /需求确认书/,
        },
      ),
    ).not.toBeInTheDocument()
  })

  it('信息未完成时禁止发送订单', () => {
    const onSendOrder = vi.fn()

    render(
      <FormProvider>
        <DeliverableSlot
          onSendOrder={onSendOrder}
        />
      </FormProvider>,
    )

    const button = screen.getByRole(
      'button',
      {
        name: /发送订单/,
      },
    )

    expect(button).toBeDisabled()

    fireEvent.click(button)

    expect(onSendOrder).not.toHaveBeenCalled()
  })

  it('已发送后显示订单已发送', () => {
    render(
      <FormProvider>
        <DeliverableSlot orderSent />
      </FormProvider>,
    )

    expect(
      screen.getByRole(
        'button',
        {
          name: /订单已发送/,
        },
      ),
    ).toBeDisabled()
  })
})