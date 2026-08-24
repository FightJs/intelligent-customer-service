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
import {
  clearAllConversationSessions,
  getConversationSessionId,
} from '../utils/conversationSession'

export default function Workbench() {
  const { user, logout } = useAuth()
  const [resetKey, setResetKey] = useState(0)
  const [centerResetToken, setCenterResetToken] = useState(0)
  const [formPreviewOpen, setFormPreviewOpen] = useState(false)
  const [orderModalOpen, setOrderModalOpen] = useState(false)
  const [earlySubmit, setEarlySubmit] = useState(false)
  const [orderSent, setOrderSent] = useState(false)
  const [petActivity, setPetActivity] = useState<CameraPetActivity>('idle')
  const { theme, toggleTheme } = useTheme()
  const isGuest = (
    user?.role === 'guest'
  )

  function handleReset() {
    clearAllConversationSessions()
    setResetKey((key) => key + 1)
    setCenterResetToken((token) => token + 1)
    setFormPreviewOpen(false)
    setOrderModalOpen(false)
    setEarlySubmit(false)
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
            onRestoreCenterCard={() => {
              setCenterResetToken((token) => token + 1)
            }}
          />

          {user?.role === 'admin' && (
            <AdminEntryButton />
          )}

          <main
            className="workbench-stage"
          >
            <GridBackground />

            <section className="workbench-pet-zone">
              <CameraPet activity={petActivity} />
            </section>

            <section className="workbench-center-zone">
              <CenterCard
                resetToken={centerResetToken}
              >
                <ChatPanel
                  userId={user?.id}
                  userRole={user?.role}
                  onPetActivityChange={setPetActivity}
                  canFinishEarly={!isGuest}
                  conversationEnded={orderSent}
                  onFinishEarly={() => {
                    setEarlySubmit(true)
                    setOrderModalOpen(true)
                  }}
                />
              </CenterCard>
            </section>

            <aside
              className="workbench-slots"
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
                    setEarlySubmit(false)
                    setOrderModalOpen(true)
                  }}
                />
              )}
            </aside>
          </main>

          {formPreviewOpen && (
            <WordPreviewModal
              sessionId={user ? getConversationSessionId(user.id) ?? '' : ''}
              onClose={() => {
                setFormPreviewOpen(false)
              }}
            />
          )}

          {!isGuest && orderModalOpen && (
            <OrderConfirmationModal
              sessionId={user ? getConversationSessionId(user.id) ?? '' : ''}
              allowIncomplete={earlySubmit}
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
