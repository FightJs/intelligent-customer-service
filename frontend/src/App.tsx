import LoginScreen from './components/LoginScreen'
import BreathingScreen from './components/BreathingScreen'
import { useState } from 'react'
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
  const [authenticated, setAuthenticated] = useState(
    () => localStorage.getItem(DEV_AUTH_STORAGE_KEY) === 'true',
  )
  const { theme, toggleTheme } = useTheme()

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

  if (!authenticated) {
    return <LoginScreen onLogin={handleLogin} />
  }

  if (!entered) {
    return <BreathingScreen onEnter={() => setEntered(true)} />
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
          <div
            className="relative flex-1 overflow-hidden grid"
            style={{ gridTemplateColumns: '120px 1fr' }}
          >
            {/* 底层网格背景：所有卡片浮在其上 */}
            <GridBackground />
            {/* 左：进度卡悬浮区占位格（进度卡是 fixed 悬浮，跨栏） */}
            <div className="relative" />
            {/* 中：中央卡（含 ChatPanel） */}
            <div className="relative overflow-hidden">
              <CenterCard expanded={centerExpanded} onToggleExpand={() => setCenterExpanded((v) => !v)}>
                <ChatPanel onComplete={() => setCenterExpanded(true)} />
              </CenterCard>
            </div>
          </div>
          {/* Loader 动效：固定右上，中央卡放大时隐藏 */}
          <div
            className="fixed top-8 -right-[94px] w-[449px] h-[529px] overflow-hidden transition-[opacity,transform] duration-300"
            style={centerExpanded ? { opacity: 0, transform: 'translateX(120%)' } : undefined}
          >
            <FormPreviewSlot />
          </div>
          {/* 交付物：固定悬浮卡片，中央卡放大时隐藏 */}
          <DeliverableSlot expanded={centerExpanded} />
          <ProgressCard visible={progressVisible} />
        </div>
      </FormProvider>
    </ZStackProvider>
  )
}
