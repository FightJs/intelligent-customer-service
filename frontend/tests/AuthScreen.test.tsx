import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AuthScreen from '../src/screens/AuthScreen'

const login = vi.fn()
const register = vi.fn()
const quickLogin = vi.fn()
const navigate = vi.fn()

vi.mock('react-router-dom', () => ({
  useNavigate: () => navigate,
}))

vi.mock('../src/state/AuthContext', () => ({
  useAuth: () => ({ login, register, quickLogin }),
}))

describe('AuthScreen visual structure', () => {
  beforeEach(() => {
    login.mockReset()
    register.mockReset()
    quickLogin.mockReset()
    navigate.mockReset()
  })

  it('uses the reference-style outer form container without changing the inner login fields', () => {
    render(<AuthScreen />)

    expect(screen.getByTestId('auth-form-container')).toBeInTheDocument()
    expect(screen.getByLabelText('用户名')).toBeInTheDocument()
    expect(screen.getByLabelText('密码')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '登录' })).toBeInTheDocument()
  })

  it('登录成功后进入工作台', async () => {
    login.mockResolvedValueOnce(undefined)
    render(<AuthScreen />)

    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'tester' } })
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'password' } })
    fireEvent.click(screen.getByRole('button', { name: '登录' }))

    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith('/workbench'))
  })

  it('快速使用后进入工作台', async () => {
    quickLogin.mockResolvedValueOnce(undefined)
    render(<AuthScreen />)

    fireEvent.click(screen.getByRole('button', { name: '快速使用' }))

    await vi.waitFor(() => {
      expect(quickLogin).toHaveBeenCalledTimes(1)
      expect(navigate).toHaveBeenCalledWith('/workbench')
    })
  })
})
