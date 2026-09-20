import { BadgeCheck, BookOpen, Package, Ruler, ShoppingCart, Store, Wrench } from 'lucide-react'
import type {
  PlanContent,
  PlanEquipmentItem,
  PlanPackageTier,
} from '../api/pipeline'

const ROOM_SIZE_LABEL: Record<string, string> = {
  small: '小型间 10-20㎡',
  medium: '中型间 20-35㎡',
  large: '大型间 35-60㎡',
  xlarge: '超大间 60㎡+',
}

const SPEC_PRIORITY = ['功率', '色温', '显色', '传感器', '画幅', '焦段', '光圈', '接口', '分辨率', '承重', '尺寸', '备注']

function SpecList({ specs }: { specs?: Record<string, string | number | boolean> }) {
  if (!specs || Object.keys(specs).length === 0) return null
  const entries = Object.entries(specs).sort((a, b) => {
    const ia = SPEC_PRIORITY.indexOf(a[0])
    const ib = SPEC_PRIORITY.indexOf(b[0])
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib)
  })
  return (
    <dl className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted">
      {entries.map(([key, value]) => (
        <div key={key} className="flex items-baseline gap-1">
          <dt className="text-secondary">{key}</dt>
          <dd>{String(value)}</dd>
        </div>
      ))}
    </dl>
  )
}

function EquipmentRow({ item }: { item: PlanEquipmentItem }) {
  const title = [item.brand, item.model].filter(Boolean).join(' ') || item.name
  return (
    <div className="rounded-card border border-outline bg-recess px-3 py-2.5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] text-muted">{item.category}</span>
            {item.must_buy && !item.already_owned && (
              <span className="rounded-pill border border-accent/40 bg-accent/10 px-1.5 py-0.5 text-[10px] font-medium text-accent">
                必买/必租
              </span>
            )}
            {item.already_owned && (
              <span className="rounded-pill border border-done/40 bg-done/10 px-1.5 py-0.5 text-[10px] font-medium text-done">
                已有设备
              </span>
            )}
          </div>
          <div className="mt-0.5 text-[13px] font-semibold text-primary">{title}</div>
          {item.name && title !== item.name && (
            <div className="text-[11px] text-muted">{item.name}</div>
          )}
          {item.reason && <p className="mt-1 text-[11px] leading-4 text-secondary">{item.reason}</p>}
          <SpecList specs={item.specs} />
        </div>
        <div className="shrink-0 text-right text-[11px] text-muted">
          <div className="text-primary">×{item.qty ?? 1}</div>
          {item.purchase_price && <div className="mt-0.5">购 {item.purchase_price}</div>}
          {item.rent_monthly && item.rent_monthly !== '—' && <div>租 {item.rent_monthly}/月</div>}
        </div>
      </div>
    </div>
  )
}

