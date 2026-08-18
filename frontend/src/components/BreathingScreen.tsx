interface BreathingScreenProps {
  onEnter: () => void
  leaving?: boolean
}

const features = [
  {
    index: '01',
    title: '智能需求采集',
    description:
      '通过自然对话逐步了解直播场景、预算、设备和交付要求。',
  },
  {
    index: '02',
    title: '实时信息整理',
    description:
      '沟通过程中同步整理客户信息，让需求更加完整清晰。',
  },
  {
    index: '03',
    title: '专业方案交付',
    description:
      '确认需求后提交订单，由团队统一查看并推进后续交付。',
  },
]

export default function BreathingScreen({
  onEnter,
  leaving = false,
}: BreathingScreenProps) {
  return (
    <main
      className={
        `breathing-screen${
          leaving ? ' is-leaving' : ''
        }`
      }
    >
      <section
        className="welcome-intro"
        aria-labelledby="welcome-title"
      >
        <p className="welcome-eyebrow">
          AI LIVESTREAM ASSISTANT
        </p>

        <h1
          id="welcome-title"
          className="welcome-title"
        >
          让直播间搭建需求
          <span>从沟通走向清晰交付</span>
        </h1>

        <p className="welcome-description">
          通过智能对话了解客户需求，实时整理直播间信息，
          帮助客户与交付团队更高效地完成需求确认。
        </p>

        <div className="welcome-features">
          {features.map((feature) => (
            <article
              key={feature.index}
              className="welcome-feature"
            >
              <span className="welcome-feature-index">
                {feature.index}
              </span>

              <div>
                <h2>{feature.title}</h2>
                <p>{feature.description}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <button
        type="button"
        className="breathing-entry"
        onClick={onEnter}
        disabled={leaving}
        aria-label="进入智能客服系统"
      >
        <div className="breathing-content">
          <div className="breathing-logo-wrap">
            <div
              data-breath-glow
              className="breathing-glow"
            />

            <svg
              width="72"
              height="72"
              viewBox="0 0 48 48"
              fill="none"
              className="relative z-10"
              aria-hidden="true"
              style={{
                filter:
                  'drop-shadow(0 0 12px rgb(var(--color-accent) / .42))',
              }}
            >
              <path
                d="M37 16.5A15 15 0 1 0 37 31.5"
                stroke="rgb(var(--color-accent))"
                strokeWidth="4.5"
                strokeLinecap="round"
              />
              <circle cx="24" cy="24" r="4.5" fill="rgb(var(--color-accent))" />
              <circle cx="39.5" cy="24" r="4" fill="rgb(var(--color-done))" />
            </svg>
          </div>

          <h2 className="breathing-title">
            智能客服工作台
          </h2>

          <p className="breathing-hint">
            点击进入系统
          </p>

          <p className="breathing-subtitle">
            登录或注册后，开始梳理您的直播间需求
          </p>
        </div>
      </button>
    </main>
  )
}
