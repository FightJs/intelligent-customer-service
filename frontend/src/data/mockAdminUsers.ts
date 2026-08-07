import type { AdminUser } from '../api/client'

export interface MockAdminUser extends AdminUser {
  email: string
  status: 'active' | 'disabled'
  last_login: string | null
  active_sessions: number
  delivery_count: number
}

export const MOCK_ADMIN_USERS: MockAdminUser[] = [
  { id: 2024001, username: 'alice', email: 'alice@acme.cn', role: 'admin', status: 'active', created_at: '2026-01-12T10:22:00Z', last_login: '刚刚', active_sessions: 1, delivery_count: 12 },
  { id: 2024002, username: 'bob', email: 'bob@acme.cn', role: 'user', status: 'active', created_at: '2026-01-14T08:35:00Z', last_login: '今天 09:14', active_sessions: 2, delivery_count: 8 },
  { id: 2024003, username: 'charlie', email: 'charlie@acme.cn', role: 'user', status: 'active', created_at: '2026-01-18T16:40:00Z', last_login: '昨天 18:20', active_sessions: 0, delivery_count: 3 },
  { id: 2024004, username: 'diana', email: 'diana@acme.cn', role: 'user', status: 'disabled', created_at: '2026-02-03T11:05:00Z', last_login: '2026-07-28', active_sessions: 0, delivery_count: 0 },
  { id: 2024005, username: 'eric', email: 'eric@acme.cn', role: 'user', status: 'active', created_at: '2026-02-11T13:12:00Z', last_login: '今天 08:47', active_sessions: 1, delivery_count: 5 },
  { id: 2024006, username: 'frank', email: 'frank@acme.cn', role: 'user', status: 'active', created_at: '2026-02-19T09:28:00Z', last_login: '2026-08-05', active_sessions: 0, delivery_count: 16 },
]

export function roleLabel(role: string) {
  return role === 'admin' ? '管理员' : '普通用户'
}
