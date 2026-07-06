import type { SectionState, FieldValue, SectionDef } from '../types/schema'

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
  }
}

export function makeSummary(section: SectionState, def: SectionDef): string {
  const parts: string[] = []
  for (const f of def.fields) {
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
  for (const f of def.fields) {
    if (!f.required) continue
    const v = section.fields[f.id]
    if (!v) continue
    if (valueToText(v, f) !== '') filled++
  }
  const total = def.fields.filter((f) => f.required).length
  return { filled, total }
}
