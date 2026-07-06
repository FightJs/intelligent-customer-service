import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import { makeSummary } from '../../utils/summary'
import type { SectionId } from '../../types/schema'
import OrderForm from './OrderForm'

const OVERVIEW_SECTIONS: { id: SectionId; label: string }[] = [
  { id: 'customer', label: '客户' },
  { id: 'industry', label: '品类' },
  { id: 'venue', label: '面积' },
  { id: 'budget', label: '预算' },
  { id: 'goal', label: '交付时间' },
]

const DELIVERABLES = ['场景设计说明', '设备参数清单', '多视角效果图', '向量化评分报告']

export default function DeliveryPanel() {
  const { state } = useFormState()

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <section>
        <h3 className="text-secondary text-xs mb-2">方案概要</h3>
        <div className="grid grid-cols-2 gap-2">
          {OVERVIEW_SECTIONS.map(({ id, label }) => {
            const sec = state.sections[id]
            const def = SECTIONS.find((s) => s.id === id)!
            return (
              <div key={id} className="bg-surface rounded-card p-2.5">
                <div className="text-muted text-[10px]">{label}</div>
                <div className="text-primary text-xs truncate">
                  {makeSummary(sec, def)}
                </div>
              </div>
            )
          })}
        </div>
      </section>

      <section>
        <h3 className="text-secondary text-xs mb-2">交付物</h3>
        <div className="space-y-2">
          {DELIVERABLES.map((title) => (
            <div key={title}>
              <div className="text-muted text-[11px] mb-1">{title}</div>
              <div className="bg-surface rounded-card h-16 flex items-center justify-center text-muted text-xs">
                [ Agent 生成中 · 占位 ]
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <OrderForm />
      </section>
    </div>
  )
}
