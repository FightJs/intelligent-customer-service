import LoginScreen from './components/LoginScreen'
import { useState } from 'react'
import TopBar from './components/TopBar'
import ChatPanel from './components/ChatPanel/ChatPanel'
import ProgressCard from './components/ProgressCard/ProgressCard'
import DeliveryPanel from './components/DeliveryPanel/DeliveryPanel'
import Sidebar from './components/Sidebar'
import { FormProvider } from './state/FormContext'
import { useTheme } from './state/theme'

const DELIVERY_WIDTH_KEY = 'sidebar.delivery.width'
const DEV_AUTH_STORAGE_KEY = 'ics_dev_auth'

function loadWidth(key: string, fallback: number) {
  const v = Number(localStorage.getItem(key))
  return Number.isFinite(v) && v > 0 ? v : fallback
}

export default function App() {
  const [resetKey, setResetKey] = useState(0)
  const [progressVisible, setProgressVisible] = useState(true)
  const [deliveryOpen, setDeliveryOpen] = useState(false)
  const [authenticated, setAuthenticated] = useState(
    () => localStorage.getItem(DEV_AUTH_STORAGE_KEY) === 'true',
  )
  const [deliveryWidth, setDeliveryWidth] = useState(() => loadWidth(DELIVERY_WIDTH_KEY, 360))
  const { theme, toggleTheme } = useTheme()

  function handleDeliveryWidth(w: number) {
    setDeliveryWidth(w)
    localStorage.setItem(DELIVERY_WIDTH_KEY, String(w))
  }

  function handleReset() {
    setResetKey((k) => k + 1)
    setProgressVisible(true)
    setDeliveryOpen(false)
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

  return (
    <FormProvider key={resetKey}>
      <div className="h-full flex flex-col bg-base text-primary">
        <TopBar
          theme={theme}
          onToggleTheme={toggleTheme}
          onReset={handleReset}
          progressVisible={progressVisible}
          deliveryOpen={deliveryOpen}
          onToggleProgress={() => setProgressVisible((v) => !v)}
          onToggleDelivery={() => setDeliveryOpen((o) => !o)}
        />
        <div className="relative flex-1 overflow-hidden">
          <div
            className="absolute inset-0 transition-[padding] duration-300"
            style={{
              paddingLeft: 0,
              paddingRight: deliveryOpen ? deliveryWidth + 12 : 0,
            }}
          >
            <ChatPanel
              onComplete={() => setDeliveryOpen(true)}
            />
          </div>
          <ProgressCard visible={progressVisible} />
          <Sidebar
            side="right"
            open={deliveryOpen}
            title="交付物"
            width={deliveryWidth}
            onWidthChange={handleDeliveryWidth}
          >
            <DeliveryPanel />
          </Sidebar>
        </div>
      </div>
    </FormProvider>
  )
}
