import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import {
  login as apiLogin,
  register as apiRegister,
  guestLogin as apiGuestLogin,
  getMe,
  setAuth,
  clearAuth,
  getToken,
  USER_KEY,
  authStorage,
  type AuthUser,
} from '../api/client'
import { clearAllConversationSessions } from '../utils/conversationSession'

interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  login: (
    username: string,
    password: string,
  ) => Promise<void>
  register: (
    username: string,
    password: string,
  ) => Promise<void>
  quickLogin: () => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function loadUserFromStorage(): AuthUser | null {
  const raw = authStorage().getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthUser
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(loadUserFromStorage)
  const [loading, setLoading] = useState(() => getToken() !== null && loadUserFromStorage() === null)

  // 启动时若有 token 但无 user 缓存，调 /auth/me 校验并取 user
  useEffect(() => {
    if (!loading) return
    if (!getToken()) {
      setLoading(false)
      return
    }
    getMe()
      .then((u) => {
        setAuth(getToken()!, u)
        setUser(u)
      })
      .catch(() => {
        clearAuth()
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [loading])

  const login = useCallback(async (username: string, password: string) => {
    const { token, user: u } = await apiLogin(username, password)
    clearAllConversationSessions()
    setAuth(token, u)
    setUser(u)
  }, [])

  const register = useCallback(async (username: string, password: string) => {
    const { token, user: u } = await apiRegister(username, password)
    clearAllConversationSessions()
    setAuth(token, u)
    setUser(u)
  }, [])

  const quickLogin = useCallback(
    async () => {
      const {
        token,
        user: guest,
      } = await apiGuestLogin()

      clearAllConversationSessions()
      setAuth(
        token,
        guest,
      )

      setUser(guest)
    },
    [],
  )

  const logout = useCallback(() => {
    clearAllConversationSessions()
    clearAuth()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        quickLogin,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth 必须在 AuthProvider 内使用')
  return ctx
}
