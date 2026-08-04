import { useState } from 'react'
import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import { makeSummary, filledCount } from '../../utils/summary'
import { generateUrl } from '../../api/client'


const OVERVIEW_SECTION_IDS = ['customer', 'industry', 'venue', 'budget', 'goal'] as const

const DELIVERABLES = [
  { type: 'markdown', label: '场景设计说明', desc: 'Markdown 格式，含完整需求清单', icon: 'pdf' },
  { type: 'excel', label: '设备参数清单', desc: 'Excel 格式，现有 + 推荐设备', icon: 'excel' },
  { type: 'word', label: '需求确认书', desc: 'Word 格式，可签字确认', icon: 'word' },
] as const

function FileTypeIcon({ type }: { type: (typeof DELIVERABLES)[number]['icon'] }) {
  const color = type === 'excel' ? '#22c55e' : type === 'word' ? '#3b82f6' : '#ef4444'

  return (
    <svg width="19" height="21" viewBox="0 0 20 22" fill="none" aria-hidden="true">
      <path d="M4 1.5h8l4 4V20a.5.5 0 0 1-.5.5h-11A.5.5 0 0 1 4 20V2a.5.5 0 0 1 .5-.5Z" stroke={color} strokeWidth="1.5" />
      <path d="M12 1.5V6h4" stroke={color} strokeWidth="1.5" />
      {type === 'excel' && <><path d="M6.5 10h7M6.5 13h7M6.5 16h7" stroke={color} strokeWidth="1.35" /><path d="M9.5 9v8M12 9v8" stroke={color} strokeWidth="1.35" /></>}
      {type === 'word' && <><path d="M6.5 10h7M6.5 13h7M6.5 16h4.5" stroke={color} strokeWidth="1.6" strokeLinecap="round" /></>}
      {type === 'pdf' && <><path d="M6.5 15.5c1.5-2.5 2.5-4.8 3-7 .7 2.3 1.6 4.2 4 5.4-2.8-.4-4.7.4-7 1.6Z" stroke={color} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /><path d="M6.5 18h7" stroke={color} strokeWidth="1.5" strokeLinecap="round" /></>}
    </svg>
  )
}

export default function DeliverableSlot() {
  const { state } = useFormState()
  const [downloading, setDownloading] = useState<string | null>(null)
  const [error, setError] = useState('')

  // 计算总进度
  let filled = 0, total = 0
  for (const def of SECTIONS) {
    const r = filledCount(state.sections[def.id], def)
    filled += r.filled
    total += r.total
  }
  const canGenerate = filled > 0

  async function handleDownload(type: string) {
    setError('')
    const sessionId = sessionStorage.getItem('ics_session_id')
    if (!sessionId) {
      setError('未找到会话，请先在对话框开始对话')
      return
    }
    setDownloading(type)
    try {
      const r = await generateUrl(
         type as 'markdown' | 'excel' | 'word',
         sessionId,
      )
      if (!r.ok) throw new Error(`生成失败：${r.status}`)
      const blob = await r.blob()
      // 从 Content-Disposition 取文件名
      const cd = r.headers.get('content-disposition') || ''
      const match = cd.match(/filename\*=UTF-8''(.+)/)
      const filename = match ? decodeURIComponent(match[1]) : `交付物.${type === 'markdown' ? 'md' : type === 'excel' ? 'xlsx' : 'docx'}`
      // 触发下载
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setDownloading(null)
    }
  }

  return (
    <section className="workbench-slot deliverable-slot">
      <div className="delivery-panel-scroll flex-1 min-h-0 overflow-y-auto space-y-4 pr-1">
        <section>
          <h3 className="text-secondary text-xs mb-2">方案概要</h3>
          <div className="grid grid-cols-2 gap-2">
            {OVERVIEW_SECTION_IDS.map((id) => {
              const sec = state.sections[id]
              const def = SECTIONS.find((s) => s.id === id)!
              return (
                <div key={id} className="rounded-card border border-idle/50 bg-surface p-2.5">
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
          <h3 className="text-secondary text-xs mb-2">
            交付物生成（{filled}/{total}）
          </h3>
          {!canGenerate && (
            <div className="text-muted text-[11px] mb-2">
              请先在左侧对话采集需求，填入信息后即可生成交付物
            </div>
          )}
          <div className="space-y-2">
            {DELIVERABLES.map(({ type, label, desc, icon }) => (
              <button
                key={type}
                type="button"
                onClick={() => handleDownload(type)}
                disabled={!canGenerate || downloading !== null}
                className="w-full rounded-card border border-idle/50 bg-surface p-3 text-left transition-colors hover:border-accent/60 hover:bg-active-surface disabled:cursor-not-allowed disabled:opacity-40"
              >
                <div className="flex items-center gap-2">
                  <span className="shrink-0"><FileTypeIcon type={icon} /></span>
                  <div className="flex-1 min-w-0">
                    <div className="text-primary text-xs font-medium">
                      {downloading === type ? '生成中…' : label}
                    </div>
                    <div className="text-muted text-[10px] truncate">{desc}</div>
                  </div>
                  <span className="text-muted text-xs">
                    {downloading === type ? '⏳' : '↓'}
                  </span>
                </div>
              </button>
            ))}
          </div>
          {error && (
            <div className="text-red-400 text-[11px] mt-2">{error}</div>
          )}
        </section>
      </div>
    </section>
  )
}
