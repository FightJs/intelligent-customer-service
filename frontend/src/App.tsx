import LoginScreen from './components/LoginScreen'
import BreathingScreen from './components/BreathingScreen'
import { useState, useRef, useEffect } from 'react'
import TopBar from './components/TopBar'
import ChatPanel from './components/ChatPanel/ChatPanel'
import ProgressCard from './components/ProgressCard/ProgressCard'
import CenterCard from './components/CenterCard/CenterCard'
import FormPreviewSlot from './components/DeliveryPanel/FormPreviewSlot'
import DeliverableSlot from './components/DeliveryPanel/DeliverableSlot'
import GridBackground from './components/GridBackground'
import { ZStackProvider } from './hooks/useZStack'
import { FormProvider } from './state/FormContext'
import { useTheme } from './state/theme'

const DEV_AUTH_STORAGE_KEY = 'ics_dev_auth'

export default function App() {
  const [resetKey, setResetKey] = useState(0)
  const [progressVisible, setProgressVisible] = useState(true)
  const [centerExpanded, setCenterExpanded] = useState(false)
  const [entered, setEntered] = useState(false)
  const [entering, setEntering] = useState(false)
  const [authenticated, setAuthenticated] = useState(
    () => localStorage.getItem(DEV_AUTH_STORAGE_KEY) === 'true',
  )
  const { theme, toggleTheme } = useTheme()
  const enterTimer = useRef<number | null>(null)

  function handleReset() {
    setResetKey((k) => k + 1)
    setProgressVisible(true)
    setCenterExpanded(false)
  }

  function handleLogin(key: string): boolean {
    if (key !== import.meta.env.VITE_DEV_KEY) {
      return false
    }

    localStorage.setItem(DEV_AUTH_STORAGE_KEY, 'true')
    setAuthenticated(true)
    return true
  }

  function enterWorkbench() {
    if (entering) return
    setEntering(true)
    enterTimer.current = window.setTimeout(() => setEntered(true), 440)
  }

  // 卸载时清理进入工作台的定时器，避免对已卸载组件 setState
  useEffect(() => {
    return () => {
      if (enterTimer.current !== null) window.clearTimeout(enterTimer.current)
    }
  }, [])

  if (!authenticated) {
    return <LoginScreen onLogin={handleLogin} />
  }

  if (!entered) {
    return <BreathingScreen onEnter={enterWorkbench} leaving={entering} />
  }

  return (
    <ZStackProvider>
      <FormProvider key={resetKey}>
        <div className="h-full flex flex-col bg-base text-primary">
          <TopBar
            theme={theme}
            onToggleTheme={toggleTheme}
            onReset={handleReset}
            progressVisible={progressVisible}
            deliveryOpen={centerExpanded}
            onToggleProgress={() => setProgressVisible((v) => !v)}
            onToggleDelivery={() => setCenterExpanded((v) => !v)}
          />
          <main className={`workbench-stage${centerExpanded ? ' is-center-expanded' : ''}`}>
            <GridBackground />
            <section className="workbench-progress-zone">
              <ProgressCard visible={progressVisible} />
            </section>
            <section className="workbench-center-zone">
              <CenterCard expanded={centerExpanded} onToggleExpand={() => setCenterExpanded((v) => !v)}>
                <ChatPanel onComplete={() => setCenterExpanded(true)} />
              </CenterCard>
            </section>
            <aside className="workbench-slots" aria-hidden={centerExpanded} inert={centerExpanded}>
              <section className="form-preview-slot">
                <FormPreviewSlot />
              </section>
              <DeliverableSlot />
            </aside>
          </main>
        </div>
      </FormProvider>
    </ZStackProvider>
  )
}
