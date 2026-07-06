import ChatPanel from './components/ChatPanel/ChatPanel'
import { FormProvider } from './state/FormContext'

export default function App() {
  return (
    <FormProvider>
      <div className="h-full flex">
        <div className="w-[55%] border-r border-idle">
          <ChatPanel />
        </div>
        <div className="w-[45%]">
          <div className="p-4 text-muted text-sm">右侧仪表盘（待实现）</div>
        </div>
      </div>
    </FormProvider>
  )
}
