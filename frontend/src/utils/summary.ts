import type {
  StudioFormState,
  SectionState,
  FieldValue,
  SectionDef,
  FieldDef,
} from '../types/schema'

/** 字段是否可见（条件分支：visibleIf 条件满足才可见）。 */
export function isFieldVisible(field: FieldDef, section: SectionState): boolean {
  if (!field.visibleIf) return true
  const dep = section.fields[field.visibleIf.fieldId]
  if (!dep || dep.type !== 'choice-single') return false
  const depValue = dep.value
  if (depValue === null) return false
  return field.visibleIf.op === 'eq'
    ? depValue === field.visibleIf.value
    : depValue !== field.visibleIf.value
}

/** 章节是否满足跨章节条件（例如仅“有现有设备”时显示设备模块）。 */
export function isSectionVisible(
  state: StudioFormState,
  def: SectionDef,
): boolean {
  if (!def.visibleIf) return true
  const [sectionId, fieldId] = def.visibleIf.fieldId.includes('.')
    ? def.visibleIf.fieldId.split('.', 2)
    : [def.id, def.visibleIf.fieldId]
  const dependency = state.sections[sectionId as keyof typeof state.sections]
    ?.fields[fieldId]
  if (!dependency || dependency.type !== 'choice-single' || dependency.value === null) {
    return false
  }
  return def.visibleIf.op === 'eq'
    ? dependency.value === def.visibleIf.value
    : dependency.value !== def.visibleIf.value
}

export function valueToText(v: FieldValue, def?: { label?: string; options?: { value: string; label: string }[] }): string {
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

export function isFieldRequired(
  state: StudioFormState,
  sectionId: string,
  field: FieldDef,
): boolean {
  if (state.mode === 'quick') {
    return state.requiredFieldIds.includes(
      `${sectionId}.${field.id}`,
    )
  }

  return field.required
}

export function filledCount(
  state: StudioFormState,
  def: SectionDef,
): {
  filled: number
  total: number
} {
  const section = (
    state.sections[def.id]
  )

  if (!isSectionVisible(state, def)) {
    return { filled: 0, total: 0 }
  }

  let filled = 0
  let total = 0

  for (const field of def.fields) {
    if (
      !isFieldRequired(
        state,
        def.id,
        field,
      )
    ) {
      continue
    }

    if (
      !isFieldVisible(
        field,
        section,
      )
    ) {
      continue
    }

    total += 1

    const value = (
      section.fields[field.id]
    )

    if (
      state.skippedFieldIds.includes(`${def.id}.${field.id}`)
      || (
        value
        && valueToText(
          value,
          field,
        ) !== ''
      )
    ) {
      filled += 1
    }
  }

  return {
    filled,
    total,
  }
}
