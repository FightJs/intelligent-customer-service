/// <reference types="@testing-library/jest-dom/vitest" />
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import Badge from '../../src/components/admin/Badge'

describe('Badge', () => {
  it('渲染子内容', () => {
    render(<Badge>admin</Badge>)
    expect(screen.getByText('admin')).toBeInTheDocument()
  })

  it('默认 variant 为 secondary', () => {
    const { container } = render(<Badge>user</Badge>)
    expect(container.firstChild).toHaveClass('text-secondary')
  })

  it('accent variant 应用对应类名', () => {
    const { container } = render(<Badge variant="accent">admin</Badge>)
    expect(container.firstChild).toHaveClass('text-accent')
  })
})
