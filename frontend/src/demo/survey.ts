import { SECTIONS } from '../data/sections'
import { createInitialState } from '../state/initialState'
import type { FieldDef, FieldValue, SectionId, StudioFormState } from '../types/schema'

export const demoSteps = [
  { section: 'customer', field: 'brand', groups: ['customer', 'industry'], sample: '青屿家居', question: '请先输入一个示例品牌名，我会同步补齐虚构的联系人和行业资料。' },
  { section: 'venue', field: 'area', groups: ['status', 'venue'], sample: '20-30㎡', question: '直播间面积大约是多少？可以填写 10㎡、25㎡ 或 60㎡。' },
  { section: 'budget', field: 'total', groups: ['budget', 'product'], sample: '3-5万', question: '搭建预算是多少？例如 3-5 万。' },
  { section: 'host', field: 'profile', groups: ['benchmark', 'host', 'equipment'], sample: '一名主播坐播，偶尔起身展示产品', question: '主播如何使用这个空间？例如一名主播坐播，偶尔起身展示产品。' },
  { section: 'goal', field: 'other', groups: ['goal'], sample: '先完成布光与收音，月底试播', question: '还有什么搭建目标或时间要求？' },
] as const

const defaults: Record<string, unknown> = {
  brand: '青屿家居', contact: '示例客户', phone: 'DEMO-0000', city: '示例城市',
  category: 'home', subcategory: '桌面家居', live_type: 'brand', has_room: 'no',
  area: '20-30', window: 'coverable', total: '3-5w', has_existing: 'yes',
  main: '桌面收纳与家居摆件', keywords: '自然、清爽、暖灰', has_benchmark: 'no',
  profile: '一名主播坐播，偶尔起身展示产品', core: 'new', other: '月底试播',
}

function sampleValue(field: FieldDef): FieldValue | undefined {
  const value = defaults[field.id]
  switch (field.type) {
    case 'text': return value ? { type: 'text', value: String(value) } : undefined
    case 'choice-single': return { type: field.type, value: String(value ?? field.options?.[0]?.value ?? '') }
    case 'choice-multi': return { type: field.type, value: [String(value ?? field.options?.[0]?.value ?? '')] }
    case 'dimension': return { type: field.type, value: Object.fromEntries((field.dims ?? []).map((dim, i) => [dim, ['5', '5', '3'][i] ?? '3'])) }
    case 'table': return { type: field.type, value: [Object.fromEntries((field.columns ?? []).map(c => [c.id, '示例相机 × 1']))] }
    case 'image': return undefined
  }
}

export function demoForm(turn: number): StudioFormState {
  const form = createInitialState()
  const active = demoSteps[turn]
  form.currentSectionId = active?.section ?? 'goal'
  form.currentFieldId = active?.field ?? ''
  form.requiredFieldIds = SECTIONS.flatMap(s => s.fields.filter(f => f.required).map(f => f.id))
  form.sections[form.currentSectionId].status = active ? 'active' : 'pending'
  return form
}

export function applyDemoAnswer(form: StudioFormState, turn: number, answer: string) {
  const active = demoSteps[turn]
  if (!active) return
  for (const sectionId of active.groups as readonly SectionId[]) {
    const definition = SECTIONS.find(section => section.id === sectionId)!
    const section = form.sections[sectionId]
    for (const field of definition.fields) {
      const value = sampleValue(field)
      if (value) section.fields[field.id] = value
    }
    section.status = 'complete'
  }
  const field = form.sections[active.section].fields[active.field]
  if (field?.type === 'text' && answer) field.value = answer
  if (field?.type === 'choice-single' && answer) {
    const definition = SECTIONS.find(s => s.id === active.section)?.fields.find(f => f.id === active.field)
    const normalized = (value: string) => value.replace(/[\s㎡]/g, '').replace(/万/g, 'w').replace(/[–—]/g, '-')
    const exact = definition?.options?.find(option =>
      normalized(option.value) === normalized(answer) || normalized(option.label) === normalized(answer))
    const number = Number(answer.match(/\d+(?:\.\d+)?/)?.[0])
    if (exact) field.value = exact.value
    else if (Number.isFinite(number) && active.section === 'venue') {
      field.value = number < 10 ? '<10' : number < 20 ? '10-20' : number < 30 ? '20-30' : number < 50 ? '30-50' : '50+'
    } else if (Number.isFinite(number) && active.section === 'budget' && /万|w/i.test(answer)) {
      field.value = number < 1 ? '<1w' : number < 3 ? '1-3w' : number < 5 ? '3-5w' : number < 10 ? '5-10w' : number < 20 ? '10-20w' : '20w+'
    }
  }
  const next = demoSteps[turn + 1]
  form.currentSectionId = next?.section ?? 'goal'
  form.currentFieldId = next?.field ?? ''
  if (next) form.sections[next.section].status = 'active'
}
