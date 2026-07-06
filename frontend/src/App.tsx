import { useState } from 'react'
import TopBar from './components/TopBar'
import ChatPanel from './components/ChatPanel/ChatPanel'
import ProgressPanel from './components/ProgressPanel/ProgressPanel'
import DeliveryPanel from './components/DeliveryPanel/DeliveryPanel'
import Sidebar from './components/Sidebar'
import ProgressRing from './components/ProgressRing'
import { FormProvider, useFormState } from './state/FormContext'
import { useTheme } from './state/theme'
import { SECTIONS } from './data/sections'
import { filledCount } from './utils/summary'

const PROGRESS_WIDTH_KEY = 'sidebar.progress.width'
const DELIVERY_WIDTH_KEY = 'sidebar.delivery.width'

function loadWidth(key: string, fallback: number) {
  const v = Number(localStorage.getItem(key))
  return Number.isFinite(v) && v > 0 ? v : fallback
}

function ProgressHeaderExtra() {
  const { state } = useFormState()
  let filled = 0, total = 0
  for (const def of SECTIONS) {
    const r = filledCount(state.sections[def.id], def)
    filled += r.filled
    total += r.total
  }
  const pct = total === 0 ? 0 : Math.round((filled / total) * 100)
  return (
    <span className="flex items-center gap-1 text-secondary text-xs">
      <ProgressRing pct={pct} />
      <span>{filled}/{total}</span>
    </span>
  )
}

export default function App() {
  const [resetKey, setResetKey] = useState(0)
  const [progressOpen, setProgressOpen] = useState(false)
  const [deliveryOpen, setDeliveryOpen] = useState(false)
  const [progressWidth, setProgressWidth] = useState(() => loadWidth(PROGRESS_WIDTH_KEY, 320))
  const [deliveryWidth, setDeliveryWidth] = useState(() => loadWidth(DELIVERY_WIDTH_KEY, 360))
  const { theme, toggleTheme } = useTheme()

  function handleProgressWidth(w: number) {
    setProgressWidth(w)
    localStorage.setItem(PROGRESS_WIDTH_KEY, String(w))
  }
  function handleDeliveryWidth(w: number) {
    setDeliveryWidth(w)
    localStorage.setItem(DELIVERY_WIDTH_KEY, String(w))
  }

  function handleReset() {
    setResetKey((k) => k + 1)
    setProgressOpen(false)
    setDeliveryOpen(false)
  }

  return (
    <FormProvider key={resetKey}>
      <div className="h-full flex flex-col bg-base text-primary">
        <TopBar
          theme={theme}
          onToggleTheme={toggleTheme}
          onReset={handleReset}
          progressOpen={progressOpen}
          deliveryOpen={deliveryOpen}
          onToggleProgress={() => setProgressOpen((o) => !o)}
          onToggleDelivery={() => setDeliveryOpen((o) => !o)}
        />
        <div className="relative flex-1 overflow-hidden">
          <div
            className="absolute inset-0 transition-[padding] duration-300"
            style={{
              paddingLeft: progressOpen ? progressWidth + 12 : 0,
              paddingRight: deliveryOpen ? deliveryWidth + 12 : 0,
            }}
          >
            <ChatPanel
              onComplete={() => setDeliveryOpen(true)}
            />
          </div>
          <Sidebar
            side="left"
            open={progressOpen}
            title="采集进度"
            width={progressWidth}
            onWidthChange={handleProgressWidth}
            headerExtra={<ProgressHeaderExtra />}
          >
            <ProgressPanel />
          </Sidebar>
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
