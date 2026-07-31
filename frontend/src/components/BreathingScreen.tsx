interface BreathingScreenProps {
  onEnter: () => void
}

export default function BreathingScreen({ onEnter }: BreathingScreenProps) {
  return (
    <div
      onClick={onEnter}
      className="h-full flex flex-col items-center justify-center bg-base text-primary cursor-pointer select-none"
      role="button"
      tabIndex={0}
    >
      <div className="relative w-40 h-40 flex items-center justify-center">
        <div
          data-breath-glow
          className="absolute inset-0 rounded-full"
          style={{
            background:
              'radial-gradient(circle, rgba(134,59,255,.35) 0%, rgba(134,59,255,.1) 40%, transparent 70%)',
            animation: 'breath 2.8s ease-in-out infinite',
          }}
        />
        <svg
          width="72"
          height="70"
          viewBox="0 0 48 46"
          fill="none"
          className="relative z-10"
          style={{ filter: 'drop-shadow(0 0 12px rgba(134,59,255,.7))' }}
        >
          <path
            fill="#863bff"
            d="M25.946 44.938c-.664.845-2.021.375-2.021-.698V33.937a2.26 2.26 0 0 0-2.262-2.262H10.287c-.92 0-1.456-1.04-.92-1.788l7.48-10.471c1.07-1.497 0-3.578-1.842-3.578H1.237c-.92 0-1.456-1.04-.92-1.788L10.013.474c.214-.297.556-.474.92-.474h28.894c.92 0 1.456 1.04.92 1.788l-7.48 10.471c-1.07 1.498 0 3.579 1.842 3.579h11.377c.943 0 1.473 1.088.89 1.83L25.947 44.94z"
          />
        </svg>
      </div>
      <h1 className="mt-7 text-xl font-semibold">智能客服工作台</h1>
      <p className="mt-2 text-sm text-muted">点击进入系统</p>

      <style>{`
        @keyframes breath {
          0%,100% { transform: scale(0.92); opacity: 0.65; }
          50%     { transform: scale(1.12); opacity: 1; }
        }
      `}</style>
    </div>
  )
}
