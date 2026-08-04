import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { X, FileText, FileSpreadsheet, FileType, Loader2 } from 'lucide-react'
import { generateUrl, type AdminDeliveryDetail } from '../../api/client'

type DocType = 'markdown' | 'excel' | 'word'

const DOC_BUTTONS: { type: DocType; label: string; icon: typeof FileText }[] = [
  { type: 'markdown', label: 'Markdown', icon: FileText },
  { type: 'excel', label: 'Excel', icon: FileSpreadsheet },
  { type: 'word', label: 'Word', icon: FileType },
]

interface DeliveryDrawerProps {
  detail: AdminDeliveryDetail | null
  loading?: boolean
  error?: string
  onClose: () => void
}

/** 右侧滑出抽屉：渲染交付物 Markdown 正文 + 下载。替代原 modal。 */
export default function DeliveryDrawer({ detail, loading, error, onClose }: DeliveryDrawerProps) {
  const [downloading, setDownloading] = useState<DocType | null>(null)

  // ESC 关闭
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function handleDownload(type: DocType) {
    if (!detail) return
    setDownloading(type)
    try {
      const r = await generateUrl(type, detail.session_id)
      if (!r.ok) throw new Error(`生成失败：${r.status}`)
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const name = detail.customer_name || '交付物'
      a.download = `${name}.${type === 'excel' ? 'xlsx' : type === 'word' ? 'docx' : 'md'}`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      // 错误静默：按钮已恢复，必要时可接 toast
    } finally {
      setDownloading(null)
    }
  }

  // 遮罩点击关闭，内容阻止冒泡
  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/50"
      onClick={onClose}
      role="presentation"
    >
      <aside
        className="flex h-full w-full max-w-2xl flex-col bg-base shadow-2xl ring-1 ring-idle/40"
        style={{ animation: 'admin-drawer-in .28s cubic-bezier(.22,1,.36,1)' }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {/* 标题栏 */}
        <div className="flex shrink-0 items-center justify-between border-b border-idle/40 px-5 py-3.5">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-primary">
              {detail?.customer_name || '交付物预览'}
            </h2>
            {detail && (
              <p className="text-xs text-muted">
                {detail.owner_username} · {new Date(detail.created_at).toLocaleString('zh-CN')}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1.5 text-muted hover:bg-active-surface hover:text-primary"
            aria-label="关闭"
          >
            <X size={18} />
          </button>
        </div>

        {/* 下载按钮组 */}
        {detail && (
          <div className="flex shrink-0 gap-2 border-b border-idle/40 px-5 py-2.5">
            {DOC_BUTTONS.map(({ type, label, icon: Icon }) => (
              <button
                key={type}
                type="button"
                disabled={downloading !== null}
                onClick={() => handleDownload(type)}
                className="inline-flex items-center gap-1.5 rounded-card border border-idle/50 bg-surface px-3 py-1.5 text-xs text-secondary hover:border-accent/60 hover:text-primary disabled:opacity-40"
              >
                {downloading === type ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <Icon size={13} />
                )}
                {label}
              </button>
            ))}
          </div>
        )}

        {/* 正文 */}
        <div className="flex-1 overflow-auto px-6 py-5">
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted">
              <Loader2 size={16} className="animate-spin" />
              加载中…
            </div>
          ) : error ? (
            <p className="text-sm text-red-400">{error}</p>
          ) : detail ? (
            <div className="prose-chat">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{detail.markdown}</ReactMarkdown>
            </div>
          ) : null}
        </div>
      </aside>
    </div>
  )
}
