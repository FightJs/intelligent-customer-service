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
    const link = screen.getByText('管理后台').closest('a')
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/admin')
  })

  it('使用 fixed 定位贴左下角', () => {
    render(
      <MemoryRouter>
        <AdminEntryButton />
      </MemoryRouter>,
    )
    const link = screen.getByText('管理后台').closest('a')!
    expect(link.className).toContain('fixed')
    expect(link.className).toContain('bottom-4')
    expect(link.className).toContain('left-4')
  })
})
