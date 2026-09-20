import { useEffect, useMemo, useRef, useState } from 'react'
import { Database, FileUp, RefreshCw, Trash2 } from 'lucide-react'
import Badge from '../../components/admin/Badge'
import DataTable, { type Column } from '../../components/admin/DataTable'
import EmptyState from '../../components/admin/EmptyState'
import SearchInput from '../../components/admin/SearchInput'
import StatCard from '../../components/admin/StatCard'
import {
  CATEGORY_COLLECTION,
  CATEGORY_LABEL,
  formatNow,
  KB_STATUS_META,
  MOCK_KNOWLEDGE,
  type KnowledgeCategory,
  type KnowledgeDoc,
  type KnowledgeStatus,
} from '../../data/mockKnowledge'

const COLUMNS: Column<KnowledgeDoc>[] = [
  {
    key: 'filename',
    header: '文件名',
  },
  {
    key: 'category',
    header: '分类',
    render: (d) => CATEGORY_LABEL[d.category],
  },
  {
    key: 'status',
    header: '状态',
    render: (d) => {
      const meta = KB_STATUS_META[d.status]
      return <Badge variant={meta.badge}>{meta.label}</Badge>
    },
  },
  {
    key: 'chunks',
    header: 'Chunks',
    render: (d) => (d.chunks ? d.chunks : <span className="text-muted">—</span>),
  },
  {
    key: 'updatedAt',
    header: '更新时间',
    render: (d) => <span className="text-muted">{d.updatedAt}</span>,
  },
]

