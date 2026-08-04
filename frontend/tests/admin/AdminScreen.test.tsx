/// <reference types="@testing-library/jest-dom/vitest" />
import {
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// hoisted mocks：admin API 全部 mock
const {
  adminListUsersMock,
  adminListDeliveriesMock,
  adminGetDeliveryMock,
} = vi.hoisted(() => ({
  adminListUsersMock: vi.fn(),
  adminListDeliveriesMock: vi.fn(),
  adminGetDeliveryMock: vi.fn(),
}))

vi.mock('../../src/api/client', () => ({
  adminListUsers: adminListUsersMock,
  adminListDeliveries: adminListDeliveriesMock,
  adminGetDelivery: adminGetDeliveryMock,
  generateUrl: vi.fn(),
}))

import AdminScreen from '../../src/screens/AdminScreen'

function renderAdmin() {
  return render(
    <MemoryRouter>
      <AdminScreen />
    </MemoryRouter>,
  )
}

describe('AdminScreen', () => {
  beforeEach(() => {
    adminListUsersMock.mockReset()
    adminListDeliveriesMock.mockReset()
    adminGetDeliveryMock.mockReset()

    adminListUsersMock.mockResolvedValue({
      items: [{ id: 1, username: 'admin', role: 'admin', created_at: '2026-08-04T00:00:00Z' }],
      total: 1,
      page: 1,
      size: 20,
    })
    adminListDeliveriesMock.mockResolvedValue({
      items: [
        {
          id: 10,
          session_id: 'sess-1',
          user_id: 1,
          customer_name: '客户甲',
          created_at: '2026-08-04T00:00:00Z',
          owner_username: 'admin',
        },
      ],
      total: 1,
      page: 1,
      size: 10,
    })
  })

  it('默认展示交付物 tab 并加载数据', async () => {
    renderAdmin()
    await waitFor(() => {
      expect(screen.getByText('客户甲')).toBeInTheDocument()
    })
    expect(adminListDeliveriesMock).toHaveBeenCalled()
  })

  it('切换到用户 tab 加载用户列表', async () => {
    renderAdmin()
    await waitFor(() => expect(adminListDeliveriesMock).toHaveBeenCalled())

    fireEvent.click(screen.getByRole('button', { name: /用户/ }))
    await waitFor(() => {
      expect(adminListUsersMock).toHaveBeenCalled()
    })
  })

  it('搜索触发后端请求并回到第 1 页', async () => {
    adminListDeliveriesMock.mockClear()
    renderAdmin()
    await waitFor(() => expect(adminListDeliveriesMock).toHaveBeenCalled())

    const callsBefore = adminListDeliveriesMock.mock.calls.length
    const input = screen.getByPlaceholderText(/搜索客户名或用户名/)
    fireEvent.change(input, { target: { value: '甲' } })

    // 防抖后触发
    await waitFor(() => {
      expect(adminListDeliveriesMock.mock.calls.length).toBeGreaterThan(callsBefore)
    })
    const lastCall = adminListDeliveriesMock.mock.calls.at(-1)?.[0]
    expect(lastCall?.search).toBe('甲')
    expect(lastCall?.page).toBe(1)
  })

  it('点击交付物行打开抽屉预览', async () => {
    adminGetDeliveryMock.mockResolvedValue({
      id: 10,
      session_id: 'sess-1',
      user_id: 1,
      customer_name: '客户甲',
      created_at: '2026-08-04T00:00:00Z',
      owner_username: 'admin',
      markdown: '# 方案\n这是交付物正文',
    })

    renderAdmin()
    await waitFor(() => expect(screen.getByText('客户甲')).toBeInTheDocument())

    fireEvent.click(screen.getByText('客户甲'))
    await waitFor(() => {
      expect(adminGetDeliveryMock).toHaveBeenCalledWith(10)
    })
    // 抽屉渲染 markdown（标题 + 正文）
    await waitFor(() => {
      expect(screen.getByText('这是交付物正文')).toBeInTheDocument()
    })
  })

  it('用户 tab 渲染角色 badge（admin 高亮）', async () => {
    renderAdmin()
    fireEvent.click(screen.getByRole('button', { name: /用户/ }))
    await waitFor(() => expect(adminListUsersMock).toHaveBeenCalled())

    // role 列的 admin 渲染为带 accent 类的 badge
    const badges = screen.getAllByText('admin')
    const roleBadge = badges.find((el) => el.closest('span')?.className.includes('text-accent'))
    expect(roleBadge).toBeDefined()
  })
})
