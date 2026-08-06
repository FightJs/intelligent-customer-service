import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AuthScreen from '../src/screens/AuthScreen'

const login = vi.fn()
const register = vi.fn()

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock('../src/state/AuthContext', () => ({
  useAuth: () => ({ login, register }),
}))

describe('AuthScreen visual structure', () => {
  beforeEach(() => {
    login.mockReset()
    register.mockReset()
  })

  it('uses the reference-style outer form container without changing the inner login fields', () => {
    render(<AuthScreen />)

    expect(screen.getByTestId('auth-form-container')).toBeInTheDocument()
    expect(screen.getByLabelText('用户名')).toBeInTheDocument()
    expect(screen.getByLabelText('密码')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '登录' })).toBeInTheDocument()
  })
})
