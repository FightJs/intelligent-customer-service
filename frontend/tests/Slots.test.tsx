/// <reference types="@testing-library/jest-dom/vitest" />
import { useEffect } from 'react'
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
import FormPreviewSlot from '../src/components/DeliveryPanel/FormPreviewSlot'
import DeliverableSlot from '../src/components/DeliveryPanel/DeliverableSlot'
import {
  FormProvider,
  useFormState,
} from '../src/state/FormContext'

const { generateUrlMock } = vi.hoisted(() => ({
  generateUrlMock: vi.fn(),
}))

vi.mock('../src/api/client', () => ({
  generateUrl: generateUrlMock,
}))

describe('FormPreviewSlot', () => {
  it('渲染需求表预览快照', () => {
    const { container } = render(
      <FormProvider>
        <FormPreviewSlot />
      </FormProvider>,
    )

    expect(
      screen.getByText('需求表预览'),
    ).toBeInTheDocument()
    expect(container.querySelector('.requirement-preview-row')).toBeInTheDocument()
  })

  it('不再渲染外部淡蓝色流光线条', () => {
    const { container } = render(
      <FormProvider>
        <FormPreviewSlot />
      </FormProvider>,
    )

    expect(
      container.querySelectorAll('.trace-flow'),
    ).toHaveLength(0)
  })

  it('点击需求表预览快照后触发完整预览', () => {
    const onPreview = vi.fn()
    render(
      <FormProvider>
        <FormPreviewSlot onPreview={onPreview} />
      </FormProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: '预览需求表' }))

    expect(onPreview).toHaveBeenCalledTimes(1)
  })
})

function FilledDeliverableSlot() {
  const { dispatch } = useFormState()

  useEffect(() => {
    dispatch({
      type: 'update_field',
      sectionId: 'customer',
      fieldId: 'brand',
      value: {
        type: 'text',
        value: '测试品牌',
      },
    })
  }, [dispatch])

  return <DeliverableSlot />
}

describe('DeliverableSlot', () => {
  beforeEach(() => {
    generateUrlMock.mockReset()
    sessionStorage.clear()
  })

  it('渲染交付物标题', () => {
    render(
      <FormProvider>
        <DeliverableSlot />
      </FormProvider>,
    )

    expect(
      screen.getAllByText(/交付物/).length,
    ).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: '发送订单' })).toBeInTheDocument()
  })

  it('点击发送订单按钮触发确认弹窗入口', () => {
    const onSendOrder = vi.fn()
    render(
      <FormProvider>
        <DeliverableSlot onSendOrder={onSendOrder} />
      </FormProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: '发送订单' }))

    expect(onSendOrder).toHaveBeenCalledTimes(1)
  })

  it('通过统一 API client 下载交付物', async () => {
    sessionStorage.setItem(
      'ics_session_id',
      'session-1',
    )

    generateUrlMock.mockResolvedValue({
      ok: false,
      status: 500,
    } as Response)

    render(
      <FormProvider>
        <FilledDeliverableSlot />
      </FormProvider>,
    )

    const button = screen.getByRole(
      'button',
      {
        name: /场景设计说明/,
      },
    )

    await waitFor(() => {
      expect(button).toBeEnabled()
    })

    fireEvent.click(button)

    await waitFor(() => {
      expect(
        generateUrlMock,
      ).toHaveBeenCalledWith(
        'markdown',
        'session-1',
      )
    })
  })

  it('交付物列表默认显示文件图标，悬浮后切换为下载图标', async () => {
    render(
      <FormProvider>
        <FilledDeliverableSlot />
      </FormProvider>,
    )

    const button = screen.getByRole('button', { name: /场景设计说明/ })

    expect(screen.queryByTestId('download-icon-markdown')).not.toBeInTheDocument()

    fireEvent.mouseEnter(button)

    await waitFor(() => {
      expect(screen.getByTestId('download-icon-markdown')).toBeInTheDocument()
    })
  })
})
