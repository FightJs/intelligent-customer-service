/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import DataTable, { type Column } from '../../src/components/admin/DataTable'

interface Row {
  id: number
  name: string
}

const ROWS: Row[] = [
  { id: 1, name: 'alice' },
  { id: 2, name: 'bob' },
]

const COLUMNS: Column<Row>[] = [
  { key: 'id', header: 'ID', sortable: true },
  { key: 'name', header: 'Name' },
]

describe('DataTable', () => {
  it('渲染表头与数据行', () => {
    render(
      <DataTable columns={COLUMNS} rows={ROWS} rowKey={(r) => r.id} />,
    )
    expect(screen.getByText('ID')).toBeInTheDocument()
    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('alice')).toBeInTheDocument()
    expect(screen.getByText('bob')).toBeInTheDocument()
  })

  it('空数据显示 empty 占位', () => {
    render(
      <DataTable columns={COLUMNS} rows={[]} rowKey={(r) => r.id} empty={<div>无数据</div>} />,
    )
    expect(screen.getByText('无数据')).toBeInTheDocument()
  })

  it('loading 时渲染骨架行（无数据文本）', () => {
    const { container } = render(
      <DataTable columns={COLUMNS} rows={[]} rowKey={(r) => r.id} loading skeletonRows={3} />,
    )
    // 骨架用 animate-pulse div
    expect(container.querySelectorAll('.animate-pulse')).toHaveLength(6) // 3 行 × 2 列
  })

  it('已有数据刷新时保留当前行，避免排序闪动', () => {
    const { container } = render(
      <DataTable columns={COLUMNS} rows={ROWS} rowKey={(r) => r.id} loading />,
    )

    expect(screen.getByText('alice')).toBeInTheDocument()
    expect(screen.getByText('bob')).toBeInTheDocument()
    expect(container.querySelectorAll('.animate-pulse')).toHaveLength(0)
  })

  it('点击可排序列头触发 onSortChange', () => {
    const onSortChange = vi.fn()
    render(
      <DataTable
        columns={COLUMNS}
        rows={ROWS}
        rowKey={(r) => r.id}
        sort={{ sort_by: 'id', order: 'desc' }}
        onSortChange={onSortChange}
      />,
    )
    fireEvent.click(screen.getByText('ID'))
    // 当前 id desc → 翻转为 asc
    expect(onSortChange).toHaveBeenCalledWith({ sort_by: 'id', order: 'asc' })
  })

  it('换列排序默认 desc', () => {
    const onSortChange = vi.fn()
    render(
      <DataTable
        columns={[...COLUMNS, { key: 'created_at', header: '时间', sortable: true }]}
        rows={ROWS}
        rowKey={(r) => r.id}
        sort={{ sort_by: 'id', order: 'desc' }}
        onSortChange={onSortChange}
      />,
    )
    fireEvent.click(screen.getByText('时间'))
    expect(onSortChange).toHaveBeenCalledWith({ sort_by: 'created_at', order: 'desc' })
  })

  it('行点击触发 onRowClick', () => {
    const onRowClick = vi.fn()
    render(
      <DataTable columns={COLUMNS} rows={ROWS} rowKey={(r) => r.id} onRowClick={onRowClick} />,
    )
    fireEvent.click(screen.getByText('alice'))
    expect(onRowClick).toHaveBeenCalledWith(ROWS[0])
  })
})
