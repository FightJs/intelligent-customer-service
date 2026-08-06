/// <reference types="@testing-library/jest-dom/vitest" />
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import AdminEntryButton from '../src/components/AdminEntryButton'

describe('AdminEntryButton', () => {
  it('渲染管理后台入口并指向 /admin', () => {
    render(
      <MemoryRouter>
        <AdminEntryButton />
      </MemoryRouter>,
    )
    const link = screen.getByRole('link', { name: '后台管理' })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/admin')
  })

  it('使用 fixed 定位贴左下角', () => {
    render(
      <MemoryRouter>
        <AdminEntryButton />
      </MemoryRouter>,
    )
    const link = screen.getByRole('link', { name: '后台管理' })
    expect(link.className).toContain('fixed')
    expect(link.className).toContain('bottom-4')
    expect(link.className).toContain('left-4')
  })

  it('显示图标和后台管理文字，悬浮反馈不使用外框', () => {
    render(
      <MemoryRouter>
        <AdminEntryButton />
      </MemoryRouter>,
    )
    const link = screen.getByRole('link', { name: '后台管理' })
    expect(link).toHaveClass('admin-entry-button')
    expect(link).toHaveAttribute('data-icon-feedback', 'scale-brightness')
    expect(link).toHaveAttribute('title', '后台管理')
    expect(link).not.toHaveClass('border')
    expect(link).toHaveTextContent('后台管理')
    expect(link.querySelector('span')).toHaveClass('admin-entry-label')
  })
})
