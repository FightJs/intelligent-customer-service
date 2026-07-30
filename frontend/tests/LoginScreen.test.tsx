/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import LoginScreen from '../src/components/LoginScreen'

describe('LoginScreen', () => {
  it('渲染密码输入框和登录按钮', () => {
    render(<LoginScreen onLogin={() => false} />)

    expect(screen.getByLabelText('访问密钥')).toHaveAttribute(
      'type',
      'password',
    )
    expect(
      screen.getByRole('button', { name: '进入系统' }),
    ).toBeInTheDocument()
  })

  it('错误密钥显示统一提示', () => {
    const onLogin = vi.fn(() => false)
    render(<LoginScreen onLogin={onLogin} />)

    fireEvent.change(screen.getByLabelText('访问密钥'), {
      target: { value: 'wrong-key' },
    })
    fireEvent.click(screen.getByRole('button', { name: '进入系统' }))

    expect(onLogin).toHaveBeenCalledWith('wrong-key')
    expect(screen.getByRole('alert')).toHaveTextContent('密钥错误')
  })

  it('正确密钥不显示错误', () => {
    const onLogin = vi.fn(() => true)
    render(<LoginScreen onLogin={onLogin} />)

    fireEvent.change(screen.getByLabelText('访问密钥'), {
      target: { value: 'dev-secret-2026' },
    })
    fireEvent.click(screen.getByRole('button', { name: '进入系统' }))

    expect(onLogin).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})