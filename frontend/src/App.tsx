import MessageBubble from './components/ChatPanel/MessageBubble'
import { FormProvider } from './state/FormContext'

export default function App() {
  return (
    <FormProvider>
      <div className="h-full p-8">
        <MessageBubble role="ai">测试气泡</MessageBubble>
        <MessageBubble role="user">用户消息</MessageBubble>
      </div>
    </FormProvider>
  )
}
