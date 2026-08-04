/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import Pagination from '../../src/components/admin/Pagination'

describe('Pagination', () => {
  it('显示总数与区间', () => {
    render(<Pagination page={1} size={10} total={25} onPageChange={vi.fn()} />)
    expect(screen.getByText(/共 25 条/)).toBeInTheDocument()
    expect(screen.getByText(/1-10/)).toBeInTheDocument()
    expect(screen.getByText('1 / 3')).toBeInTheDocument()
  })

  it('首页时上一页禁用', () => {
    render(<Pagination page={1} size={10} total={25} onPageChange={vi.fn()} />)
    expect(screen.getByLabelText('上一页')).toBeDisabled()
    expect(screen.getByLabelText('下一页')).not.toBeDisabled()
  })

  it('末页时下一页禁用', () => {
    render(<Pagination page={3} size={10} total={25} onPageChange={vi.fn()} />)
    expect(screen.getByLabelText('下一页')).toBeDisabled()
    expect(screen.getByLabelText('上一页')).not.toBeDisabled()
  })

  it('点击下一页回调 page+1', () => {
    const onChange = vi.fn()
    render(<Pagination page={1} size={10} total={25} onPageChange={onChange} />)
    fireEvent.click(screen.getByLabelText('下一页'))
    expect(onChange).toHaveBeenCalledWith(2)
  })

  it('空数据显示 0 条', () => {
    render(<Pagination page={1} size={10} total={0} onPageChange={vi.fn()} />)
    expect(screen.getByText(/共 0 条/)).toBeInTheDocument()
  })
})
