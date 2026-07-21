import type { StudioFormState, SectionId, FieldValue, SectionState } from '../types/schema'
import { SECTIONS, SECTION_ORDER } from '../data/sections'
import { filledCount } from '../utils/summary'

export type Action =
  | { type: 'update_field'; sectionId: SectionId; fieldId: string; value: FieldValue }
  | { type: 'replace_state'; state: StudioFormState }
  | { type: 'set_active_section'; sectionId: SectionId }
  | { type: 'advance' }
  | { type: 'complete' }
  | { type: 'reset' }

function sectionDef(id: SectionId) {
  return SECTIONS.find((s) => s.id === id)!
}

function recomputeStatus(state: StudioFormState, sectionId: SectionId): StudioFormState {
  const def = sectionDef(sectionId)
  const sec = state.sections[sectionId]
  const { filled, total } = filledCount(sec, def)
  let status: SectionState['status']
  if (filled >= total && total > 0) status = 'complete'
  else if (filled > 0 || sectionId === state.currentSectionId) status = 'active'
  else status = 'pending'
  const newSec = { ...sec, status }
  return { ...state, sections: { ...state.sections, [sectionId]: newSec } }
}

export function reducer(state: StudioFormState, action: Action): StudioFormState {
  switch (action.type) {
    case 'update_field': {
      const sec = state.sections[action.sectionId]
      const newFields = { ...sec.fields, [action.fieldId]: action.value }
      const newSec = { ...sec, fields: newFields }
      let next: StudioFormState = { ...state, sections: { ...state.sections, [action.sectionId]: newSec } }
      next = recomputeStatus(next, action.sectionId)
      return next
    }
    case 'replace_state': {
      // 后端返回的 section.status 可能不准（如从未填的章节仍为 pending），
      // 整体替换后按填充情况重算一次，保证 ProgressCard 显示正确。
      let next = action.state
      for (const id of Object.keys(next.sections) as SectionId[]) {
        next = recomputeStatus(next, id)
      }
      return next
    }
    case 'set_active_section':
      return { ...state, currentSectionId: action.sectionId }
    case 'advance': {
      const idx = SECTION_ORDER.indexOf(state.currentSectionId)
      const nextIdx = Math.min(idx + 1, SECTION_ORDER.length - 1)
      return { ...state, currentSectionId: SECTION_ORDER[nextIdx] }
    }
    case 'complete':
      return { ...state, completed: true }
    case 'reset':
      return state
    default:
      return state
  }
}
