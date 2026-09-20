/** 交付管线 API 与前端展示类型（对齐后端 build_pipeline_detail）。 */
import { API_BASE, getToken, request } from './client'

export type PlanStatus = 'pending' | 'running' | 'ready' | 'partial' | 'failed'
export type SkillState = 'pending' | 'running' | 'succeeded' | 'partial' | 'failed'
export type ImageAngle = 'front' | 'left' | 'rear'

export interface PlanImage {
  angle: ImageAngle | string
  label: string
  name: string
  url: string
  width?: number
  height?: number
  sha256?: string
  missing?: boolean
  /** 鉴权加载后的 blob URL */
  objectUrl?: string
}

export interface PlanListItem {
  id: string
  title: string
  industry: string
  roomSize: string
  status: PlanStatus
  updatedAt: string
}

export interface PlanVideoOk {
  durationSec: number
  resolution: string
  url: string
  sha256?: string
  objectUrl?: string
}

export interface PlanVideoFailed {
  failed: true
  message: string
}

export interface PlanPdf {
  title: string
  sections: string[]
  url: string
}

export interface PlanSkills {
  plan: SkillState
  images: SkillState
  video: SkillState
  package: SkillState
}

export interface PlanEquipmentItem {
  knowledge_id?: number | null
  category: string
  name: string
  model?: string
  brand?: string
  qty?: number
  unit_price_band?: string
  reason?: string
  is_custom?: boolean
  already_owned?: boolean
  must_buy?: boolean
  specs?: Record<string, string | number | boolean>
  purchase_price?: string
  rent_monthly?: string
}

export interface PlanPackageItem {
  name: string
  qty?: number
  model?: string
  brand?: string
}

export interface PlanPackageTier {
  tier: string
  total_range: string
  items: PlanPackageItem[]
  mode?: 'rent' | 'buy' | 'mixed'
  monthly_rent_range?: string
  suitable?: string
}

export interface PlanRentalChannel {
  name: string
  kind?: string
  note?: string
  categories?: string[]
}

export interface PlanLayoutZone {
  name: string
  notes?: string
}

export interface PlanContent {
  meta?: Record<string, unknown> & {
    brand?: string
    industry?: string
    room_size?: string
    budget_total?: string
    area_band?: string
    layout_scale?: string
  }
  summary?: string
  layout?: {
    zones?: PlanLayoutZone[]
    lighting_plan?: string
    camera_plan?: string
    background_plan?: string
  }
  equipment_list?: PlanEquipmentItem[]
  package_tiers?: PlanPackageTier[]
  setup_steps?: string[]
  risks?: string[]
  scene_card?: {
    style_keywords?: string[]
    color_palette?: string[]
    color_temp?: string
    furniture?: string[]
    lighting_fixtures?: string[]
    product_category?: string
  }
  rental_channels?: PlanRentalChannel[]
  vertical_notes?: string[]
  must_buy_list?: string[]
}

export interface PlanDetailRaw {
  id: string
  title: string
  industry: string
  roomSize: string
  budget: string
  status: PlanStatus
  raw_status?: string
  current_skill?: string | null
  session_id?: string
  error?: string | null
  created_at?: string
  updated_at?: string
  skills: PlanSkills
  images: PlanImage[]
  video: PlanVideoOk | PlanVideoFailed | null
  pdf: PlanPdf | null
  plan?: PlanContent | null
  packageFileCount: number | null
  total_cost_cny?: number
  skill_runs?: Array<{
    id: number
    skill: string
    status: string
    attempt: number
    cost_cny: number
    error?: string | null
  }>
}

export interface PlanDetail extends PlanDetailRaw {
  budget: string
}

export const PLAN_STATUS_META: Record<
  PlanStatus,
  { label: string; badge: 'done' | 'accent' | 'warning' | 'danger' | 'muted' }
> = {
  ready: { label: '可下载', badge: 'done' },
  running: { label: '生成中', badge: 'accent' },
  partial: { label: '部分完成', badge: 'warning' },
  failed: { label: '失败', badge: 'danger' },
  pending: { label: '排队中', badge: 'muted' },
}

