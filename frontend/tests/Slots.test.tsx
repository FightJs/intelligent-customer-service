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
  it('渲染需求表预览入口并隐藏卡片中间的说明文字', () => {
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

    expect(screen.getByText('点击预览需求表')).toBeInTheDocument()
    expect(screen.queryByText('客户需求表')).not.toBeInTheDocument()
    expect(screen.queryByText('实时更新 · 点击查看')).not.toBeInTheDocument()
    expect(screen.queryByText('SECTIONS')).not.toBeInTheDocument()
    expect(container.querySelectorAll('.file-icon')).toHaveLength(0)

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

  it('点击外层文件夹也触发预览', () => {
    const onPreview = vi.fn()
    const { container } = render(
      <FormProvider>
        <FormPreviewSlot onPreview={onPreview} />
      </FormProvider>,
    )

    fireEvent.click(container.querySelector('.folder-back') as Element)

    expect(onPreview).toHaveBeenCalledTimes(1)
  })

  it('拖拽需求表时将横向偏移限制在 240px 范围内', () => {
    const onPreview = vi.fn()

    render(
      <FormProvider>
        <FormPreviewSlot onPreview={onPreview} />
      </FormProvider>,
    )

    const folder = screen.getByRole('button', {
      name: '预览需求表',
    })
    const boundary = folder.parentElement as HTMLElement

    vi.spyOn(boundary, 'getBoundingClientRect').mockReturnValue({
      width: 240,
      height: 240,
    } as DOMRect)
    vi.spyOn(folder, 'getBoundingClientRect').mockReturnValue({
      width: 156,
      height: 126,
    } as DOMRect)

    fireEvent.mouseDown(folder, { clientX: 0, clientY: 0 })
    fireEvent.mouseMove(document, { clientX: 500, clientY: 42 })
    fireEvent.mouseUp(document)

    expect(folder).toHaveStyle({
      transform: 'translate3d(42px, 42px, 0) scale(.82)',
    })
    expect(onPreview).not.toHaveBeenCalled()
  })
})

describe('DeliverableSlot', () => {
  it('明确标注必填信息进度口径', () => {
    render(
      <FormProvider>
        <DeliverableSlot />
      </FormProvider>,
    )

    expect(screen.getByText(/必填信息 0\/24/)).toBeInTheDocument()
    expect(screen.getByText(/进度仅统计必填信息/)).toBeInTheDocument()
  })

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