/** 后台知识库 Tab：上传 PDF → 向量化状态 → 文档管理 */
export default function KnowledgeTab() {
  const [docs, setDocs] = useState<KnowledgeDoc[]>(MOCK_KNOWLEDGE)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<KnowledgeStatus | ''>('')
  const [categoryFilter, setCategoryFilter] = useState<KnowledgeCategory | ''>('')
  const [uploadCategory, setUploadCategory] = useState<KnowledgeCategory>('vertical')
  const [dragover, setDragover] = useState(false)
  const [selected, setSelected] = useState<KnowledgeDoc | null>(null)
  const [toast, setToast] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!selected) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setSelected(null)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [selected])

  const stats = useMemo(() => {
    const total = docs.length
    const ready = docs.filter((d) => d.status === 'ready').length
    const embedding = docs.filter((d) => d.status === 'embedding').length
    const failed = docs.filter((d) => d.status === 'failed').length
    return { total, ready, embedding, failed }
  }, [docs])

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase()
    return docs.filter((d) => {
      if (q && !d.filename.toLowerCase().includes(q)) return false
      if (statusFilter && d.status !== statusFilter) return false
      if (categoryFilter && d.category !== categoryFilter) return false
      return true
    })
  }, [docs, search, statusFilter, categoryFilter])

  function notify(message: string) {
    setToast(message)
    window.setTimeout(() => setToast(''), 2600)
  }

  function ingest(filename: string) {
    if (!filename.toLowerCase().endsWith('.pdf')) {
      notify('仅支持 PDF 文件')
      return
    }
    const id = `kb_${Date.now()}`
    const created: KnowledgeDoc = {
      id,
      filename,
      category: uploadCategory,
      status: 'pending',
      chunks: 0,
      updatedAt: formatNow(),
      note: '已上传，等待切块与向量化',
    }
    setDocs((prev) => [created, ...prev])
    notify(`「${filename}」已加入向量化队列`)

    window.setTimeout(() => {
      setDocs((prev) =>
        prev.map((d) =>
          d.id === id && d.status === 'pending'
            ? { ...d, status: 'embedding' as const, updatedAt: formatNow(), note: '切块完成，正在写入 Milvus' }
            : d,
        ),
      )
    }, 900)
    window.setTimeout(() => {
      setDocs((prev) =>
        prev.map((d) => {
          if (d.id !== id || d.status !== 'embedding') return d
          const chunks = 8 + Math.floor(Math.random() * 40)
          return {
            ...d,
            status: 'ready' as const,
            chunks,
            updatedAt: formatNow(),
            note: `已写入 ${CATEGORY_COLLECTION[d.category]}，${chunks} chunks`,
          }
        }),
      )
      notify(`「${filename}」向量化完成`)
    }, 2600)
  }

  function reembed(doc: KnowledgeDoc) {
    setDocs((prev) =>
      prev.map((d) =>
        d.id === doc.id
          ? { ...d, status: 'embedding' as const, updatedAt: formatNow(), note: '重新提交向量化' }
          : d,
      ),
    )
    notify('已重新提交向量化')
    window.setTimeout(() => {
      setDocs((prev) =>
        prev.map((d) =>
          d.id === doc.id && d.status === 'embedding'
            ? { ...d, status: 'ready' as const, chunks: d.chunks || 18, updatedAt: formatNow() }
            : d,
        ),
      )
    }, 2000)
  }

  function remove(doc: KnowledgeDoc) {
    if (!window.confirm(`删除「${doc.filename}」？将从向量库移除全部 chunk。`)) return
    setDocs((prev) => prev.filter((d) => d.id !== doc.id))
    setSelected((cur) => (cur?.id === doc.id ? null : cur))
    notify('文档已删除')
  }

  const actionColumn: Column<KnowledgeDoc> = {
    key: 'actions',
    header: '操作',
    className: 'text-right',
    render: (d) => (
      <div className="flex justify-end gap-1.5">
        <button
          type="button"
          className="rounded-card border border-idle bg-surface px-2 py-1 text-xs text-primary hover:bg-active-surface"
          onClick={(e) => {
            e.stopPropagation()
            setSelected(d)
          }}
        >
          详情
        </button>
        {d.status === 'failed' && (
          <button
            type="button"
            className="rounded-card border border-idle bg-surface px-2 py-1 text-xs text-primary hover:bg-active-surface"
            onClick={(e) => {
              e.stopPropagation()
              reembed(d)
            }}
          >
            重试
          </button>
        )}
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-card bg-danger px-2 py-1 text-xs text-white hover:brightness-95"
          onClick={(e) => {
            e.stopPropagation()
            remove(d)
          }}
        >
          <Trash2 size={12} aria-hidden="true" />
          删除
        </button>
      </div>
    ),
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
        <StatCard label="文档总数" value={stats.total} icon={<Database size={16} />} />
        <StatCard label="就绪" value={stats.ready} />
        <StatCard label="向量化中" value={stats.embedding} />
        <StatCard label="失败" value={stats.failed} />
      </div>

      <div
        className={`rounded-card border border-dashed p-4 transition ${
          dragover ? 'border-accent bg-active-surface' : 'border-idle bg-surface'
        }`}
        onDragOver={(e) => {
          e.preventDefault()
          setDragover(true)
        }}
        onDragLeave={() => setDragover(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragover(false)
          const file = e.dataTransfer.files?.[0]
          if (file) ingest(file.name)
        }}
      >
        <div className="flex flex-wrap items-start gap-4">
          <div className="min-w-0 flex-1">
            <h3 className="text-[13px] font-semibold text-primary">上传知识库 PDF</h3>
            <p className="mt-1 text-xs text-muted">
              拖拽文件到此处，或点击选择。支持设备参数、搭建方案、垂类知识文档；入库后自动切块并向量化到 Milvus。
            </p>
            <div className="mt-2.5 flex flex-wrap items-center gap-2">
              <select
                className="h-8 rounded-card border border-idle bg-surface px-2.5 text-xs text-primary focus:border-accent focus:outline-none"
                value={uploadCategory}
                onChange={(e) => setUploadCategory(e.target.value as KnowledgeCategory)}
                aria-label="知识分类"
              >
                <option value="equipment">设备参数</option>
                <option value="scheme">搭建方案</option>
                <option value="vertical">垂类知识</option>
              </select>
              <button
                type="button"
                className="inline-flex items-center gap-1.5 rounded-card bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-strong"
                onClick={() => fileRef.current?.click()}
              >
                <FileUp size={13} aria-hidden="true" />
                选择 PDF
              </button>
              <input
                ref={fileRef}
                type="file"
                accept="application/pdf,.pdf"
                hidden
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) ingest(file.name)
                  e.target.value = ''
                }}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <SearchInput
          value={search}
          onChange={(v) => setSearch(v)}
          placeholder="搜索文件名…"
        />
        <select
          className="h-8 rounded-card border border-idle bg-surface px-2.5 text-xs text-primary focus:border-accent focus:outline-none"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as KnowledgeStatus | '')}
          aria-label="状态筛选"
        >
          <option value="">全部状态</option>
          <option value="ready">就绪</option>
          <option value="embedding">向量化中</option>
          <option value="pending">待处理</option>
          <option value="failed">失败</option>
        </select>
        <select
          className="h-8 rounded-card border border-idle bg-surface px-2.5 text-xs text-primary focus:border-accent focus:outline-none"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value as KnowledgeCategory | '')}
          aria-label="分类筛选"
        >
          <option value="">全部分类</option>
          <option value="equipment">设备参数</option>
          <option value="scheme">搭建方案</option>
          <option value="vertical">垂类知识</option>
        </select>
      </div>

      <DataTable
        columns={[...COLUMNS, actionColumn]}
        rows={rows}
        rowKey={(d) => d.id}
        onRowClick={(d) => setSelected(d)}
        empty={
          <EmptyState
            title="没有匹配的文档"
            description="调整筛选条件，或上传新的 PDF 入向量库"
            icon={<Database size={32} strokeWidth={1.5} />}
          />
        }
      />

      {selected && (
        <>
          <div
            className="fixed inset-0 z-40 bg-primary/25"
            onClick={() => setSelected(null)}
            aria-hidden="true"
          />
          <aside
            className="fixed inset-y-0 right-0 z-50 w-[min(400px,92vw)] overflow-auto border-l border-idle bg-surface p-4 shadow-lg"
            aria-label="文档详情"
          >
            <div className="mb-1 flex items-start justify-between gap-2">
              <h3 className="text-[15px] font-semibold text-primary">{selected.filename}</h3>
              <button
                type="button"
                className="rounded-card border border-idle px-2 py-1 text-xs text-primary hover:bg-active-surface"
                onClick={() => setSelected(null)}
              >
                关闭
              </button>
            </div>
            <p className="mb-3 text-xs text-muted">
              {CATEGORY_LABEL[selected.category]} · {selected.updatedAt}
            </p>
            <div className="mb-4">
              <Badge variant={KB_STATUS_META[selected.status].badge}>
                {KB_STATUS_META[selected.status].label}
              </Badge>
            </div>
            <dl className="mb-4 grid grid-cols-[88px_1fr] gap-y-2 text-[13px]">
              <dt className="text-muted">分类</dt>
              <dd>{CATEGORY_LABEL[selected.category]}</dd>
              <dt className="text-muted">Chunks</dt>
              <dd>{selected.chunks || '—'}</dd>
              <dt className="text-muted">Collection</dt>
              <dd className="font-mono text-xs">{CATEGORY_COLLECTION[selected.category]}</dd>
              <dt className="text-muted">说明</dt>
              <dd>{selected.note || '—'}</dd>
            </dl>
            <p className="mb-4 text-xs text-muted">
              切块后写入 dense + BM25 sparse；检索时按 industry / room_size / budget 过滤。
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="inline-flex items-center gap-1.5 rounded-card border border-idle bg-surface px-2.5 py-1.5 text-xs text-primary hover:bg-active-surface"
                onClick={() => {
                  reembed(selected)
                  setSelected(null)
                }}
              >
                <RefreshCw size={12} aria-hidden="true" />
                重新向量化
              </button>
              <button
                type="button"
                className="inline-flex items-center gap-1.5 rounded-card bg-danger px-2.5 py-1.5 text-xs text-white hover:brightness-95"
                onClick={() => remove(selected)}
              >
                <Trash2 size={12} aria-hidden="true" />
                删除文档
              </button>
            </div>
          </aside>
        </>
      )}

      {toast && (
        <div className="fixed bottom-5 right-5 z-[60] rounded-card border border-outline bg-surface px-3.5 py-2.5 text-[13px] shadow-lg">
          {toast}
        </div>
      )}
    </div>
  )
}
