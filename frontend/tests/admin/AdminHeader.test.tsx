/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import AdminHeader from '../../src/components/admin/AdminHeader'

function LocationProbe() {
  return <output data-testid="location">{useLocation().pathname}</output>
}

describe('AdminHeader', () => {
  it('将返回工作台放在左侧并直接跳转到工作台路由', () => {
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <AdminHeader tab="deliveries" onTabChange={vi.fn()} />
        <LocationProbe />
      </MemoryRouter>,
    )

    const header = screen.getByRole('banner')
    const returnLink = screen.getByRole('link', { name: '返回工作台' })
    const title = screen.getByText('后台管理')

    expect(header.firstElementChild).toBe(returnLink)
    expect(header.lastElementChild).toBe(title)

    fireEvent.click(returnLink)
    expect(screen.getByTestId('location')).toHaveTextContent('/workbench')
  })
})
