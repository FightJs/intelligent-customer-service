import { useEffect, useRef, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useAuth } from './state/AuthContext'
import AuthScreen from './screens/AuthScreen'
import Workbench from './screens/Workbench'
import AdminScreen from './screens/AdminScreen'
import BreathingScreen from './components/BreathingScreen'
import MarketingScreen from './screens/MarketingScreen'
import WorkbenchPreview from './screens/WorkbenchPreview'
import { useTheme } from './state/theme'

function ThemeRoot({ children }: { children: React.ReactNode }) {
  useTheme()
  return <>{children}</>
}

/** 受保护路由：未登录跳 /login，loading 时显示占位 */
function Protected({ children, adminOnly = false }: { children: React.ReactNode; adminOnly?: boolean }) {
  const { user, loading } = useAuth()
  if (loading) {
    return <div className="h-full flex items-center justify-center bg-base text-muted text-sm">加载中…</div>
  }
  if (!user) return <Navigate to="/login" replace />
  if (adminOnly && user.role !== 'admin') return <Navigate to="/" replace />
  return <>{children}</>
}

function GuestOnly({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return <div className="h-full flex items-center justify-center bg-base text-muted text-sm">加载中…</div>
  }
  if (user) return <Navigate to="/workbench" replace />
  return <>{children}</>
}

function BreathingRoute() {
  const navigate = useNavigate()
  const [leaving, setLeaving] = useState(false)
  const timerRef = useRef<number | null>(null)

  useEffect(() => () => {
    if (timerRef.current !== null) window.clearTimeout(timerRef.current)
  }, [])

  function enterLogin() {
    if (leaving) return
    setLeaving(true)
    timerRef.current = window.setTimeout(() => navigate('/login'), 440)
  }

  return <BreathingScreen onEnter={enterLogin} leaving={leaving} />
}

export default function App() {
  return (
    <ThemeRoot>
      <Routes>
      <Route path="/welcome" element={<BreathingRoute />} />
      <Route
        path="/"
        element={<MarketingScreen />}
      />
      <Route
        path="/login"
        element={<GuestOnly><AuthScreen /></GuestOnly>}
      />
      <Route path="/breathing" element={<Navigate to="/login" replace />} />
      <Route
        path="/workbench"
        element={
          <Protected>
            <Workbench />
          </Protected>
        }
      />
      <Route path="/workbench-preview" element={<WorkbenchPreview />} />
      <Route
        path="/admin"
        element={
          <Protected adminOnly>
            <AdminScreen />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/welcome" replace />} />
      </Routes>
    </ThemeRoot>
  )
}
