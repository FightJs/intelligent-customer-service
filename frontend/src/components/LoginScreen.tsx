import { useState, type FormEvent } from 'react'

interface LoginScreenProps {
  onLogin: (key: string) => boolean
}

export default function LoginScreen({ onLogin }: LoginScreenProps) {
  const [key, setKey] = useState('')
  const [error, setError] = useState('')

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!onLogin(key)) {
      setError('密钥错误')
      return
    }

    setError('')
  }

  return (
    <div className="h-full flex items-center justify-center bg-base text-primary px-4">
      <div className="w-full max-w-sm rounded-card bg-surface p-6 shadow-xl ring-1 ring-idle">
        <div className="mb-6 text-center">
          <img
            src="/favicon.svg"
            alt=""
            className="mx-auto mb-3 h-10 w-10"
          />
          <h1 className="text-xl font-semibold">客户登录</h1>
          <p className="mt-2 text-sm text-secondary">
            请输入访问密钥进入智能客服系统
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="dev-key"
              className="mb-1.5 block text-sm text-secondary"
            >
              访问密钥
            </label>

            <input
              id="dev-key"
              type="password"
              value={key}
              onChange={(event) => {
                setKey(event.target.value)
                if (error) setError('')
              }}
              autoComplete="off"
              autoFocus
              className="w-full rounded-bubble bg-base px-3.5 py-2.5 text-sm text-primary outline-none ring-1 ring-idle placeholder:text-muted focus:ring-accent"
              placeholder="请输入访问密钥"
            />
          </div>

          {error && (
            <p role="alert" className="text-sm text-red-400">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={key === ''}
            className="w-full rounded-bubble bg-accent px-4 py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            进入系统
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-muted">
          当前为开发阶段访问验证
        </p>
      </div>
    </div>
  )
}