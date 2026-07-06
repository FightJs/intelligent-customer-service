import { useFormState } from '../state/FormContext'
import { SECTIONS } from '../data/sections'
import { makeSummary } from '../utils/summary'

export default function ReportPreview({ onBack }: { onBack: () => void }) {
  const { state } = useFormState()
  const json = JSON.stringify(state.sections, null, 2)

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="flex justify-between items-center mb-5">
        <h2 className="text-primary text-lg font-semibold">需求采集报告</h2>
        <button
          type="button"
          onClick={onBack}
          className="text-sm bg-surface text-secondary px-3 py-1.5 rounded-pill hover:text-primary"
        >
          ‹ 返回修改
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-5">
        {SECTIONS.map((def) => (
          <div key={def.id} className="bg-surface rounded-card p-3">
            <div className="text-secondary text-xs mb-1">{def.title}</div>
            <div className="text-primary text-sm">{makeSummary(state.sections[def.id], def)}</div>
          </div>
        ))}
      </div>

      <div className="space-y-3">
        {[
          '场景设计说明',
          '设备参数清单',
          '多视角效果图',
          '向量化评分报告',
        ].map((title) => (
          <div key={title}>
            <div className="text-secondary text-xs mb-1">{title}</div>
            <div className="bg-surface rounded-card h-24 flex items-center justify-center text-muted text-xs">
              [ 后端 Agent 生成中 · 占位 ]
            </div>
          </div>
        ))}
      </div>

      <details className="mt-5">
        <summary className="text-secondary text-xs cursor-pointer">查看原始 JSON</summary>
        <pre className="bg-surface rounded-card p-3 text-[10px] text-secondary overflow-x-auto mt-2">{json}</pre>
      </details>
    </div>
  )
}
