import type { FieldDef, StudioFormState, SectionState, FieldValue } from '../types/schema'
import { SECTIONS, SECTION_ORDER } from '../data/sections'

function emptyFieldValue(def: FieldDef): FieldValue {
  switch (def.type) {
    case 'text': return { type: 'text', value: '' }
    case 'choice-single': return { type: 'choice-single', value: null }
    case 'choice-multi': return { type: 'choice-multi', value: [] }
    case 'dimension':
      return { type: 'dimension', value: Object.fromEntries((def.dims ?? []).map((d) => [d, ''])) }
    case 'image': return { type: 'image', value: [] }
    case 'table': return { type: 'table', value: [] }
  }
}

function emptySectionState(sectionDef: typeof SECTIONS[number]): SectionState {
  const fields: Record<string, FieldValue> = {}
  for (const f of sectionDef.fields) fields[f.id] = emptyFieldValue(f)
  return { id: sectionDef.id, status: 'pending', fields }
}

export function createInitialState(): StudioFormState {
  const sections = {} as StudioFormState['sections']
  for (const def of SECTIONS) sections[def.id] = emptySectionState(def)
  return {
    sections,
    currentSectionId: SECTION_ORDER[0],
    completed: false,
  }
}
