import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../state/AuthContext'

type Mode = 'login' | 'register'

export default function AuthScreen() {
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState<Mode>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (mode === 'login') {
        await login(username, password)
      } else {
        await register(username, password)
      }
      navigate('/breathing')
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="h-full flex items-center justify-center bg-base text-primary px-4">
      <div
        data-testid="auth-form-container"
        className="auth-form-container w-full max-w-sm p-6 shadow-xl"
      >
        <div className="mb-6 text-center">
          <img src="/favicon.svg" alt="" className="mx-auto mb-3 h-10 w-10" />
          <h1 className="text-xl font-semibold">
            {mode === 'login' ? '登录' : '注册'}
          </h1>
          <p className="mt-2 text-sm text-secondary">
            {mode === 'login'
              ? '登录智能客服系统'
              : '创建账号开始使用'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="auth-username" className="mb-1.5 block text-sm text-secondary">
              用户名
            </label>
            <input
              id="auth-username"
              type="text"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value)
                if (error) setError('')
              }}
              autoComplete="username"
              autoFocus
              className="w-full rounded-bubble bg-base px-3.5 py-2.5 text-sm text-primary outline-none ring-1 ring-idle placeholder:text-muted focus:ring-accent"
              placeholder="至少 2 个字符"
            />
          </div>

          <div>
            <label htmlFor="auth-password" className="mb-1.5 block text-sm text-secondary">
              密码
            </label>
            <input
              id="auth-password"
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value)
                if (error) setError('')
              }}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              className="w-full rounded-bubble bg-base px-3.5 py-2.5 text-sm text-primary outline-none ring-1 ring-idle placeholder:text-muted focus:ring-accent"
              placeholder="至少 6 个字符"
            />
          </div>

          {error && (
            <p role="alert" className="text-sm text-red-400">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy || username.length < 2 || password.length < 6}
            className="w-full rounded-bubble bg-accent px-4 py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy ? '处理中…' : mode === 'login' ? '登录' : '注册'}
          </button>
        </form>

        <div className="mt-4 text-center text-xs text-muted">
          {mode === 'login' ? (
            <>
              没有账号？
              <button
                type="button"
                onClick={() => { setMode('register'); setError('') }}
                className="ml-1 text-accent hover:underline"
              >
                去注册
              </button>
            </>
          ) : (
            <>
              已有账号？
              <button
                type="button"
                onClick={() => { setMode('login'); setError('') }}
                className="ml-1 text-accent hover:underline"
              >
                去登录
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
