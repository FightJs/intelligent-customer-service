import type { SectionState, FieldValue, SectionDef, FieldDef } from '../types/schema'

/** 字段是否可见（条件分支：visibleIf 条件满足才可见）。 */
export function isFieldVisible(field: FieldDef, section: SectionState): boolean {
  if (!field.visibleIf) return true
  const dep = section.fields[field.visibleIf.fieldId]
  if (!dep || dep.type !== 'choice-single') return true
  const depValue = dep.value
  if (depValue === null) return false
  return field.visibleIf.op === 'eq'
    ? depValue === field.visibleIf.value
    : depValue !== field.visibleIf.value
}

function valueToText(v: FieldValue, def?: { label?: string; options?: { value: string; label: string }[] }): string {
  switch (v.type) {
    case 'text':
      return v.value
    case 'choice-single': {
      if (!v.value) return ''
      const opt = def?.options?.find((o) => o.value === v.value)
      return opt?.label ?? v.value
    }
    case 'choice-multi': {
      return v.value
        .map((val) => def?.options?.find((o) => o.value === val)?.label ?? val)
        .join('/')
    }
    case 'dimension':
      return Object.entries(v.value)
        .filter(([, n]) => n !== '')
        .map(([k, n]) => `${k}${n}`)
        .join('×')
    case 'image':
      return v.value.length ? `${v.value.length}张图` : ''
    case 'table':
      return v.value.length ? `${v.value.length}行` : ''
  }
}

export function makeSummary(section: SectionState, def: SectionDef): string {
  const parts: string[] = []
  for (const f of def.fields) {
    if (!isFieldVisible(f, section)) continue
    const v = section.fields[f.id]
    if (!v) continue
    const t = valueToText(v, f)
    if (t) parts.push(t)
  }
  if (parts.length === 0) return '未采集'
  if (parts.length < def.fields.length) return parts.join(' · ') + '…'
  return parts.join(' · ')
}

export function filledCount(section: SectionState, def: SectionDef): { filled: number; total: number } {
  let filled = 0
  let total = 0
  for (const f of def.fields) {
    if (!f.required) continue
    if (!isFieldVisible(f, section)) continue
    total++
    const v = section.fields[f.id]
    if (!v) continue
    if (valueToText(v, f) !== '') filled++
  }
  return { filled, total }
}
