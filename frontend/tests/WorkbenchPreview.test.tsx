import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import WorkbenchPreview from '../src/screens/WorkbenchPreview'

describe('WorkbenchPreview 主题切换', () => {
  it('切换方案时只更新工作台主题并保留当前结构', () => {
    render(<WorkbenchPreview />)

    expect(screen.getByRole('main', { name: '直播设备租赁工作台预览' })).toHaveClass('theme-jade')
    expect(screen.getByRole('button', { name: '青瓷运营台' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: '珊瑚工单台' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '工业调度台' }))

    expect(screen.getByRole('main', { name: '直播设备租赁工作台预览' })).toHaveClass('theme-carbon')
    expect(screen.getByRole('button', { name: '青瓷运营台' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('heading', { name: '确认机位与收音配置' })).toBeInTheDocument()
  })
})
