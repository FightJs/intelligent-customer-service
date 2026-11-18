import { useState } from 'react'
import {
  CalendarDays,
  Check,
  ChevronRight,
  CircleAlert,
  Clock3,
  FileText,
  Headphones,
  Lightbulb,
  MessageSquareText,
  PackageCheck,
  RadioTower,
  Send,
  ShieldCheck,
  Video,
} from 'lucide-react'
import '../styles/workbenchPreview.css'

const EQUIPMENT = [
  { id: 'fx3', name: 'Sony FX3 直播套装', detail: '4K 60P · 24-70mm · 监看', price: '680', icon: Video },
  { id: 'audio', name: '双通道无线收音', detail: '两支领夹麦 · 充电盒', price: '180', icon: Headphones },
  { id: 'light', name: '双灯布光套装', detail: '主灯 · 柔光箱 · 灯架', price: '260', icon: Lightbulb },
]

const PROGRESS = [
  ['租赁用途', '品牌直播新品发布', 'complete'],
  ['直播时间', '8 月 16 日至 18 日', 'complete'],
  ['场地信息', '上海 · 80 平方米', 'complete'],
  ['设备清单', '正在确认机位与收音', 'active'],
  ['取还方式', '待确认', 'pending'],
] as const

type PaletteId = 'carbon' | 'jade' | 'atlassian' | 'govuk'

const PALETTES: Array<{ id: PaletteId; label: string; description: string }> = [
  { id: 'carbon', label: '工业调度台', description: '中性灰层级 + IBM 蓝，适合设备与库存' },
  { id: 'jade', label: '青瓷运营台', description: '浅青表面 + 深青操作，更柔和、更有行业感' },
  { id: 'atlassian', label: '珊瑚工单台', description: '暖珊瑚主操作，适合客服与订单协同' },
  { id: 'govuk', label: '信任服务台', description: '白底 + 可信蓝，状态和焦点边界最明确' },
]

