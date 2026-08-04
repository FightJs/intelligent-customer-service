import { useState } from 'react'
import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import { makeSummary, filledCount } from '../../utils/summary'
import { generateUrl } from '../../api/client'

const OVERVIEW_SECTION_IDS = ['customer', 'industry', 'venue', 'budget', 'goal'] as const

const DELIVERABLES = [
  { type: 'markdown', label: '场景设计说明', desc: 'Markdown 格式，含完整需求清单', icon: '📄' },
  { type: 'excel', label: '设备参数清单', desc: 'Excel 格式，现有 + 推荐设备', icon: '📊' },
  { type: 'word', label: '需求确认书', desc: 'Word 格式，可签字确认', icon: '📝' },
] as const

export default function DeliveryPanel() {
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
      const r = await generateUrl(type as 'markdown' | 'excel' | 'word', sessionId)
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
    <div className="h-full p-4 space-y-4 overflow-y-auto">
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
              className="w-full bg-surface rounded-card p-3 text-left transition-colors hover:bg-active-surface disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <div className="flex items-center gap-2">
                <span className="text-lg">{icon}</span>
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
  )
}
