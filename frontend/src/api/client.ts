/**
 * 后端 API client。
 *
 * 统一通过 request() 发请求，自动注入 Authorization: Bearer <token>。
 * 401 时清掉 token 并跳登录页（由 AuthContext 接管）。
 */
import type { StudioFormState, SectionId } from '../types/schema'

export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000/api'

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
  role: 'user' | 'admin' | 'guest'
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

async function responseError(r: Response, fallback: string): Promise<Error> {
  const body = await r.json().catch(() => ({})) as { detail?: unknown }
  const detail = typeof body.detail === 'string' ? body.detail : ''
  return new Error(detail || fallback)
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

export async function guestLogin(): Promise<{
  token: string
  user: AuthUser
}> {
  const response = await request(
    '/auth/guest',
    {
      method: 'POST',
    },
  )

  if (!response.ok) {
    throw await responseError(
      response,
      `guestLogin: ${response.status}`,
    )
  }

  return response.json()
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

export interface SessionMessage {
  role: string
  content: string | Array<{
    type: string
    text?: string
    source?: { media_type: string; data: string }
  }>
}

export interface SessionData {
  session_id: string
  form_state: StudioFormState
  greeting: string
  messages?: SessionMessage[]
  form_complete?: boolean
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
  if (!r.ok) throw await responseError(r, `createSession: ${r.status}`)
  return r.json()
}

export async function getSession(sessionId: string): Promise<SessionData> {
  const r = await request(`/session/${sessionId}`)
  if (!r.ok) throw await responseError(r, `getSession: ${r.status}`)
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
  images?: string[],
): Promise<ChatResult> {
  const r = await request('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, history, updates, images }),
  })
  if (!r.ok) throw await responseError(r, `chat: ${r.status}`)
  return r.json()
}

export interface OrderResult {
  delivery_id: number
  sent: boolean
  message: string
}

/** 确认需求并发送订单。发送成功后管理员后台才会出现记录。 */
export async function sendOrder(
  sessionId: string,
): Promise<OrderResult> {
  const response = await request('/orders', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
    }),
  })

  if (!response.ok) {
    throw await responseError(
      response,
      `sendOrder: ${response.status}`,
    )
  }

  return response.json()
}

/** 生成交付物文件流。调用方自取 blob。 */
export async function generateUrl(
  docType: 'markdown' | 'excel' | 'word',
  sessionId: string,
  options: { preview?: boolean } = {},
): Promise<Response> {
  const previewQuery = options.preview ? '&preview=true' : ''
  return request(`/generate/${docType}?session_id=${sessionId}${previewQuery}`, { method: 'POST' })
}

// ── Admin ────────────────────────────────────────────────────

export interface AdminUser {
  id: number
  username: string
  role: 'user' | 'admin'
  created_at: string
}

export interface AdminUserDetail extends AdminUser {
  delivery_count: number
}

export interface AdminUserCreate {
  username: string
  password: string
  role: AdminUser['role']
}

export interface AdminUserUpdate {
  username?: string
  password?: string
  role?: AdminUser['role']
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

export interface AdminUsersPage extends Paged<AdminUser> {
  admin_count: number
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

export async function adminListUsers(params: AdminListParams = {}): Promise<AdminUsersPage> {
  const r = await request(`/admin/users${buildQuery(params)}`)
  if (!r.ok) throw await responseError(r, `adminListUsers: ${r.status}`)
  return r.json()
}

export async function adminCreateUser(payload: AdminUserCreate): Promise<AdminUserDetail> {
  const r = await request('/admin/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) throw await responseError(r, `adminCreateUser: ${r.status}`)
  return r.json()
}

export async function adminGetUser(id: number): Promise<AdminUserDetail> {
  const r = await request(`/admin/users/${id}`)
  if (!r.ok) throw await responseError(r, `adminGetUser: ${r.status}`)
  return r.json()
}

export async function adminUpdateUser(id: number, payload: AdminUserUpdate): Promise<AdminUserDetail> {
  const r = await request(`/admin/users/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) throw await responseError(r, `adminUpdateUser: ${r.status}`)
  return r.json()
}

export async function adminDeleteUser(id: number): Promise<void> {
  const r = await request(`/admin/users/${id}`, { method: 'DELETE' })
  if (!r.ok) throw await responseError(r, `adminDeleteUser: ${r.status}`)
}

export async function adminListDeliveries(
  params: AdminListParams & { user_id?: number } = {},
): Promise<Paged<AdminDeliveryListItem>> {
  const r = await request(`/admin/deliverables${buildQuery(params)}`)
  if (!r.ok) throw await responseError(r, `adminListDeliveries: ${r.status}`)
  return r.json()
}

export async function adminGetDelivery(id: number): Promise<AdminDeliveryDetail> {
  const r = await request(`/admin/deliverables/${id}`)
  if (!r.ok) throw await responseError(r, `adminGetDelivery: ${r.status}`)
  return r.json()
}

export async function adminUpdateDelivery(
  id: number,
  payload: Pick<AdminDeliveryDetail, 'customer_name' | 'markdown'>,
): Promise<AdminDeliveryDetail> {
  const r = await request(`/admin/deliverables/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) throw await responseError(r, `adminUpdateDelivery: ${r.status}`)
  return r.json()
}

export async function adminDeleteDelivery(id: number): Promise<void> {
  const r = await request(`/admin/deliverables/${id}`, { method: 'DELETE' })
  if (!r.ok) throw await responseError(r, `adminDeleteDelivery: ${r.status}`)
}
