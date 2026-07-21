/**
 * 后端 API client。
 */
import type { StudioFormState, SectionId } from '../types/schema'

const API_BASE = 'http://localhost:8000/api'

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
  const r = await fetch(`${API_BASE}/session`, { method: 'POST' })
  if (!r.ok) throw new Error(`createSession: ${r.status}`)
  return r.json()
}

export async function getSession(sessionId: string): Promise<SessionData> {
  const r = await fetch(`${API_BASE}/session/${sessionId}`)
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
  const r = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, history, updates }),
  })
  if (!r.ok) throw new Error(`chat: ${r.status}`)
  return r.json()
}
