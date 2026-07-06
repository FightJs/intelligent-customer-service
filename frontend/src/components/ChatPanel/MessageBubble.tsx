interface Props {
  role: 'ai' | 'user'
  children: React.ReactNode
}

export default function MessageBubble({ role, children }: Props) {
  const isAi = role === 'ai'
  return (
    <div className={`flex ${isAi ? 'justify-start' : 'justify-end'} mb-3`}>
      <div
        className={`max-w-[80%] px-3.5 py-2.5 text-sm leading-relaxed bg-surface text-primary ${
          isAi ? 'rounded-bubble rounded-bl-[4px]' : 'rounded-bubble rounded-br-[4px] bg-accent text-white'
        }`}
      >
        {children}
      </div>
    </div>
  )
}
