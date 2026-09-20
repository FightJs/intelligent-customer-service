import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Download, FileText, Loader2, RefreshCw, RotateCcw, Square } from 'lucide-react'
import Badge from '../components/admin/Badge'
import EmptyState from '../components/admin/EmptyState'
import PlanDocumentPanel from '../components/DeliveryPanel/PlanDocumentPanel'
import { useAuth } from '../state/AuthContext'
import { getLatestSession, getSession } from '../api/client'
import type { StudioFormState } from '../types/schema'
import { SECTIONS } from '../data/sections'
import { filledCount, makeSummary } from '../utils/summary'
import {
  getConversationSessionId,
  setConversationSessionId,
} from '../utils/conversationSession'
import {
  PLAN_STATUS_META,
  SKILL_STATUS_META,
  cancelPipeline,
  downloadAuthedFile,
  fetchAuthedBlobUrl,
  getPipeline,
  isVideoFailed,
  isVideoOk,
  listPipelines,
  normalizePlanDetail,
  retryPipeline,
  startPipeline,
  type PlanDetail,
  type PlanImage,
  type PlanListItem,
  type SkillState,
} from '../api/pipeline'
import './plans.css'

function SkillChip({ label, state }: { label: string; state: SkillState }) {
  const meta = SKILL_STATUS_META[state]
  return (
    <div className="rounded-card border border-outline bg-recess px-3 py-2.5">
      <div className="text-xs font-medium text-primary">{label}</div>
      <div className="mt-1 flex items-center gap-1.5 text-[11px] text-muted">
        <span className={`h-1.5 w-1.5 rounded-full ${meta.dotClass}`} aria-hidden="true" />
        {meta.label}
      </div>
    </div>
  )
}

