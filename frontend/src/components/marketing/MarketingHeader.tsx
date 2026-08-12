import { Menu, X } from 'lucide-react'
import { marketingNavItems } from '../../data/marketingContent'

interface MarketingHeaderProps {
  menuOpen: boolean
  onMenuToggle: () => void
  onStartConsultation: () => void
  onNavigate: () => void
}

export default function MarketingHeader({
  menuOpen,
  onMenuToggle,
  onStartConsultation,
  onNavigate,
}: MarketingHeaderProps) {
  return (
    <header className="marketing-nav">
      <a className="marketing-brand" href="#top" onClick={onNavigate}>
        <span className="marketing-brand-mark" aria-hidden="true">↗</span>
        <span>智流 / AI CS</span>
      </a>

      <nav id="marketing-nav-links" className={`marketing-nav-links${menuOpen ? ' is-open' : ''}`} aria-label="介绍页导航">
        {marketingNavItems.map((item) => (
          <a key={item.href} href={item.href} onClick={onNavigate}>{item.label}</a>
        ))}
      </nav>

      <button className="marketing-nav-cta" type="button" onClick={onStartConsultation}>
        开始咨询 <span aria-hidden="true">↗</span>
      </button>

      <button
        className="marketing-menu-toggle"
        type="button"
        aria-label={menuOpen ? '关闭导航菜单' : '打开导航菜单'}
        aria-expanded={menuOpen}
        aria-controls="marketing-nav-links"
        onClick={onMenuToggle}
      >
        {menuOpen ? <X size={19} /> : <Menu size={19} />}
      </button>
    </header>
  )
}