export default function WorkbenchPreview({ demo = false }: { demo?: boolean }) {
  const [palette, setPalette] = useState<PaletteId>('jade')
  const [selectedEquipment, setSelectedEquipment] = useState('fx3')
  const [addedToOrder, setAddedToOrder] = useState(false)
  const [message, setMessage] = useState('')
  const [sentMessage, setSentMessage] = useState('')
  const [showDetails, setShowDetails] = useState(false)
  const selected = EQUIPMENT.find(({ id }) => id === selectedEquipment) ?? EQUIPMENT[0]

  return (
    <main className={`rental-preview theme-${palette}`} aria-label="直播设备租赁工作台预览">
      <header className="rental-preview-topbar">
        <div className="rental-preview-brand">
          <span className="rental-preview-brand-mark" aria-hidden="true"><RadioTower size={17} /></span>
          <div>
            <strong>直播设备租赁</strong>
            <span>工作台预览</span>
          </div>
        </div>

        <div className="rental-preview-top-status">
          <span><i className="status-dot is-live" />上海仓正常</span>
          <span className="rental-preview-divider" aria-hidden="true" />
          <span><Clock3 size={14} /> 今日 18:00 前可取</span>
        </div>

        <div className="rental-preview-user">
          <span>租赁顾问</span>
          <span className="rental-preview-avatar">L</span>
        </div>
      </header>

      <nav className="rental-preview-theme-toolbar" aria-label="预览配色方案">
        <span className="rental-preview-theme-label">预览方案</span>
        <div className="rental-preview-theme-options">
          {PALETTES.map(({ id, label }) => (
            <button
              className="rental-preview-theme-option"
              key={id}
              type="button"
              aria-pressed={palette === id}
              onClick={() => setPalette(id)}
            >
              <i className={`theme-option-swatch theme-option-swatch-${id}`} aria-hidden="true" />
              {label}
            </button>
          ))}
        </div>
        <span className="rental-preview-theme-description">
          {PALETTES.find(({ id }) => id === palette)?.description}
        </span>
      </nav>

      <div className="rental-preview-shell">
        <aside className="rental-preview-progress" aria-label="需求进度">
          <div className="rental-preview-panel-heading">
            <div>
              <span className="rental-preview-kicker">需求确认</span>
              <h1>订单要点</h1>
            </div>
            <span className="rental-preview-count">3 / 5</span>
          </div>

          <div className="rental-preview-progress-rail" aria-label="需求采集进度 60%">
            <span style={{ width: '60%' }} />
          </div>

          <div className="rental-preview-progress-list">
            {PROGRESS.map(([label, value, status]) => (
              <article className="rental-preview-progress-item" key={label}>
                <span className={`progress-status is-${status}`} aria-label={status === 'complete' ? '已完成' : status === 'active' ? '进行中' : '待确认'}>
                  {status === 'complete' ? <Check size={12} /> : status === 'active' ? <span /> : null}
                </span>
                <div>
                  <strong>{label}</strong>
                  <span>{value}</span>
                </div>
              </article>
            ))}
          </div>

          <div className="rental-preview-advisory">
            <ShieldCheck size={16} />
            <p>所有设备出库前均完成通电、收音与配件核验。</p>
          </div>
        </aside>

        <section className="rental-preview-conversation" aria-label="租赁顾问对话">
          <div className="rental-preview-conversation-header">
            <div>
              <span className="rental-preview-kicker">租赁顾问</span>
              <h2>确认机位与收音配置</h2>
            </div>
            <span className="rental-preview-chat-status"><i className="status-dot is-live" />正在服务</span>
          </div>

          <div className="rental-preview-messages">
            <article className="rental-preview-message is-advisor">
              <span className="rental-preview-message-avatar">L</span>
              <div>
                <p>已为你保留 8 月 16 日至 18 日的档期。此次直播是否需要双机位和主持人收音？</p>
                <time>10:28</time>
              </div>
            </article>
            <article className="rental-preview-message is-customer">
              <div>
                <p>需要一台主机位，主持人与嘉宾各一支无线麦，直播间约 80 平方米。</p>
                <time>10:29</time>
              </div>
            </article>
            <article className="rental-preview-suggestion">
              <MessageSquareText size={17} />
              <div>
                <strong>建议配置已更新</strong>
                <p>FX3 主机位、双通道无线收音与双灯布光套装适配当前场地。</p>
              </div>
              <ChevronRight size={16} aria-hidden="true" />
            </article>
            {demo && sentMessage && <>
              <article className="rental-preview-message is-customer"><div><p>{sentMessage}</p></div></article>
              <article className="rental-preview-message is-advisor">
                <span className="rental-preview-message-avatar">L</span>
                <div><p>模拟回复：已收到补充需求。可在右侧试选设备，核对示例租金。</p></div>
              </article>
            </>}
          </div>

          <form className="rental-preview-composer" onSubmit={(event) => {
            event.preventDefault()
            if (demo && message.trim()) {
              setSentMessage(message.trim())
              setMessage('')
            }
          }}>
            <label className="sr-only" htmlFor="rental-preview-input">输入租赁需求</label>
            <input value={demo ? message : undefined} onChange={demo ? event => setMessage(event.target.value) : undefined} maxLength={demo ? 200 : undefined} id="rental-preview-input" placeholder="补充设备、收音或取还需求" />
            <button disabled={demo && !message.trim()} type="submit" aria-label="发送消息"><Send size={16} /></button>
          </form>
        </section>

        <aside className="rental-preview-order" aria-label="租赁单">
          <div className="rental-preview-panel-heading">
            <div>
              <span className="rental-preview-kicker">本次租赁</span>
              <h2>设备与档期</h2>
            </div>
            <PackageCheck size={18} aria-hidden="true" />
          </div>

          <div className="rental-preview-date">
            <CalendarDays size={17} />
            <div><span>取用档期</span><strong>8 月 16 日至 18 日</strong></div>
            <span className="rental-preview-date-length">3 天</span>
          </div>

          <div className="rental-preview-equipment-list">
            {EQUIPMENT.map(({ id, name, detail, price, icon: Icon }) => (
              <button
                className={`rental-preview-equipment${selectedEquipment === id ? ' is-selected' : ''}`}
                key={id}
                type="button"
                aria-pressed={selectedEquipment === id}
                onClick={() => {
                  setSelectedEquipment(id)
                  setAddedToOrder(false)
                }}
              >
                <span className="rental-preview-equipment-icon"><Icon size={17} /></span>
                <span className="rental-preview-equipment-info"><strong>{name}</strong><small>{detail}</small></span>
                <span className="rental-preview-equipment-price">¥{price}<small>/天</small></span>
              </button>
            ))}
          </div>

          <div className="rental-preview-order-summary">
            <span>已选 {selected.name}</span>
            <strong>¥{Number(selected.price) * 3}</strong>
            <small>设备租金预估，不含运费与押金</small>
          </div>

          <div className="rental-preview-inventory-note"><CircleAlert size={15} />双通道无线收音库存仅剩 2 套</div>

          <button
            className={`rental-preview-primary-action${addedToOrder ? ' is-confirmed' : ''}`}
            type="button"
            onClick={() => setAddedToOrder(true)}
          >
            {addedToOrder ? <><Check size={16} />已加入租赁单</> : '加入租赁单'}
          </button>
          <button className="rental-preview-secondary-action" type="button" aria-expanded={demo ? showDetails : undefined} onClick={demo ? () => setShowDetails(value => !value) : undefined}><FileText size={15} />查看配置说明</button>
          {demo && showDetails && <div className="rental-preview-inventory-note">{selected.name} · {selected.detail}。示例配置及价格仅用于页面体验。</div>}
        </aside>
      </div>
    </main>
  )
}