function TierCard({ tier, primary }: { tier: PlanPackageTier; primary?: boolean }) {
  return (
    <div
      className={`rounded-card border p-3 ${
        primary ? 'border-accent/40 bg-brand-soft/40' : 'border-outline bg-recess'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-[13px] font-semibold text-primary">{tier.tier}</div>
          {tier.suitable && <p className="mt-0.5 text-[11px] text-muted">{tier.suitable}</p>}
        </div>
        <div className="text-right">
          <div className="text-sm font-semibold text-accent">{tier.total_range}</div>
          {tier.monthly_rent_range && (
            <div className="mt-0.5 text-[10px] text-muted">{tier.monthly_rent_range}</div>
          )}
        </div>
      </div>
      <ul className="mt-2 space-y-1">
        {(tier.items || []).map((item, i) => (
          <li key={`${item.name}-${i}`} className="flex items-baseline justify-between gap-2 text-[11px]">
            <span className="min-w-0 flex-1 text-secondary">
              {[item.brand, item.model].filter(Boolean).join(' ') || item.name}
            </span>
            <span className="shrink-0 text-muted">×{item.qty ?? 1}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function PlanDocumentPanel({ plan }: { plan: PlanContent }) {
  const layout = plan.layout || {}
  const equipment = plan.equipment_list || []
  const tiers = plan.package_tiers || []
  const mustBuy = plan.must_buy_list || equipment.filter((e) => e.must_buy && !e.already_owned).map((e) => [e.brand, e.model].filter(Boolean).join(' ') || e.name)
  const scale = (plan.meta?.layout_scale as string) || ''
  const areaBand = (plan.meta?.area_band as string) || ''
  const roomSize = (plan.meta?.room_size as string) || ''
  const scene = plan.scene_card || {}

  return (
    <section className="mb-5 space-y-5">
      <div>
        <div className="mb-2 flex items-center gap-2">
          <Package size={14} className="text-accent" aria-hidden="true" />
          <h3 className="text-[13px] font-semibold text-primary">直播间布局与规模</h3>
          <span className="text-[11px] text-muted">
            {ROOM_SIZE_LABEL[roomSize] || roomSize || '—'}
            {areaBand ? ` · ${areaBand}` : ''}
          </span>
        </div>
        {scale && (
          <div className="mb-2 rounded-card border border-outline bg-recess px-3 py-2 text-[12px] text-secondary">
            <Ruler size={12} className="mr-1 inline align-[-2px]" aria-hidden="true" />
            {scale}
          </div>
        )}
        <div className="space-y-1.5">
          {(layout.zones || []).map((zone) => (
            <div key={zone.name} className="flex flex-wrap gap-x-2 gap-y-0.5 rounded-card border border-outline bg-recess px-3 py-2 text-xs">
              <span className="font-medium text-secondary">{zone.name}</span>
              <span className="min-w-0 flex-1 text-muted">{zone.notes}</span>
            </div>
          ))}
        </div>
        <div className="mt-2 grid gap-1.5 sm:grid-cols-3">
          {layout.lighting_plan && (
            <div className="rounded-card border border-outline bg-recess px-2.5 py-2">
              <div className="text-[11px] font-medium text-secondary">布光</div>
              <p className="mt-0.5 text-[11px] leading-4 text-muted">{layout.lighting_plan}</p>
            </div>
          )}
          {layout.camera_plan && (
            <div className="rounded-card border border-outline bg-recess px-2.5 py-2">
              <div className="text-[11px] font-medium text-secondary">机位</div>
              <p className="mt-0.5 text-[11px] leading-4 text-muted">{layout.camera_plan}</p>
            </div>
          )}
          {layout.background_plan && (
            <div className="rounded-card border border-outline bg-recess px-2.5 py-2">
              <div className="text-[11px] font-medium text-secondary">背景</div>
              <p className="mt-0.5 text-[11px] leading-4 text-muted">{layout.background_plan}</p>
            </div>
          )}
        </div>
        {(scene.furniture?.length || scene.lighting_fixtures?.length) ? (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {[...(scene.lighting_fixtures || []), ...(scene.furniture || [])].map((tag) => (
              <span key={tag} className="rounded-pill border border-outline bg-surface px-2 py-0.5 text-[11px] text-secondary">
                {tag}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      {mustBuy.length > 0 && (
        <div>
          <div className="mb-2 flex items-center gap-2">
            <BadgeCheck size={14} className="text-done" aria-hidden="true" />
            <h3 className="text-[13px] font-semibold text-primary">必买 / 必租核心设备</h3>
            <span className="text-[11px] text-muted">{mustBuy.length} 项</span>
          </div>
          <div className="flex flex-wrap gap-1.5 rounded-card border border-done/30 bg-done/5 p-3">
            {mustBuy.map((name) => (
              <span key={name} className="rounded-pill border border-outline bg-surface px-2 py-0.5 text-[11px] text-primary">
                {name}
              </span>
            ))}
          </div>
        </div>
      )}

      <div>
        <div className="mb-2 flex items-center gap-2">
          <Wrench size={14} className="text-accent" aria-hidden="true" />
          <h3 className="text-[13px] font-semibold text-primary">设备清单（含型号与参数）</h3>
          <span className="text-[11px] text-muted">{equipment.length} 项</span>
        </div>
        <div className="space-y-1.5">
          {equipment.map((item, i) => (
            <EquipmentRow key={`${item.category}-${item.model || item.name}-${i}`} item={item} />
          ))}
        </div>
      </div>

      {tiers.length > 0 && (
        <div>
          <div className="mb-2 flex items-center gap-2">
            <ShoppingCart size={14} className="text-accent" aria-hidden="true" />
            <h3 className="text-[13px] font-semibold text-primary">推荐套餐（购买 / 租赁）</h3>
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            {tiers.map((tier, i) => (
              <TierCard key={tier.tier} tier={tier} primary={i === 1} />
            ))}
          </div>
        </div>
      )}

      {(plan.rental_channels || []).length > 0 && (
        <div>
          <div className="mb-2 flex items-center gap-2">
            <Store size={14} className="text-accent" aria-hidden="true" />
            <h3 className="text-[13px] font-semibold text-primary">设备租赁 / 采购渠道</h3>
          </div>
          <div className="space-y-1.5">
            {(plan.rental_channels || []).map((ch) => (
              <div key={ch.name} className="rounded-card border border-outline bg-recess px-3 py-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[12px] font-semibold text-primary">{ch.name}</span>
                  {(ch.categories || []).map((c) => (
                    <span key={c} className="rounded-pill border border-outline bg-surface px-1.5 py-0.5 text-[10px] text-muted">
                      {c}
                    </span>
                  ))}
                </div>
                {ch.note && <p className="mt-0.5 text-[11px] text-muted">{ch.note}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {(plan.vertical_notes || []).length > 0 && (
        <div>
          <div className="mb-2 flex items-center gap-2">
            <BookOpen size={14} className="text-accent" aria-hidden="true" />
            <h3 className="text-[13px] font-semibold text-primary">垂类搭建要点</h3>
          </div>
          <ul className="space-y-1.5 rounded-card border border-outline bg-recess p-3">
            {(plan.vertical_notes || []).map((note, i) => (
              <li key={i} className="flex gap-2 text-[12px] leading-5 text-secondary">
                <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent" aria-hidden="true" />
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {(plan.setup_steps || []).length > 0 && (
          <div>
            <h3 className="mb-2 text-[13px] font-semibold text-primary">搭建步骤</h3>
            <ol className="space-y-1.5">
              {(plan.setup_steps || []).map((step, i) => (
                <li key={i} className="rounded-card border border-outline bg-recess px-3 py-2 text-[12px] leading-5 text-secondary">
                  {step}
                </li>
              ))}
            </ol>
          </div>
        )}
        {(plan.risks || []).length > 0 && (
          <div>
            <h3 className="mb-2 text-[13px] font-semibold text-primary">风险与提醒</h3>
            <ul className="space-y-1.5">
              {(plan.risks || []).map((risk, i) => (
                <li key={i} className="rounded-card border border-warning/30 bg-warning/5 px-3 py-2 text-[12px] leading-5 text-secondary">
                  {risk}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  )
}
