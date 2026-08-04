/**
 * 后端 API client。
 *
 * 统一通过 request() 发请求，自动注入 Authorization: Bearer <token>。
 * 401 时清掉 token 并跳登录页（由 AuthContext 接管）。
 */
import type { StudioFormState, SectionId } from '../types/schema'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000/api'

const TOKEN_KEY = 'ics_token'
const USER_KEY = 'ics_user'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setAuth(token: string, user: AuthUser): void {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export interface AuthUser {
  id: number
  username: string
  role: 'user' | 'admin'
}

/** 统一请求封装：注入 token、401 自动清 auth。 */
async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken()
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string> | undefined),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const r = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (r.status === 401) {
    clearAuth()
    // 跳登录（避免在循环里用 router，简单 reload）
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
  }
  return r
}

// ── Auth ─────────────────────────────────────────────────────

export async function register(username: string, password: string): Promise<{ token: string; user: AuthUser }> {
  const r = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({})))?.detail ?? r.statusText
    throw new Error(detail)
  }
  return r.json()
}

export async function login(username: string, password: string): Promise<{ token: string; user: AuthUser }> {
  const r = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({})))?.detail ?? r.statusText
    throw new Error(detail)
  }
  return r.json()
}

export async function getMe(): Promise<AuthUser> {
  const r = await request('/auth/me')
  if (!r.ok) throw new Error(`me: ${r.status}`)
  return r.json()
}

// ── 业务端点 ─────────────────────────────────────────────────

export interface ToolEvent {
  kind: 'fill' | 'skip' | 'deliverable'
  section_id: SectionId
  field_id?: string
  value?: unknown
}

export interface SuggestionOption {
  value: string
  label: string
}

export interface Suggestion {
  section_id: SectionId
  field_id: string
  options: SuggestionOption[]
}

export interface SessionData {
  session_id: string
  form_state: StudioFormState
  greeting: string
}

export interface ChatResult {
  reply: string
  tool_events: ToolEvent[]
  form_state: StudioFormState
  form_complete: boolean
  suggestions: Suggestion[]
}

export async function createSession(): Promise<SessionData> {
  const r = await request('/session', { method: 'POST' })
  if (!r.ok) throw new Error(`createSession: ${r.status}`)
  return r.json()
}

export async function getSession(sessionId: string): Promise<SessionData> {
  const r = await request(`/session/${sessionId}`)
  if (!r.ok) throw new Error(`getSession: ${r.status}`)
  return r.json()
}

export interface FieldUpdate {
  section_id: SectionId
  field_id: string
  value: unknown
}

export async function chat(
  sessionId: string,
  message: string,
  history: { role: string; content: string }[] | undefined,
  updates?: FieldUpdate[],
): Promise<ChatResult> {
  const r = await request('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, history, updates }),
  })
  if (!r.ok) throw new Error(`chat: ${r.status}`)
  return r.json()
}

/** 生成交付物下载（文件流）。调用方自取 blob。 */
export async function generateUrl(docType: 'markdown' | 'excel' | 'word', sessionId: string): Promise<Response> {
  return request(`/generate/${docType}?session_id=${sessionId}`, { method: 'POST' })
}

// ── Admin ────────────────────────────────────────────────────

export interface AdminUser {
  id: number
  username: string
  role: string
  created_at: string
}

export interface AdminDeliveryListItem {
  id: number
  session_id: string
  user_id: number
  customer_name: string | null
  created_at: string
  owner_username: string
}

export interface AdminDeliveryDetail extends AdminDeliveryListItem {
  markdown: string
}

/** 分页列表响应。 */
export interface Paged<T> {
  items: T[]
  total: number
  page: number
  size: number
}

/** admin 列表查询参数。 */
export interface AdminListParams {
  search?: string
  sort_by?: string
  order?: 'asc' | 'desc'
  page?: number
  size?: number
}

function buildQuery(params: object): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

export async function adminListUsers(params: AdminListParams = {}): Promise<Paged<AdminUser>> {
  const r = await request(`/admin/users${buildQuery(params)}`)
  if (!r.ok) throw new Error(`adminListUsers: ${r.status}`)
  return r.json()
}

export async function adminListDeliveries(
  params: AdminListParams & { user_id?: number } = {},
): Promise<Paged<AdminDeliveryListItem>> {
  const r = await request(`/admin/deliverables${buildQuery(params)}`)
  if (!r.ok) throw new Error(`adminListDeliveries: ${r.status}`)
  return r.json()
}

export async function adminGetDelivery(id: number): Promise<AdminDeliveryDetail> {
  const r = await request(`/admin/deliverables/${id}`)
  if (!r.ok) throw new Error(`adminGetDelivery: ${r.status}`)
  return r.json()
}
