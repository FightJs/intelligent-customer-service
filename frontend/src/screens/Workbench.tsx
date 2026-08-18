import { useState } from 'react'
import TopBar from '../components/TopBar'
import AdminEntryButton from '../components/AdminEntryButton'
import ChatPanel from '../components/ChatPanel/ChatPanel'
import CameraPet from '../components/CameraPet/CameraPet'
import type { CameraPetActivity } from '../components/CameraPet/types'
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
  const [centerExpanded, setCenterExpanded] = useState(false)
  const [formPreviewOpen, setFormPreviewOpen] = useState(false)
  const [orderModalOpen, setOrderModalOpen] = useState(false)
  const [orderSent, setOrderSent] = useState(false)
  const [petActivity, setPetActivity] = useState<CameraPetActivity>('idle')
  const { theme, toggleTheme } = useTheme()
  const isGuest = (
    user?.role === 'guest'
  )

  function handleReset() {
    setResetKey((key) => key + 1)
    setCenterExpanded(false)
    setFormPreviewOpen(false)
    setOrderModalOpen(false)
    setOrderSent(false)
    setPetActivity('idle')
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
            deliveryOpen={centerExpanded}
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

            <section className="workbench-pet-zone">
              <CameraPet activity={petActivity} />
            </section>

            <section className="workbench-center-zone">
              <CenterCard
                expanded={centerExpanded}
                onToggleExpand={() => {
                  setCenterExpanded((expanded) => !expanded)
                }}
              >
                <ChatPanel onPetActivityChange={setPetActivity} />
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

              {!isGuest && (
                <DeliverableSlot
                  orderSent={orderSent}
                  onSendOrder={() => {
                    setOrderModalOpen(true)
                  }}
                />
              )}
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

          {!isGuest && orderModalOpen && (
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
