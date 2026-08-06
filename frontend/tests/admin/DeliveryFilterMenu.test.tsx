/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import DeliveryFilterMenu from '../../src/components/admin/DeliveryFilterMenu'

const USERS = [
  { id: 1, username: 'admin', role: 'admin', created_at: '2026-08-04T00:00:00Z' },
  { id: 2, username: 'test', role: 'user', created_at: '2026-08-04T00:00:00Z' },
]

describe('DeliveryFilterMenu', () => {
  it('以二级面板展示交付物筛选分类', () => {
    render(<DeliveryFilterMenu users={USERS} value="" onChange={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: /全部交付物/ }))

    expect(screen.getByRole('menu', { name: '交付物筛选' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /交付状态/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /交付类型/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /所属用户/ })).toBeInTheDocument()
    expect(screen.getByText('该属性等待交付物接口提供后启用。')).toBeInTheDocument()
  })

  it('选择所属用户时回传用户 ID 并关闭菜单', () => {
    const onChange = vi.fn()
    render(<DeliveryFilterMenu users={USERS} value="" onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: /全部交付物/ }))
    fireEvent.click(screen.getByRole('button', { name: /所属用户/ }))
    fireEvent.click(screen.getByRole('menuitemradio', { name: /test/ }))

    expect(onChange).toHaveBeenCalledWith(2)
    expect(screen.queryByRole('menu', { name: '交付物筛选' })).not.toBeInTheDocument()
  })
})
