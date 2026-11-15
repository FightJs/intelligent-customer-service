import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import PagesDemo from '../src/PagesDemo'

it('标明示例数据并禁用没有后端的操作', () => {
  render(<PagesDemo />)
  expect(screen.getByText(/前端演示.*示例数据/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: '发送消息' })).toBeDisabled()
  expect(screen.getByRole('button', { name: /查看配置说明/ })).toBeDisabled()
})
