import ChatPanel from './components/ChatPanel/ChatPanel'
import Dashboard from './components/Dashboard/Dashboard'
import { FormProvider } from './state/FormContext'

export default function App() {
  return (
    <FormProvider>
      <div className="h-full flex">
        <div className="w-[55%] border-r border-idle">
          <ChatPanel />
        </div>
        <div className="w-[45%]">
          <Dashboard />
        </div>
      </div>
    </FormProvider>
  )
}