/** 从管线关联会话回显工作台采集结果，确认方案与调研同源。 */
function SurveySummary({ sessionId }: { sessionId?: string }) {
  const [state, setState] = useState<StudioFormState | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!sessionId) {
      setState(null)
      setError('')
      return
    }
    let cancelled = false
    setLoading(true)
    setError('')
    getSession(sessionId)
      .then((data) => {
        if (!cancelled) setState(data.form_state)
      })
      .catch(() => {
        if (!cancelled) setError('无法读取调研会话')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [sessionId])

  if (!sessionId) return null

  if (loading) {
    return (
      <section className="mb-5">
        <h3 className="mb-2 text-[13px] font-semibold text-primary">调研需求摘要</h3>
        <div className="rounded-card border border-outline bg-recess px-3 py-3 text-xs text-muted">加载中…</div>
      </section>
    )
  }

  if (error || !state) {
    return (
      <section className="mb-5">
        <h3 className="mb-2 text-[13px] font-semibold text-primary">调研需求摘要</h3>
        <div className="rounded-card border border-outline bg-recess px-3 py-3 text-xs text-muted">
          {error || '暂无关联调研数据'}
        </div>
      </section>
    )
  }

  const rows = SECTIONS.map((definition) => ({
    title: definition.title,
    summary: makeSummary(state.sections[definition.id], definition),
    progress: filledCount(state, definition),
  })).filter((row) => row.summary !== '未采集' || row.progress.filled > 0)

  const totals = SECTIONS.reduce(
    (acc, definition) => {
      const progress = filledCount(state, definition)
      return { filled: acc.filled + progress.filled, total: acc.total + progress.total }
    },
    { filled: 0, total: 0 },
  )

  return (
    <section className="mb-5">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-[13px] font-semibold text-primary">调研需求摘要</h3>
        <span className="text-[11px] text-muted">必填 {totals.filled}/{totals.total} · 来自工作台会话</span>
      </div>
      {rows.length === 0 ? (
        <div className="rounded-card border border-outline bg-recess px-3 py-3 text-xs text-muted">
          该会话暂无已填写内容
        </div>
      ) : (
        <div className="space-y-1.5 rounded-card border border-outline bg-recess p-3">
          {rows.map((row) => (
            <div key={row.title} className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-xs">
              <span className="shrink-0 font-medium text-secondary">{row.title}</span>
              <span className="min-w-0 flex-1 text-muted">{row.summary}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function GalleryCard({ image, onOpen }: { image: PlanImage; onOpen: () => void }) {
  if (image.missing || !image.objectUrl) {
    return (
      <div
        className="relative aspect-[16/10] overflow-hidden rounded-card border border-outline bg-active-surface"
        aria-label={`${image.label} 暂未生成`}
      >
        <div className="absolute inset-0 grid place-items-center text-xs text-warning">
          {image.missing ? '该机位暂未生成' : '加载中…'}
        </div>
        <div className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-primary/55 px-2.5 py-2 text-xs text-white">
          <span className="font-semibold">{image.label}</span>
          <span className="opacity-90">{image.name}</span>
        </div>
      </div>
    )
  }

  return (
    <button
      type="button"
      onClick={onOpen}
      className="relative aspect-[16/10] w-full overflow-hidden rounded-card border border-outline bg-recess text-left transition hover:border-accent/45"
      aria-label={`放大查看 ${image.label}`}
    >
      <img
        src={image.objectUrl}
        alt={image.label}
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-primary/55 px-2.5 py-2 text-xs text-white">
        <span className="font-semibold">{image.label}</span>
        <span className="opacity-90">{image.name}</span>
      </div>
    </button>
  )
}

function Lightbox({
  images,
  index,
  onIndexChange,
  onClose,
}: {
  images: PlanImage[]
  index: number
  onIndexChange: (i: number) => void
  onClose: () => void
}) {
  const img = images[index]

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowLeft') onIndexChange((index - 1 + images.length) % images.length)
      if (e.key === 'ArrowRight') onIndexChange((index + 1) % images.length)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [index, images.length, onIndexChange, onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-primary/40 p-6"
      role="dialog"
      aria-modal="true"
      aria-label="预览图放大"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="w-full max-w-3xl overflow-hidden rounded-card border border-outline bg-surface shadow-xl">
        <div className="relative aspect-[16/10] bg-active-surface">
          {img.objectUrl ? (
            <img src={img.objectUrl} alt={img.label} className="absolute inset-0 h-full w-full object-contain" />
          ) : (
            <div className="absolute inset-0 grid place-items-center text-sm text-muted">暂无图片</div>
          )}
        </div>
        <div className="flex items-center justify-between gap-2 border-t border-outline px-3 py-2.5">
          <div>
            <strong className="text-sm text-primary">{img.label}</strong>
            <span className="ml-2 text-xs text-muted">{img.name}</span>
          </div>
          <div className="flex gap-1.5">
            <button
              type="button"
              className="rounded-card border border-idle bg-surface px-2.5 py-1 text-xs text-primary hover:bg-active-surface"
              onClick={() => onIndexChange((index - 1 + images.length) % images.length)}
            >
              上一张
            </button>
            <button
              type="button"
              className="rounded-card border border-idle bg-surface px-2.5 py-1 text-xs text-primary hover:bg-active-surface"
              onClick={() => onIndexChange((index + 1) % images.length)}
            >
              下一张
            </button>
            <button
              type="button"
              className="rounded-card border border-idle bg-surface px-2.5 py-1 text-xs text-primary hover:bg-active-surface"
              onClick={onClose}
            >
              关闭
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function PlanDetailPanel({
  plan,
  canRetry,
  onChanged,
}: {
  plan: PlanDetail
  canRetry: boolean
  onChanged: () => void
}) {
  const statusMeta = PLAN_STATUS_META[plan.status]
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)
  const [toast, setToast] = useState('')
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [busySkill, setBusySkill] = useState<string | null>(null)

  useEffect(() => {
    let revoked: string | null = null
    let cancelled = false
    async function loadVideo() {
      if (!isVideoOk(plan.video) || !plan.video.url) {
        setVideoUrl(null)
        return
      }
      if (plan.video.objectUrl) {
        setVideoUrl(plan.video.objectUrl)
        return
      }
      try {
        const url = await fetchAuthedBlobUrl(plan.video.url.replace(/^\/api/, ''))
        if (cancelled) {
          URL.revokeObjectURL(url)
          return
        }
        revoked = url
        setVideoUrl(url)
      } catch {
        setVideoUrl(null)
      }
    }
    void loadVideo()
    return () => {
      cancelled = true
      if (revoked) URL.revokeObjectURL(revoked)
    }
  }, [plan.video])

  function notify(message: string) {
    setToast(message)
    window.setTimeout(() => setToast(''), 2400)
  }

  async function retrySkill(skill: string) {
    if (!canRetry || busySkill) return
    setBusySkill(skill)
    try {
      await retryPipeline(plan.id, skill)
      notify(`已提交「${skill}」重试`)
      onChanged()
    } catch (e) {
      notify(e instanceof Error ? e.message : '重试失败')
    } finally {
      setBusySkill(null)
    }
  }

  async function downloadPackage() {
    try {
      await downloadAuthedFile(`/pipeline/${plan.id}/package`, `${plan.id}.zip`)
    } catch (e) {
      notify(e instanceof Error ? e.message : '下载失败')
    }
  }

  async function downloadPdf() {
    if (!plan.pdf?.url) return
    try {
      await downloadAuthedFile(plan.pdf.url.replace(/^\/api/, ''), 'plan.pdf')
    } catch (e) {
      notify(e instanceof Error ? e.message : '下载失败')
    }
  }

  const statusNote =
    plan.status === 'running'
      ? `当前阶段 ${plan.current_skill ?? ''} · 可离开页面，完成后回来查看`
      : plan.status === 'partial'
        ? '部分产物失败，方案文档仍可下载'
        : plan.status === 'failed'
          ? plan.error || '管线失败 · 可按 skill 单独重试'
          : ''

  const images = plan.images

  return (
    <article className="min-w-0 overflow-auto rounded-card border border-outline bg-surface p-4">
      <header className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-primary">{plan.title || plan.id}</h2>
          <p className="mt-1 text-xs text-muted">
            {[plan.industry, plan.roomSize, plan.budget && `预算 ${plan.budget}`, plan.updated_at]
              .filter(Boolean)
              .join(' · ')}
          </p>
        </div>
        <Badge variant={statusMeta.badge}>{statusMeta.label}</Badge>
      </header>

      {statusNote && <p className="-mt-1 mb-3 text-xs text-muted">{statusNote}</p>}

      <div className="mb-5 grid grid-cols-2 gap-2 lg:grid-cols-4">
        <SkillChip label="方案 PDF" state={plan.skills.plan} />
        <SkillChip label="预览图" state={plan.skills.images} />
        <SkillChip label="预览视频" state={plan.skills.video} />
        <SkillChip label="交付包" state={plan.skills.package} />
      </div>

      <SurveySummary sessionId={plan.session_id} />

      <section className="mb-5">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-[13px] font-semibold text-primary">360° 预览图</h3>
          <div className="flex items-center gap-2">
            {(plan.skills.images === 'failed' || plan.skills.images === 'partial') && canRetry && (
              <button
                type="button"
                disabled={busySkill === 'preview_images'}
                className="inline-flex items-center gap-1 rounded-card border border-idle bg-surface px-2 py-1 text-[11px] text-primary hover:bg-active-surface disabled:opacity-50"
                onClick={() => void retrySkill('preview_images')}
              >
                {busySkill === 'preview_images' ? (
                  <Loader2 size={12} className="animate-spin" aria-hidden="true" />
                ) : (
                  <RotateCcw size={12} aria-hidden="true" />
                )}
                重试图集
              </button>
            )}
            <span className="text-[11px] text-muted">三机位连贯静帧 · 0° / 120° / 240°</span>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
          {images.map((img, i) => (
            <GalleryCard
              key={img.angle}
              image={img}
              onOpen={() => {
                if (!img.missing && img.objectUrl) setLightboxIndex(i)
              }}
            />
          ))}
        </div>
      </section>

      <section className="mb-5">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-[13px] font-semibold text-primary">预览视频</h3>
          <span className="text-[11px] text-muted">
            {isVideoOk(plan.video) ? `${plan.video.durationSec}s · ${plan.video.resolution}` : ''}
          </span>
        </div>
        {isVideoFailed(plan.video) ? (
          <div className="rounded-card border border-danger/30 bg-danger/5 px-4 py-5 text-center">
            <p className="text-[13px] text-danger">{plan.video.message}</p>
            {canRetry && (
              <button
                type="button"
                disabled={busySkill === 'preview_video'}
                className="mt-3 inline-flex items-center gap-1.5 rounded-card bg-danger px-3 py-1.5 text-xs font-medium text-white hover:brightness-95 disabled:opacity-50"
                onClick={() => void retrySkill('preview_video')}
              >
                {busySkill === 'preview_video' ? (
                  <Loader2 size={12} className="animate-spin" aria-hidden="true" />
                ) : (
                  <RotateCcw size={12} aria-hidden="true" />
                )}
                重试预览视频
              </button>
            )}
          </div>
        ) : isVideoOk(plan.video) && videoUrl ? (
          <div className="overflow-hidden rounded-card border border-outline">
            <video
              src={videoUrl}
              controls
              className="video-stage-shell aspect-video w-full bg-black"
              preload="metadata"
            />
            <div className="video-meta-bar flex items-center justify-between px-3 py-2 text-xs">
              <span>
                {plan.video.durationSec}s · {plan.video.resolution}
              </span>
              <span>基于正面机位 i2v</span>
            </div>
          </div>
        ) : plan.skills.video === 'running' || plan.status === 'running' ? (
          <div className="rounded-card border border-outline bg-recess px-4 py-6 text-center">
            <p className="text-sm font-medium text-secondary">视频生成中</p>
            <p className="mt-1 text-xs text-muted">预览图就绪后将自动提交图生视频任务（约 1–4 分钟）</p>
          </div>
        ) : (
          <div className="rounded-card border border-outline bg-recess px-4 py-6 text-center">
            <p className="text-sm font-medium text-secondary">暂无预览视频</p>
          </div>
        )}
      </section>

      <section className="mb-5">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-[13px] font-semibold text-primary">方案清单</h3>
          <div className="flex items-center gap-2">
            {plan.pdf && (
              <button
                type="button"
                className="inline-flex items-center gap-1.5 rounded-card border border-idle bg-surface px-2.5 py-1 text-[11px] text-primary hover:bg-active-surface"
                onClick={() => void downloadPdf()}
              >
                <Download size={12} aria-hidden="true" />
                下载 PDF
              </button>
            )}
            <span className="text-[11px] text-muted">布局规模 · 设备型号 · 套餐 · 租赁 · 垂类要点</span>
          </div>
        </div>
        {plan.plan && (plan.plan.equipment_list?.length || plan.plan.layout?.zones?.length) ? (
          <PlanDocumentPanel plan={plan.plan} />
        ) : plan.pdf ? (
          <div className="flex flex-wrap items-center gap-3 rounded-card border border-outline bg-recess p-3">
            <div className="grid h-12 w-10 shrink-0 place-items-center rounded border border-outline bg-surface text-[10px] font-bold text-danger">
              PDF
            </div>
            <div className="min-w-0 flex-1">
              <h4 className="text-[13px] font-semibold text-primary">{plan.pdf.title}</h4>
              <p className="text-xs text-muted">含设备清单、三档套餐与可执行搭建步骤</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {plan.pdf.sections.map((s) => (
                  <span
                    key={s}
                    className="rounded-pill border border-outline bg-surface px-2 py-0.5 text-[11px] text-secondary"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-card border border-idle bg-surface px-3 py-1.5 text-xs text-primary hover:bg-active-surface"
              onClick={() => void downloadPdf()}
            >
              <Download size={14} aria-hidden="true" />
              下载方案
            </button>
          </div>
        ) : (
          <EmptyState
            title="方案文档生成中"
            description="知识检索完成后将渲染设备清单与套餐"
            icon={<FileText size={28} strokeWidth={1.5} />}
          />
        )}
      </section>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-accent/25 bg-brand-soft/50 p-3">
        <div>
          <strong className="block text-[13px] text-primary">完整交付包</strong>
          <span className="text-xs text-secondary">
            {plan.packageFileCount != null
              ? `${plan.packageFileCount} 个文件 · 图 / 视频 / 方案 / 说明`
              : '全部 skill 完成后可打包下载'}
          </span>
        </div>
        <button
          type="button"
          disabled={plan.packageFileCount == null}
          className="inline-flex items-center gap-1.5 rounded-card bg-accent px-3 py-1.5 text-xs font-medium text-white transition hover:bg-accent-strong disabled:opacity-50"
          onClick={() => void downloadPackage()}
        >
          <Download size={14} aria-hidden="true" />
          下载完整交付包
        </button>
      </div>

      {lightboxIndex !== null && (
        <Lightbox
          images={images}
          index={lightboxIndex}
          onIndexChange={setLightboxIndex}
          onClose={() => setLightboxIndex(null)}
        />
      )}

      {toast && (
        <div className="fixed bottom-5 right-5 z-[60] rounded-card border border-outline bg-surface px-3.5 py-2.5 text-[13px] shadow-lg">
          {toast}
        </div>
      )}
    </article>
  )
}

/** 用户端「我的方案」：真实 pipeline 列表 + 详情。Guest 可查看，不展示生成/重试入口。 */
export default function PlansScreen() {
  const { user } = useAuth()
  const isGuest = user?.role === 'guest'
  const [params] = useSearchParams()
  const [items, setItems] = useState<PlanListItem[]>([])
  const [detail, setDetail] = useState<PlanDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [toast, setToast] = useState('')
  const [starting, setStarting] = useState(false)
  const [activeId, setActiveId] = useState(params.get('id') ?? '')
  const blobUrlsRef = useRef<Map<string, string>>(new Map())

  const selectedId = activeId || items[0]?.id || ''

  const loadList = useCallback(async () => {
    try {
      const data = await listPipelines()
      setItems(data.items || [])
      setError('')
      return data.items || []
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败')
      return []
    }
  }, [])

  const loadDetail = useCallback(async (id: string) => {
    if (!id) {
      setDetail(null)
      return
    }
    try {
      const raw = await getPipeline(id)
      const norm = normalizePlanDetail(raw)

      // 鉴权拉取预览图 blob
      const map = blobUrlsRef.current
      const nextImages = await Promise.all(
        norm.images.map(async (img) => {
          if (img.missing || !img.url) return { ...img, objectUrl: undefined }
          const key = `${norm.id}:${img.angle}`
          const cached = map.get(key)
          if (cached) return { ...img, objectUrl: cached }
          try {
            const objectUrl = await fetchAuthedBlobUrl(img.url.replace(/^\/api/, ''))
            map.set(key, objectUrl)
            return { ...img, objectUrl }
          } catch {
            return { ...img, objectUrl: undefined }
          }
        }),
      )
      setDetail({ ...norm, images: nextImages })
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载详情失败')
    }
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    const list = await loadList()
    const id = selectedId || list[0]?.id || ''
    if (id) setActiveId(id)
    await loadDetail(id)
    setLoading(false)
  }, [loadDetail, loadList, selectedId])

  useEffect(() => {
    void refresh()
    return () => {
      for (const url of blobUrlsRef.current.values()) URL.revokeObjectURL(url)
      blobUrlsRef.current.clear()
    }
    // 首次进入
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!selectedId) return
    void loadDetail(selectedId)
  }, [selectedId, loadDetail])

  // running 时轮询
  useEffect(() => {
    if (!detail || (detail.status !== 'running' && detail.status !== 'pending')) return
    const t = window.setInterval(() => {
      void loadList()
      void loadDetail(detail.id)
    }, 8000)
    return () => window.clearInterval(t)
  }, [detail, loadDetail, loadList])

  useEffect(() => {
    if (!toast) return
    const t = window.setTimeout(() => setToast(''), 2200)
    return () => window.clearTimeout(t)
  }, [toast])

  async function resolveSessionId(): Promise<string | null> {
    if (!user) return null
    const saved = getConversationSessionId(user.id)
    if (saved) return saved
    try {
      const latest = await getLatestSession()
      if (latest.session_id) {
        setConversationSessionId(user.id, latest.session_id)
        return latest.session_id
      }
    } catch {
      // 无最近调研
    }
    return null
  }

  async function handleStart() {
    if (!user || isGuest || starting) return
    const sessionId = await resolveSessionId()
    if (!sessionId) {
      setToast('未找到当前会话，请先在工作台完成调研')
      return
    }
    setStarting(true)
    try {
      const result = await startPipeline(sessionId)
      setToast(result.message || '管线已启动')
      setActiveId(result.id)
      await refresh()
    } catch (e) {
      setToast(e instanceof Error ? e.message : '启动失败')
    } finally {
      setStarting(false)
    }
  }

  async function handleCancel() {
    if (!detail || isGuest) return
    try {
      await cancelPipeline(detail.id)
      setToast('已取消')
      await refresh()
    } catch (e) {
      setToast(e instanceof Error ? e.message : '取消失败')
    }
  }

  const list = useMemo(() => items, [items])

  return (
    <div className="flex h-full flex-col bg-base text-primary">
      <header className="flex h-12 shrink-0 items-center gap-4 border-b border-idle/40 px-5">
        <Link
          to="/workbench"
          className="inline-flex items-center gap-1 text-sm text-muted hover:text-secondary"
        >
          <ArrowLeft size={14} />
          返回工作台
        </Link>
        <span className="text-sm font-semibold text-primary">我的方案</span>
        <span className="text-xs text-muted">360 预览图、预览视频与交付包</span>
        <div className="flex-1" />
        {!isGuest && (
          <button
            type="button"
            disabled={starting}
            className="inline-flex items-center gap-1.5 rounded-card bg-accent px-2.5 py-1.5 text-xs font-medium text-white hover:bg-accent-strong disabled:opacity-50"
            onClick={() => void handleStart()}
          >
            {starting ? <Loader2 size={13} className="animate-spin" /> : null}
            生成方案
          </button>
        )}
        {detail && (detail.status === 'running' || detail.status === 'pending') && !isGuest && (
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-card border border-idle bg-surface px-2.5 py-1.5 text-xs text-primary hover:bg-active-surface"
            onClick={() => void handleCancel()}
          >
            <Square size={12} aria-hidden="true" />
            取消
          </button>
        )}
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-card border border-idle bg-surface px-2.5 py-1.5 text-xs text-primary hover:bg-active-surface"
          onClick={() => {
            void refresh()
            setToast('已刷新管线状态')
          }}
        >
          <RefreshCw size={13} aria-hidden="true" />
          刷新状态
        </button>
      </header>

      {error && (
        <div className="border-b border-danger/30 bg-danger/5 px-5 py-2 text-xs text-danger">{error}</div>
      )}

      <div className="plans-layout">
        <aside className="flex min-h-0 flex-col overflow-hidden rounded-card border border-outline bg-surface">
          <div className="flex items-center justify-between border-b border-outline px-3 py-2.5 text-xs text-secondary">
            <span>历史方案</span>
            <span>{list.length}</span>
          </div>
          <div className="flex-1 space-y-1.5 overflow-auto p-2">
            {loading && list.length === 0 ? (
              <div className="px-2 py-6 text-center text-xs text-muted">加载中…</div>
            ) : list.length === 0 ? (
              <div className="px-2 py-6 text-center text-xs text-muted">
                暂无方案。完成调研并「生成方案」后出现在这里。
              </div>
            ) : (
              list.map((p) => {
                const meta = PLAN_STATUS_META[p.status]
                const on = p.id === selectedId
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setActiveId(p.id)}
                    className={`w-full rounded-card border px-3 py-2.5 text-left transition ${
                      on
                        ? 'border-accent/35 bg-active-surface'
                        : 'border-transparent hover:bg-active-surface'
                    }`}
                  >
                    <span className="block text-[13px] font-medium text-primary">{p.title || p.id}</span>
                    <span className="mt-1 flex items-center justify-between gap-2 text-[11px] text-muted">
                      <span>
                        {[p.industry, p.roomSize].filter(Boolean).join(' · ') || '—'}
                      </span>
                      <Badge variant={meta.badge}>{meta.label}</Badge>
                    </span>
                    <span className="mt-1 block text-[11px] text-muted">{p.updatedAt || ''}</span>
                  </button>
                )
              })
            )}
          </div>
        </aside>

        {detail ? (
          <PlanDetailPanel
            key={detail.id}
            plan={detail}
            canRetry={!isGuest}
            onChanged={() => {
              void refresh()
            }}
          />
        ) : (
          <div className="rounded-card border border-outline bg-surface">
            <EmptyState
              title="暂无方案"
              description="完成工作台调研后点击「生成方案」，智能交付会生成预览图、视频与清单"
            />
          </div>
        )}
      </div>

      {toast && (
        <div className="fixed bottom-5 right-5 z-[60] rounded-card border border-outline bg-surface px-3.5 py-2.5 text-[13px] shadow-lg">
          {toast}
        </div>
      )}
    </div>
  )
}
