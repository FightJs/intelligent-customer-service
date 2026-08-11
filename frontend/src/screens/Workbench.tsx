import { useState } from 'react'
import TopBar from '../components/TopBar'
import AdminEntryButton from '../components/AdminEntryButton'
import ChatPanel from '../components/ChatPanel/ChatPanel'
import ProgressCard from '../components/ProgressCard/ProgressCard'
import CenterCard from '../components/CenterCard/CenterCard'
import FormPreviewSlot from '../components/DeliveryPanel/FormPreviewSlot'
import WordPreviewModal from '../components/DeliveryPanel/WordPreviewModal'
import DeliverableSlot from '../components/DeliveryPanel/DeliverableSlot'
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
  const [orderSent, setOrderSent] = useState(false)
  const { theme, toggleTheme } = useTheme()

  function handleReset() {
    setResetKey((key) => key + 1)
    setProgressVisible(true)
    setCenterExpanded(false)
    setFormPreviewOpen(false)
    setOrderModalOpen(false)
    setOrderSent(false)
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
            onToggleProgress={() => {
              setProgressVisible((visible) => !visible)
            }}
            onToggleDelivery={() => {
              setCenterExpanded((expanded) => !expanded)
            }}
          />

          {user?.role === 'admin' && (
            <AdminEntryButton />
          )}

          <main
            className={
              `workbench-stage${
                centerExpanded
                  ? ' is-center-expanded'
                  : ''
              }`
            }
          >
            <GridBackground />

            <section className="workbench-progress-zone">
              <ProgressCard visible={progressVisible} />
            </section>

            <section className="workbench-center-zone">
              <CenterCard
                expanded={centerExpanded}
                onToggleExpand={() => {
                  setCenterExpanded((expanded) => !expanded)
                }}
              >
                <ChatPanel />
              </CenterCard>
            </section>

            <aside
              className="workbench-slots"
              aria-hidden={centerExpanded}
              inert={centerExpanded}
            >
              <section className="form-preview-slot">
                <FormPreviewSlot
                  isPreviewOpen={formPreviewOpen}
                  onPreview={() => {
                    setFormPreviewOpen(true)
                  }}
                />
              </section>

              <DeliverableSlot
                orderSent={orderSent}
                onSendOrder={() => {
                  setOrderModalOpen(true)
                }}
              />
            </aside>
          </main>

          {formPreviewOpen && (
            <WordPreviewModal
              sessionId={sessionStorage.getItem('ics_session_id') ?? ''}
              onClose={() => {
                setFormPreviewOpen(false)
              }}
            />
          )}

          {orderModalOpen && (
            <OrderConfirmationModal
              onClose={() => {
                setOrderModalOpen(false)
              }}
              onSent={() => {
                setOrderSent(true)
              }}
            />
          )}
        </div>
      </FormProvider>
    </ZStackProvider>
  )
}
