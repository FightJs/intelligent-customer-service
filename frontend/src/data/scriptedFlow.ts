/**
 * 对话流程定义（数据驱动版）。
 *
 * 流程步骤由 SECTIONS 自动生成，prompt 由 FieldDef.label 派生。
 * 条件分支字段（visibleIf）在条件不满足时自动跳过。
 *
 * 注意：本模块是前端"脚本化"流程，用于阶段 0（无后端 AI 时）。
 * 阶段 2 接入后端 AI agent 后，chatController 会改为调 /api/chat，
 * 本模块仍保留作为 fallback 和测试用。
 */
import type { SectionId, StudioFormState, SectionState } from '../types/schema'
import { SECTIONS, SECTION_ORDER, SECTION_BY_ID } from './sections'
import { isFieldVisible } from '../utils/summary'

export interface ScriptedStep {
  sectionId: SectionId
  fieldId: string
  prompt: string
}

/** 从 FieldDef.label 生成提问话术。 */
function fieldPrompt(sectionId: SectionId, fieldId: string): string {
  const def = SECTION_BY_ID[sectionId].fields.find((f) => f.id === fieldId)
  if (!def) return ''
  // 不同类型微调话术
  if (def.type === 'choice-single') return `${def.label}？`
  if (def.type === 'choice-multi') return `${def.label}？（可多选）`
  if (def.type === 'dimension') return `${def.label}？`
  if (def.type === 'image') return `${def.label}？（可直接跳过）`
  if (def.type === 'table') return `${def.label}？（可添加多行，也可跳过）`
  return `${def.label}？`
}

/** 所有可见字段按章节顺序展开为流程步骤。 */
export function visibleSteps(state: StudioFormState): ScriptedStep[] {
  const steps: ScriptedStep[] = []
  for (const secId of SECTION_ORDER) {
    const secState = state.sections[secId]
    const secDef = SECTION_BY_ID[secId]
    if (secState.status === 'skipped') continue
    for (const f of secDef.fields) {
      if (!isFieldVisible(f, secState)) continue
      steps.push({
        sectionId: secId,
        fieldId: f.id,
        prompt: fieldPrompt(secId, f.id),
      })
    }
  }
  return steps
}

export function stepAfter(fieldId: string): ScriptedStep | null {
  // 兼容旧 API：无 state 时按线性顺序找下一个（不处理条件分支）
  const all = visibleSteps(createEmptyFlowState())
  const idx = all.findIndex((s) => s.fieldId === fieldId)
  if (idx === -1 || idx + 1 >= all.length) return null
  return all[idx + 1]
}

export function nextStep(
  currentFieldId: string,
  state: StudioFormState,
): ScriptedStep | null {
  const steps = visibleSteps(state)
  const idx = steps.findIndex((s) => s.fieldId === currentFieldId)
  if (idx === -1 || idx + 1 >= steps.length) return null
  return steps[idx + 1]
}

export function transitionPrompt(from: SectionId, to: SectionId): string {
  const fromTitle = SECTION_BY_ID[from].title
  const toTitle = SECTION_BY_ID[to].title
  return `${fromTitle}信息够了，聊聊${toTitle}吧 👇`
}

/** 起始第一步。 */
export function firstStep(state: StudioFormState): ScriptedStep | null {
  return visibleSteps(state)[0] ?? null
}

// ── 用于 stepAfter 兼容函数的空状态 ──
function createEmptyFlowState(): StudioFormState {
  const sections = {} as StudioFormState['sections']
  for (const def of SECTIONS) {
    const fields: Record<string, { type: 'choice-single'; value: string | null }> = {}
    for (const f of def.fields) {
      // 给依赖字段一个非 null 默认值，让 visibleIf 字段默认可见
      fields[f.id] = { type: 'choice-single', value: '' }
    }
    sections[def.id] = { id: def.id, status: 'pending', fields } as SectionState
  }
  return {
    sections,
    currentSectionId: SECTION_ORDER[0],
    completed: false,
  }
}
