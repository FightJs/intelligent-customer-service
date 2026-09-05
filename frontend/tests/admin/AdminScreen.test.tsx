/// <reference types="@testing-library/jest-dom/vitest" />
import {
  act,
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
  generateUrlMock,
} = vi.hoisted(() => ({
  adminListUsersMock: vi.fn(),
  adminListDeliveriesMock: vi.fn(),
  adminGetDeliveryMock: vi.fn(),
  generateUrlMock: vi.fn(),
}))

vi.mock('../../src/api/client', () => ({
  adminListUsers: adminListUsersMock,
  adminListDeliveries: adminListDeliveriesMock,
  adminGetDelivery: adminGetDeliveryMock,
  generateUrl: generateUrlMock,
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
    generateUrlMock.mockReset()

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

  it('预加载两个 tab 并通过常驻面板切换，避免重新挂载闪屏', async () => {
    renderAdmin()

    await waitFor(() => {
      expect(adminListDeliveriesMock).toHaveBeenCalled()
      expect(adminListUsersMock).toHaveBeenCalled()
    })

    const deliveriesPanel = screen.getByTestId('admin-tab-deliveries')
    const usersPanel = screen.getByTestId('admin-tab-users')
    expect(deliveriesPanel).toHaveAttribute('data-active', 'true')
    expect(usersPanel).toHaveAttribute('data-active', 'false')

    fireEvent.click(screen.getByRole('button', { name: /用户/ }))
    expect(deliveriesPanel).toHaveAttribute('data-active', 'false')
    expect(usersPanel).toHaveAttribute('data-active', 'true')
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

  it.each([
    ['Excel', '下载设备参数清单'],
    ['Word', '下载需求确认书'],
  ])('下载%s时显示可关闭且五秒后自动消失的不支持提示，且不请求生成接口', async (documentLabel, downloadLabel) => {
    adminGetDeliveryMock.mockResolvedValue({
      id: 10,
      session_id: 'sess-1',
      user_id: 1,
      customer_name: '客户甲',
      created_at: '2026-08-04T00:00:00Z',
      owner_username: 'admin',
      markdown: '# 方案\n这是交付物正文',
    })
    const { unmount } = renderAdmin()
    await waitFor(() => expect(screen.getByText('客户甲')).toBeInTheDocument())
    fireEvent.click(screen.getByText('客户甲'))
    await waitFor(() => expect(screen.getByText('这是交付物正文')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: documentLabel }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: documentLabel })).toHaveAttribute('aria-pressed', 'true')
    })
    // 只控制提示消失的定时器，不替换 React 调度器依赖的时钟。
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    try {
      fireEvent.click(screen.getByRole('button', { name: downloadLabel }))
      expect(screen.getByRole('alert')).toHaveTextContent('暂不支持该类文档')
      expect(generateUrlMock).not.toHaveBeenCalled()

      act(() => vi.advanceTimersByTime(5000))
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()

      fireEvent.click(screen.getByRole('button', { name: downloadLabel }))
      fireEvent.click(screen.getByRole('button', { name: '关闭提示' }))
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
      expect(screen.getByRole('dialog')).toBeInTheDocument()

      fireEvent.click(screen.getByRole('button', { name: downloadLabel }))
      fireEvent.click(screen.getByRole('button', { name: '关闭' }))
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      expect(screen.getByRole('alert')).toBeInTheDocument()
    } finally {
      // 组件仍持有提示定时器，先卸载清理，再恢复真实计时器。
      unmount()
      vi.useRealTimers()
    }
  })

  it('用户 tab 渲染角色 badge（admin 高亮）', async () => {
    renderAdmin()
    fireEvent.click(screen.getByRole('button', { name: /用户/ }))
    await waitFor(() => expect(adminListUsersMock).toHaveBeenCalled())

    // 角色列的管理员渲染为 accent 样式的 badge
    const roleBadge = screen
      .getAllByText('管理员')
      .find((element) => element.classList.contains('text-accent'))
    expect(roleBadge).toBeDefined()
  })
})
