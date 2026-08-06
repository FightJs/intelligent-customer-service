import type { StudioFormState } from '../types/schema'
import { SECTIONS } from '../data/sections'
import { isFieldVisible, valueToText } from './summary'

/**
 * 把当前 form_state 转成 markdown 需求表（每节一个表格：字段 | 值）。
 * 用于需求表预览弹窗的 react-markdown 渲染。
 */
export function formStateToMarkdown(state: StudioFormState): string {
  const blocks: string[] = ['# 客户需求表']
  for (const def of SECTIONS) {
    const section = state.sections[def.id]
    if (!section) continue
    const rows: string[] = []
    for (const f of def.fields) {
      if (!isFieldVisible(f, section)) continue
      const v = section.fields[f.id]
      const text = v ? valueToText(v, f) : ''
      rows.push(`| ${f.label} | ${text || '—'} |`)
    }
    blocks.push(`\n## ${def.title}\n\n| 字段 | 内容 |\n| --- | --- |\n${rows.join('\n')}`)
  }
  return blocks.join('\n')
}
