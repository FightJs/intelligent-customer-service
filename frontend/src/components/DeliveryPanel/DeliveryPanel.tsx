import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import { makeSummary } from '../../utils/summary'
import OrderForm from './OrderForm'

// 概要展示的 section（取关键章节，避免 10 个全列太长）
const OVERVIEW_SECTION_IDS = ['customer', 'industry', 'venue', 'budget', 'goal'] as const

const DELIVERABLES = ['场景设计说明', '设备参数清单', '多视角效果图', '向量化评分报告']

export default function DeliveryPanel() {
  const { state } = useFormState()

  return (
    <div className="h-full p-4 space-y-4">
      <section>
        <h3 className="text-secondary text-xs mb-2">方案概要</h3>
        <div className="grid grid-cols-2 gap-2">
          {OVERVIEW_SECTION_IDS.map((id) => {
            const sec = state.sections[id]
            const def = SECTIONS.find((s) => s.id === id)!
            return (
              <div key={id} className="bg-surface rounded-card p-2.5">
                <div className="text-muted text-[10px]">{def.title}</div>
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
