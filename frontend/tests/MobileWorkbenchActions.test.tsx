/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const formState = vi.hoisted(() => ({
  currentFieldId: 'brand',
  completed: false,
}))

vi.mock('../src/state/FormContext', () => ({
  useFormState: () => ({ state: formState }),
}))

import MobileWorkbenchActions from '../src/components/MobileWorkbenchActions'

function renderActions(role: string = 'user', overrides = {}) {
  const props: React.ComponentProps<typeof MobileWorkbenchActions> = {
    role,
    previewOpen: false,
    orderSent: false,
    onPreview: vi.fn(),
    onSendOrder: vi.fn(),
    ...overrides,
  }

  return {
    props,
    ...render(
      <MemoryRouter>
        <MobileWorkbenchActions {...props} />
      </MemoryRouter>,
    ),
  }
}

describe('MobileWorkbenchActions', () => {
  beforeEach(() => {
    formState.currentFieldId = 'brand'
    formState.completed = false
  })

  it('游客可打开需求表，但不显示订单入口', () => {
    const { props } = renderActions('guest')
    fireEvent.click(screen.getByRole('button', { name: '需求表' }))
    expect(props.onPreview).toHaveBeenCalledTimes(1)
    expect(screen.queryByText(/发送/)).not.toBeInTheDocument()
  })

  it('正式用户完成采集后可以发送订单', () => {
    formState.currentFieldId = ''
    const { props } = renderActions('user')
    const send = screen.getByRole('button', { name: '发送订单' })
    expect(send).toBeEnabled()
    fireEvent.click(send)
    expect(props.onSendOrder).toHaveBeenCalledTimes(1)
  })

  it('管理员可进入后台，订单已提交后显示完成状态', () => {
    formState.currentFieldId = ''
    formState.completed = true
    renderActions('admin')
    expect(screen.getByRole('link', { name: '管理后台' })).toHaveAttribute('href', '/admin')
    expect(screen.getByRole('button', { name: '已发送' })).toBeDisabled()
  })
})
