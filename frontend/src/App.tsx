import { useState } from 'react'
import TopBar from './components/TopBar'
import ChatPanel from './components/ChatPanel/ChatPanel'
import ProgressPanel from './components/ProgressPanel/ProgressPanel'
import DeliveryPanel from './components/DeliveryPanel/DeliveryPanel'
import { FormProvider } from './state/FormContext'

export default function App() {
  const [resetKey, setResetKey] = useState(0)
  const [showDelivery, setShowDelivery] = useState(false)

  return (
    <FormProvider key={resetKey}>
      <div className="h-full flex flex-col">
        <TopBar onReset={() => { setResetKey((k) => k + 1); setShowDelivery(false) }} />
        <div className="flex-1 flex overflow-hidden">
          <div className={`${showDelivery ? 'w-[20%]' : 'w-[30%]'} border-r border-idle transition-all duration-300`}>
            <ProgressPanel />
          </div>
          <div className={`${showDelivery ? 'w-[40%]' : 'w-[70%]'} border-r border-idle transition-all duration-300`}>
            <ChatPanel onComplete={() => setShowDelivery(true)} />
          </div>
          <div className={`bg-base overflow-hidden transition-all duration-300 ${showDelivery ? 'w-[40%]' : 'w-0'}`}>
            {showDelivery && <DeliveryPanel />}
          </div>
        </div>
      </div>
    </FormProvider>
  )
}
