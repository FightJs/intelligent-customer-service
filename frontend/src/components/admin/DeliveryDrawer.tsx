import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { X, FileText, FileSpreadsheet, FileType, Loader2, Download, Pencil, Trash2 } from 'lucide-react'
import { type AdminDeliveryDetail } from '../../api/client'

type DocType = 'markdown' | 'excel' | 'word'

const DOC_BUTTONS: { type: DocType; label: string; icon: typeof FileText }[] = [
  { type: 'markdown', label: 'Markdown', icon: FileText },
  { type: 'excel', label: 'Excel', icon: FileSpreadsheet },
  { type: 'word', label: 'Word', icon: FileType },
]

const PREVIEW_TITLES: Record<DocType, string> = {
  markdown: '场景设计说明',
  excel: '设备参数清单',
  word: '需求确认书',
}

interface DeliveryDrawerProps {
  detail: AdminDeliveryDetail | null
  loading?: boolean
  error?: string
  onClose: () => void
  onUnsupportedDocument: () => void
  onUpdated: (detail: AdminDeliveryDetail) => Promise<void>
  onDeleted: () => Promise<void>
}

/** 右侧滑出抽屉：渲染交付物 Markdown 正文 + 下载。替代原 modal。 */
export default function DeliveryDrawer({ detail, loading, error, onClose, onUnsupportedDocument, onUpdated, onDeleted }: DeliveryDrawerProps) {
  const [downloading, setDownloading] = useState<DocType | null>(null)
  const [previewType, setPreviewType] = useState<DocType>('markdown')
  const [editing, setEditing] = useState(false)
  const [draftName, setDraftName] = useState('')
  const [draftMarkdown, setDraftMarkdown] = useState('')
  const [saving, setSaving] = useState(false)
  const [actionError, setActionError] = useState('')
  const [isScrolling, setIsScrolling] = useState(false)
  const scrollTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    setPreviewType('markdown')
    setEditing(false)
    setDraftName(detail?.customer_name ?? '')
    setDraftMarkdown(detail?.markdown ?? '')
    setActionError('')
  }, [detail?.id, detail?.customer_name, detail?.markdown])

  useEffect(() => () => {
    if (scrollTimer.current !== null) clearTimeout(scrollTimer.current)
  }, [])

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
    if (type !== 'markdown') {
      onUnsupportedDocument()
      return
    }

    setDownloading(type)
    try {
      const blob = new Blob([detail.markdown], { type: 'text/markdown;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const name = detail.customer_name || '交付物'
      a.download = `${name}.md`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 0)
    } catch {
      onUnsupportedDocument()
    } finally {
      setDownloading(null)
    }
  }

  async function handleSave() {
    if (!detail || !draftMarkdown.trim()) return
    setSaving(true)
    setActionError('')
    try {
      await onUpdated({ ...detail, customer_name: draftName.trim() || null, markdown: draftMarkdown })
      setEditing(false)
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!detail || !window.confirm(`确认删除交付物“${detail.customer_name || '未命名'}”？`)) return
    setSaving(true)
    setActionError('')
    try {
      await onDeleted()
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setSaving(false)
    }
  }

  function handleContentScroll() {
    setIsScrolling(true)
    if (scrollTimer.current) clearTimeout(scrollTimer.current)
    scrollTimer.current = setTimeout(() => setIsScrolling(false), 700)
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

        {/* 文档预览切换与下载 */}
        {detail && (
          <div className="flex shrink-0 items-center gap-2 border-b border-idle/40 px-5 py-2.5">
            {DOC_BUTTONS.map(({ type, label, icon: Icon }) => (
              <button
                key={type}
                type="button"
                aria-pressed={previewType === type}
                onClick={() => setPreviewType(type)}
                className={`inline-flex items-center gap-1.5 rounded-card border px-3 py-1.5 text-xs transition-colors ${
                  previewType === type
                    ? 'border-accent/70 bg-active-surface text-primary'
                    : 'border-idle/50 bg-surface text-secondary hover:border-accent/60 hover:text-primary'
                }`}
              >
                <Icon size={13} />
                {label}
              </button>
            ))}
            <button
              type="button"
              disabled={downloading !== null}
              onClick={() => handleDownload(previewType)}
              className="ml-auto grid h-7 w-7 place-items-center rounded-card text-muted transition-colors hover:bg-active-surface hover:text-primary disabled:opacity-40"
              aria-label={`下载${PREVIEW_TITLES[previewType]}`}
            >
              {downloading === previewType ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
            </button>
            <button type="button" onClick={() => setEditing((current) => !current)} disabled={saving} className="grid h-7 w-7 place-items-center rounded-card text-muted transition-colors hover:bg-active-surface hover:text-primary disabled:opacity-40" aria-label={editing ? '取消编辑' : '编辑交付物'} title={editing ? '取消编辑' : '编辑交付物'}>
              <Pencil size={14} />
            </button>
            <button type="button" onClick={() => void handleDelete()} disabled={saving} className="grid h-7 w-7 place-items-center rounded-card text-muted transition-colors hover:bg-red-950 hover:text-red-300 disabled:opacity-40" aria-label="删除交付物" title="删除交付物">
              <Trash2 size={14} />
            </button>
          </div>
        )}

        {/* 正文 */}
        <div
          className={`delivery-drawer-scroll flex-1 overflow-auto px-6 py-5 ${isScrolling ? 'is-scrolling' : ''}`}
          onScroll={handleContentScroll}
        >
          {actionError && <p className="mb-4 text-sm text-red-400">{actionError}</p>}
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted">
              <Loader2 size={16} className="animate-spin" />
              加载中…
            </div>
          ) : error ? (
            <p className="text-sm text-red-400">{error}</p>
          ) : detail && editing ? (
            <div className="space-y-4">
              <label className="block text-xs text-secondary">客户名<input value={draftName} onChange={(event) => setDraftName(event.target.value)} className="mt-1.5 w-full rounded-card bg-surface px-3 py-2.5 text-sm text-primary outline-none ring-1 ring-idle focus:ring-accent" /></label>
              <label className="block text-xs text-secondary">Markdown 正文<textarea value={draftMarkdown} onChange={(event) => setDraftMarkdown(event.target.value)} rows={18} className="mt-1.5 w-full resize-y rounded-card bg-surface px-3 py-2.5 font-mono text-sm text-primary outline-none ring-1 ring-idle focus:ring-accent" /></label>
              <div className="flex justify-end gap-2"><button type="button" onClick={() => setEditing(false)} disabled={saving} className="rounded-card px-3 py-2 text-sm text-secondary hover:bg-active-surface">取消</button><button type="button" onClick={() => void handleSave()} disabled={saving || !draftMarkdown.trim()} className="rounded-card bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-blue-400 disabled:opacity-50">{saving ? '保存中…' : '保存修改'}</button></div>
            </div>
          ) : detail ? (
            <div className="prose-chat">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{getPreviewContent(detail, previewType)}</ReactMarkdown>
            </div>
          ) : null}
        </div>
      </aside>
    </div>
  )
}

function getPreviewContent(detail: AdminDeliveryDetail, type: DocType): string {
  if (type === 'markdown') return detail.markdown

  const name = detail.customer_name || '交付物'
  const title = type === 'excel' ? `${name}设备参数清单` : `${name}直播间搭建需求确认书`
  const note = type === 'excel'
    ? '以下为设备参数清单的内容预览，下载后可在 Excel 中查看完整表格。'
    : '以下为需求确认书的内容预览，下载后可在 Word 中签字确认。'
  return `# ${title}\n\n> ${note}\n\n---\n\n${detail.markdown}`
}
