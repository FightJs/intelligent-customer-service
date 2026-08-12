import type { CSSProperties } from 'react'
import { capabilitySteps, deliverables, faqs, scenarios, trustMetrics, workflowSteps } from '../../data/marketingContent'

export function HeroWaterfall() {
  const drops = Array.from({ length: 18 }, (_, index) => index)

  return (
    <div className="waterfall-hero-visual" data-testid="waterfall-hero" aria-hidden="true">
      <div className="waterfall-grid" />
      <div className="waterfall-columns">
        {[0, 1, 2, 3, 4].map((column) => (
          <div className="waterfall-column" key={column} style={{ '--column': column } as CSSProperties}>
            <span className="waterfall-column-line" />
            {drops.slice(column * 3, column * 3 + 8).map((drop, offset) => (
              <span
                className="waterfall-drop"
                key={drop}
                style={{ '--drop-delay': `${(offset * 0.62) + column * 0.23}s` } as CSSProperties}
              />
            ))}
          </div>
        ))}
      </div>
      <div className="waterfall-source-card">
        <span className="waterfall-card-kicker">客户表达 / LIVE INPUT</span>
        <strong>“想做一间有质感的直播间”</strong>
        <div className="waterfall-source-tags"><span>目标</span><span>空间</span><span>预算</span></div>
      </div>
      <div className="waterfall-field-stack">
        <span>空间尺寸 <b>24㎡</b></span>
        <span>预算区间 <b>8–12w</b></span>
        <span>交付节点 <b>已确认</b></span>
      </div>
      <div className="waterfall-output-card">
        <span className="waterfall-card-kicker">AI DELIVERY / 03</span>
        <strong>搭建方案</strong>
        <span>从对话下落，向交付汇聚。</span>
        <div className="waterfall-progress"><i /></div>
      </div>
      <span className="waterfall-orbit orbit-one" />
      <span className="waterfall-orbit orbit-two" />
    </div>
  )
}

export function CapabilitySection() {
  return (
    <section className="marketing-section capabilities-section" id="capabilities">
      <div className="marketing-section-heading marketing-reveal">
        <span className="marketing-overline">01 / CAPABILITIES</span>
        <h2>需求字段，方案逻辑，交付确认。</h2>
        <p>每一次问答都有归属。AI 不止记录，更会根据缺口主动追问，让团队在同一条信息流上工作。</p>
      </div>
      <div className="capability-waterfall" aria-label="三步需求瀑布">
        <div className="capability-spine" aria-hidden="true" />
        {capabilitySteps.map((step, index) => (
          <article className={`capability-card marketing-reveal reveal-delay-${index + 1}`} key={step.index}>
            <div className="capability-index">{step.index}</div>
            <div className="capability-card-copy">
              <h3>{step.title}</h3>
              <p>{step.description}</p>
              <div className="capability-fields">{step.fields.map((field) => <span key={field}>{field}</span>)}</div>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

export function ValueSection() {
  return (
    <section className="marketing-section value-section" id="value">
      <div className="value-heading marketing-reveal">
        <span className="marketing-overline">00 / WHY IT MATTERS</span>
        <h2>把反复确认，变成一次有方向的对话。</h2>
        <p>客户不需要先学会描述需求，团队也不必在聊天记录里反复找答案。系统让每一次追问都有目的，每一个结论都有去处。</p>
      </div>
      <div className="value-metric-grid">
        {trustMetrics.map((metric, index) => (
          <article className={`value-metric marketing-reveal reveal-delay-${index + 1}`} key={metric.value}>
            <strong>{metric.value}</strong>
            <span>{metric.label}</span>
            <i aria-hidden="true" />
          </article>
        ))}
      </div>
      <div className="value-contrast marketing-reveal reveal-delay-2">
        <div><span>没有智能整理时</span><strong>聊天记录越来越长</strong><p>信息散落在不同轮次，关键判断藏在上下文里。</p></div>
        <div className="contrast-arrow" aria-hidden="true">→</div>
        <div><span>有需求瀑布时</span><strong>交付路径越来越清晰</strong><p>字段、缺口和结果同时可见，下一步自然出现。</p></div>
      </div>
    </section>
  )
}

export function WorkflowSection() {
  return (
    <section className="marketing-section workflow-section" id="workflow">
      <div className="workflow-intro marketing-reveal">
        <span className="marketing-overline">02 / ORCHESTRATION</span>
        <h2>不是聊天记录，<br /><em>是可执行的判断。</em></h2>
        <p>从原话到字段，从字段到方案。每个节点都留下一份能被团队继续使用的上下文。</p>
      </div>
      <div className="workflow-track">
        {workflowSteps.map((step, index) => (
          <article className={`workflow-node marketing-reveal reveal-delay-${index + 1}`} key={step.label}>
            <span className="workflow-node-dot" aria-hidden="true" />
            <span className="workflow-node-label">{step.label}</span>
            <strong>{step.value}</strong>
          </article>
        ))}
      </div>
    </section>
  )
}

export function DeliverablesSection() {
  return (
    <section className="marketing-section deliverables-section" id="deliverables">
      <div className="marketing-section-heading marketing-reveal">
        <span className="marketing-overline">03 / DELIVERABLES</span>
        <h2>聊完之后，手里真的多了一份东西。</h2>
        <p>交付不是一句“收到”，而是三种可以直接推进下一步的结果。</p>
      </div>
      <div className="deliverable-grid">
        {deliverables.map((item, index) => (
          <article className={`deliverable-preview deliverable-${item.accent} marketing-reveal reveal-delay-${index + 1}`} key={item.title}>
            <span className="deliverable-type">{item.type}</span>
            <div className="deliverable-sheet" aria-hidden="true">
              <div className="sheet-topline"><i /><i /><i /></div>
              <div className="sheet-title-line" />
              <div className="sheet-lines"><i /><i /><i /><i /></div>
              <div className="sheet-chart"><i /><i /><i /><i /><i /></div>
            </div>
            <h3>{item.title}</h3>
            <p>{item.detail}</p>
            <span className="deliverable-arrow" aria-hidden="true">↗</span>
          </article>
        ))}
      </div>
    </section>
  )
}

export function ScenariosSection() {
  return (
    <section className="marketing-section scenarios-section" id="scenarios">
      <div className="marketing-section-heading marketing-reveal">
        <span className="marketing-overline">04 / SCENARIOS</span>
        <h2>每一种开场，<br />都能落到同一条交付线上。</h2>
      </div>
      <div className="scenario-list">
        {scenarios.map((scenario, index) => (
          <article className={`scenario-row marketing-reveal reveal-delay-${index + 1}`} key={scenario.index}>
            <span>{scenario.index}</span>
            <h3>{scenario.title}</h3>
            <p>{scenario.detail}</p>
            <span className="scenario-arrow" aria-hidden="true">↘</span>
          </article>
        ))}
      </div>
    </section>
  )
}

export function FaqSection() {
  return (
    <section className="marketing-section faq-section" id="faq">
      <div className="faq-heading marketing-reveal">
        <span className="marketing-overline">05 / FAQ</span>
        <h2>常见问题</h2>
        <p>先把第一次使用时最关心的几件事说清楚。</p>
      </div>
      <div className="faq-list">
        {faqs.map((faq, index) => (
          <details className={`faq-item marketing-reveal reveal-delay-${index + 1}`} key={faq.question}>
            <summary><span>{faq.question}</span><b aria-hidden="true">+</b></summary>
            <p>{faq.answer}</p>
          </details>
        ))}
      </div>
    </section>
  )
}
