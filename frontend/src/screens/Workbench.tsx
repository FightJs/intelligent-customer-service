import { useState } from 'react'
import TopBar from '../components/TopBar'
import AdminEntryButton from '../components/AdminEntryButton'
import ChatPanel from '../components/ChatPanel/ChatPanel'
import ProgressCard from '../components/ProgressCard/ProgressCard'
import CenterCard from '../components/CenterCard/CenterCard'
import FormPreviewSlot from '../components/DeliveryPanel/FormPreviewSlot'
import DeliverableSlot from '../components/DeliveryPanel/DeliverableSlot'
import FormPreviewModal from '../components/DeliveryPanel/FormPreviewModal'
import OrderConfirmationModal from '../components/DeliveryPanel/OrderConfirmationModal'
import GridBackground from '../components/GridBackground'
import { ZStackProvider } from '../hooks/useZStack'
import { FormProvider } from '../state/FormContext'
import { useTheme } from '../state/theme'
import { useAuth } from '../state/AuthContext'

export default function Workbench() {
  const { user, logout } = useAuth()
  const [resetKey, setResetKey] = useState(0)
  const [progressVisible, setProgressVisible] = useState(true)
  const [centerExpanded, setCenterExpanded] = useState(false)
  const [formPreviewOpen, setFormPreviewOpen] = useState(false)
  const [orderModalOpen, setOrderModalOpen] = useState(false)
  const { theme, toggleTheme } = useTheme()

  function handleReset() {
    setResetKey((k) => k + 1)
    setProgressVisible(true)
    setCenterExpanded(false)
  }

  return (
    <ZStackProvider>
      <FormProvider key={resetKey}>
        <div className="h-full flex flex-col bg-base text-primary">
          <TopBar
            theme={theme}
            onToggleTheme={toggleTheme}
            onReset={handleReset}
            onLogout={logout}
            role={user?.role}
            progressVisible={progressVisible}
            deliveryOpen={centerExpanded}
            onToggleProgress={() => setProgressVisible((v) => !v)}
            onToggleDelivery={() => setCenterExpanded((v) => !v)}
          />
          {user?.role === 'admin' && <AdminEntryButton />}
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
                <FormPreviewSlot onPreview={() => setFormPreviewOpen(true)} />
              </section>
              <DeliverableSlot onSendOrder={() => setOrderModalOpen(true)} />
            </aside>
          </main>
          {formPreviewOpen && <FormPreviewModal onClose={() => setFormPreviewOpen(false)} />}
          {orderModalOpen && <OrderConfirmationModal onClose={() => setOrderModalOpen(false)} />}
        </div>
      </FormProvider>
    </ZStackProvider>
  )
}
