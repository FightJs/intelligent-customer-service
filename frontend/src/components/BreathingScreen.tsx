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
              height="70"
              viewBox="0 0 48 46"
              fill="none"
              className="relative z-10"
              aria-hidden="true"
              style={{
                filter:
                  'drop-shadow(0 0 12px rgba(134,59,255,.7))',
              }}
            >
              <path
                fill="#863bff"
                d="M25.946 44.938c-.664.845-2.021.375-2.021-.698V33.937a2.26 2.26 0 0 0-2.262-2.262H10.287c-.92 0-1.456-1.04-.92-1.788l7.48-10.471c1.07-1.497 0-3.578-1.842-3.578H1.237c-.92 0-1.456-1.04-.92-1.788L10.013.474c.214-.297.556-.474.92-.474h28.894c.92 0 1.456 1.04.92 1.788l-7.48 10.471c-1.07 1.498 0 3.579 1.842 3.579h11.377c.943 0 1.473 1.088.89 1.83L25.947 44.94z"
              />
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