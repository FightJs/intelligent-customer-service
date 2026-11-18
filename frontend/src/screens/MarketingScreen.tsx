import { useEffect, useRef, useState } from 'react'
import { isPagesDemo } from '../api/transport'
import { useNavigate } from 'react-router-dom'
import MarketingHeader from '../components/marketing/MarketingHeader'
import { CapabilitySection, DeliverablesSection, FaqSection, HeroWaterfall, ScenariosSection, ValueSection, WorkflowSection } from '../components/marketing/MarketingSections'
import '../styles/marketing.css'

export default function MarketingScreen() {
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const pageRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const root = pageRef.current
    if (!root) return

    const items = Array.from(root.querySelectorAll<HTMLElement>('.marketing-reveal'))
    if (!('IntersectionObserver' in window)) {
      items.forEach((item) => item.classList.add('is-visible'))
      return
    }
    let lastScrollTop = root.scrollTop
    const handleScroll = () => {
      const currentScrollTop = root.scrollTop
      root.dataset.scrollDirection = currentScrollTop > lastScrollTop ? 'down' : 'up'
      lastScrollTop = currentScrollTop
    }
    root.addEventListener('scroll', handleScroll, { passive: true })
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible')
        } else {
          entry.target.classList.remove('is-visible')
        }
      })
    }, { root, threshold: 0.16, rootMargin: '0px 0px -8% 0px' })

    items.forEach((item) => observer.observe(item))
    return () => {
      root.removeEventListener('scroll', handleScroll)
      observer.disconnect()
    }
  }, [])

  function startConsultation() {
    navigate('/login')
  }

  function closeMenu() {
    setMenuOpen(false)
  }

  return (
    <main className="marketing-page" id="top" ref={pageRef} onClick={isPagesDemo ? (event) => {
      const hash = (event.target as Element).closest('a')?.getAttribute('href')
      if (!hash?.startsWith('#')) return
      event.preventDefault()
      if (hash === '#top') pageRef.current?.scrollTo({ top: 0 })
      else document.getElementById(hash.slice(1))?.scrollIntoView({ block: 'start' })
    } : undefined}>
      <MarketingHeader
        menuOpen={menuOpen}
        onMenuToggle={() => setMenuOpen((open) => !open)}
        onStartConsultation={startConsultation}
        onNavigate={closeMenu}
      />

      <section className="marketing-hero">
        <div className="marketing-hero-copy marketing-reveal is-visible">
          <span className="marketing-overline">AI LIVESTREAM ASSISTANT / 2026</span>
          <h1>让每一条需求，<br /><span>汇成可执行的直播间。</span></h1>
          <p>从一句模糊的想法开始，AI 逐步追问、结构化并生成方案，让咨询不再停留在聊天记录里。</p>
          <div className="marketing-hero-actions">
            <button className="marketing-primary-cta" type="button" onClick={startConsultation}>开始咨询 <span aria-hidden="true">↗</span></button>
            <a className="marketing-text-link" href="#capabilities">查看需求瀑布 <span aria-hidden="true">↓</span></a>
          </div>
          <div className="marketing-hero-note"><span className="live-dot" /> 对话正在被整理为交付</div>
        </div>
        <HeroWaterfall />
      </section>

      <section className="marketing-intro-band">
        <span className="marketing-overline marketing-reveal">FROM CONVERSATION TO DELIVERY</span>
        <p className="marketing-intro-statement marketing-reveal reveal-delay-1">客户说出一堆零散的想法，<br /><strong>系统负责把它们安放到正确的位置。</strong></p>
      </section>

      <ValueSection />
      <CapabilitySection />
      <WorkflowSection />
      <DeliverablesSection />
      <ScenariosSection />
      <section className="marketing-before-after marketing-reveal" aria-labelledby="before-after-title">
        <div className="before-after-copy">
          <span className="marketing-overline">THE OUTPUT CHANGES EVERYTHING</span>
          <h2 id="before-after-title">同一段对话，<br /><em>交付前后是两种状态。</em></h2>
        </div>
        <div className="before-after-board">
          <div className="board-column board-before"><span>BEFORE</span><p>“大概想做得高级一点，预算再看看。”</p><i>信息未归档</i></div>
          <div className="board-divider" aria-hidden="true">↓</div>
          <div className="board-column board-after"><span>AFTER</span><p>风格：克制科技感<br />预算：8–12 万<br />节点：方案确认</p><i>14 个字段已确认</i></div>
        </div>
      </section>
      <FaqSection />

      <section className="marketing-final-cta">
        <div className="final-cta-waterfall" aria-hidden="true"><i /><i /><i /><i /><i /></div>
        <div className="marketing-reveal is-visible">
          <span className="marketing-overline">READY WHEN YOU ARE</span>
          <h2>把下一次咨询，<br /><em>直接变成下一步。</em></h2>
          <button className="marketing-primary-cta" type="button" onClick={startConsultation}>开始咨询 <span aria-hidden="true">↗</span></button>
        </div>
      </section>

      <footer className="marketing-footer">
        <span>智流 / AI CS</span>
        <span>直播间需求采集与交付工作台</span>
        <span>© 2026</span>
      </footer>
    </main>
  )
}
