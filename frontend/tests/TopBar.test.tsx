/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import TopBar from '../src/components/TopBar'
import type { Theme } from '../src/state/theme'

const DARK: Theme = 'dark'

function renderBar(overrides: Partial<React.ComponentProps<typeof TopBar>> = {}) {
  const props: React.ComponentProps<typeof TopBar> = {
    theme: DARK,
    onToggleTheme: vi.fn(),
    onReset: vi.fn(),
    onLogout: vi.fn(),
    role: 'user',
    progressVisible: true,
    deliveryOpen: false,
    onToggleProgress: vi.fn(),
    onToggleDelivery: vi.fn(),
    ...overrides,
  }
  return { props, ...render(<TopBar {...props} />) }
}

describe('TopBar', () => {
  it('头像环色按角色区分：admin=done(绿)', () => {
    const { container } = renderBar({ role: 'admin' })
    const avatar = container.querySelector('[role="button"][aria-label="管理员"]')
    expect(avatar?.className).toContain('ring-done')
  })

  it('头像环色按角色区分：user=accent(蓝)', () => {
    const { container } = renderBar({ role: 'user' })
    const avatar = container.querySelector('[role="button"][aria-label="普通用户"]')
    expect(avatar?.className).toContain('ring-accent')
  })

  it('右键头像弹出二级菜单', () => {
    renderBar()
    const avatar = screen.getByRole('button', { name: '普通用户' })
    fireEvent.contextMenu(avatar)
    expect(screen.getByRole('menu')).toBeInTheDocument()
    expect(screen.getByText('退出登录')).toBeInTheDocument()
    expect(screen.getByText(/切换到/)).toBeInTheDocument()
    expect(screen.getByText('重新开始')).toBeInTheDocument()
  })

  it('菜单项点击触发回调并关闭', () => {
    const onLogout = vi.fn()
    renderBar({ onLogout })
    fireEvent.contextMenu(screen.getByRole('button', { name: '普通用户' }))
    fireEvent.click(screen.getByText('退出登录'))
    expect(onLogout).toHaveBeenCalled()
    // 菜单关闭
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('ESC 关闭菜单', () => {
    renderBar()
    fireEvent.contextMenu(screen.getByRole('button', { name: '普通用户' }))
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('顶栏不再含主题切换/重新开始按钮（已移入菜单）', () => {
    renderBar()
    // 这些文案只在菜单里出现，顶栏 header 内不应直接渲染
    const header = screen.getByRole('banner')
    // header 内不应含「重新开始」「切换到浅色主题」这类文本按钮
    expect(header.textContent).not.toContain('重新开始')
  })
})
