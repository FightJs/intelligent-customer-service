import { useState } from 'react'
import TopBar from './components/TopBar'
import ChatPanel from './components/ChatPanel/ChatPanel'
import Dashboard from './components/Dashboard/Dashboard'
import ReportPreview from './components/ReportPreview'
import { FormProvider } from './state/FormContext'

export default function App() {
  const [resetKey, setResetKey] = useState(0)
  const [showReport, setShowReport] = useState(false)

  return (
    <FormProvider key={resetKey}>
      <div className="h-full flex flex-col">
        <TopBar onReset={() => { setResetKey((k) => k + 1); setShowReport(false) }} />
        {showReport ? (
          <ReportPreview onBack={() => setShowReport(false)} />
        ) : (
          <div className="flex-1 flex overflow-hidden">
            <div className="w-[55%] border-r border-idle">
              <ChatPanel />
            </div>
            <div className="w-[45%]">
              <Dashboard onGenerate={() => setShowReport(true)} />
            </div>
          </div>
        )}
      </div>
    </FormProvider>
  )
}
