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
  it('渲染 Loader 动效（含 SVG）', () => {
    const { container } = render(
      <FormPreviewSlot />,
    )

    expect(
      container.querySelector('svg'),
    ).toBeInTheDocument()
  })

  it('不再渲染外部淡蓝色流光线条', () => {
    const { container } = render(
      <FormPreviewSlot />,
    )

    expect(
      container.querySelectorAll('.trace-flow'),
    ).toHaveLength(0)
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
})