export const SKILL_STATUS_META: Record<SkillState, { label: string; dotClass: string }> = {
  succeeded: { label: '已完成', dotClass: 'bg-done' },
  running: { label: '生成中', dotClass: 'bg-accent' },
  partial: { label: '部分完成', dotClass: 'bg-warning' },
  failed: { label: '失败', dotClass: 'bg-danger' },
  pending: { label: '等待中', dotClass: 'bg-idle' },
}

const ANGLE_LABEL: Record<string, string> = {
  front: '正面 0°',
  left: '左侧 120°',
  rear: '背面 240°',
}

const ANGLE_NAME: Record<string, string> = {
  front: '主播主视角',
  left: '布光与背景',
  rear: '动线与纵深',
}

export function angleLabel(angle: string): string {
  return ANGLE_LABEL[angle] ?? angle
}

export function angleName(angle: string): string {
  return ANGLE_NAME[angle] ?? angle
}

async function responseError(r: Response, fallback: string): Promise<Error> {
  const body = (await r.json().catch(() => ({}))) as { detail?: unknown }
  const detail = typeof body.detail === 'string' ? body.detail : ''
  return new Error(detail || fallback)
}

export async function listPipelines(): Promise<{ items: PlanListItem[] }> {
  const r = await request('/pipeline')
  if (!r.ok) throw await responseError(r, `listPipelines: ${r.status}`)
  return r.json()
}

export async function getPipeline(id: string): Promise<PlanDetailRaw> {
  const r = await request(`/pipeline/${id}`)
  if (!r.ok) throw await responseError(r, `getPipeline: ${r.status}`)
  return r.json()
}

export async function startPipeline(
  sessionId: string,
  allowIncomplete = false,
): Promise<{ id: string; status: string; message: string }> {
  const r = await request('/pipeline', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, allow_incomplete: allowIncomplete }),
  })
  if (!r.ok) throw await responseError(r, `startPipeline: ${r.status}`)
  return r.json()
}

export async function retryPipeline(id: string, skill: string): Promise<{ id: string; skill: string }> {
  const r = await request(`/pipeline/${id}/retry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ skill }),
  })
  if (!r.ok) throw await responseError(r, `retryPipeline: ${r.status}`)
  return r.json()
}

export async function cancelPipeline(id: string): Promise<{ id: string; status: string }> {
  const r = await request(`/pipeline/${id}/cancel`, { method: 'POST' })
  if (!r.ok) throw await responseError(r, `cancelPipeline: ${r.status}`)
  return r.json()
}

/** 带鉴权取媒体/文件，返回 blob URL。 */
export async function fetchAuthedBlobUrl(path: string): Promise<string> {
  const token = getToken()
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const r = await fetch(`${API_BASE}${path}`, { headers })
  if (!r.ok) throw new Error(`下载失败: ${r.status}`)
  const blob = await r.blob()
  return URL.createObjectURL(blob)
}

export async function downloadAuthedFile(path: string, filename: string): Promise<void> {
  const token = getToken()
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const r = await fetch(`${API_BASE}${path}`, { headers })
  if (!r.ok) throw await responseError(r, `download: ${r.status}`)
  const blob = await r.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

/** 规范化后端 detail → 展示用 PlanDetail（补 label/name）。 */
export function normalizePlanDetail(raw: PlanDetailRaw): PlanDetail {
  const images = (raw.images || []).map((img) => ({
    ...img,
    label: img.label || angleLabel(img.angle),
    name: img.name || angleName(img.angle),
    missing: Boolean(img.missing || !img.url),
  }))
  return { ...raw, images }
}

export function skillStateOf(detail: PlanDetailRaw, key: keyof PlanSkills): SkillState {
  return detail.skills?.[key] ?? 'pending'
}

export function isVideoOk(
  video: PlanDetailRaw['video'],
): video is PlanVideoOk {
  return Boolean(video && 'durationSec' in video)
}

export function isVideoFailed(
  video: PlanDetailRaw['video'],
): video is PlanVideoFailed {
  return Boolean(video && 'failed' in video)
}
