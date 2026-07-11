/**
 * 从 ../schema.json 生成前端 TS schema 文件。
 *
 * 用法：node scripts/gen-schema.mjs
 *
 * 产物（均为 @generated，勿手改）：
 *   src/types/schema.ts  — 数据结构类型（SectionId / FieldType / FieldDef / FieldValue / StudioFormState）
 *   src/data/sections.ts — UI 元数据常量（SECTIONS / SECTION_ORDER）
 *
 * 后端 schema 改动后，先跑 `python -m backend.survey.export`，再跑本脚本。
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '..')
const SCHEMA_JSON = resolve(ROOT, 'schema.json')
const OUT_TYPES = resolve(ROOT, 'src/types/schema.ts')
const OUT_SECTIONS = resolve(ROOT, 'src/data/sections.ts')

const payload = JSON.parse(readFileSync(SCHEMA_JSON, 'utf-8'))
const { sections, sectionOrder } = payload

// ─── helpers ────────────────────────────────────────────────
const sortedSectionIds = sectionOrder.slice().sort()
const sectionIdUnion = sortedSectionIds.map((id) => `'${id}'`).join(' | ')

const ts = (strings) => strings[0]

// ─── 1. src/types/schema.ts ─────────────────────────────────
const typesContent = `/**
 * @generated 由 frontend/scripts/gen-schema.mjs 从 schema.json 生成，勿手改。
 * 改后端 schema 后：python -m backend.survey.export && npm run gen:schema
 */

export type SectionId = ${sectionIdUnion}

export type FieldType =
  | 'text' | 'choice-single' | 'choice-multi' | 'dimension' | 'image' | 'table'

export interface OptionDef {
  value: string
  label: string
}

export interface VisibleIf {
  fieldId: string
  op: 'eq' | 'ne'
  value: string
}

export interface TableColumn {
  id: string
  label: string
  placeholder: string
}

export interface FieldDef {
  id: string
  label: string
  type: FieldType
  required: boolean
  options?: OptionDef[]
  dims?: string[]              // dimension：['宽','深','高']
  unit?: string                // dimension：'m' / 'cm'
  placeholder?: string         // text
  columns?: TableColumn[]      // table：列定义
  visibleIf?: VisibleIf        // 条件分支
}

export interface SectionDef {
  id: SectionId
  title: string
  hint: string
  order: number
  fields: FieldDef[]
}

export type FieldValue =
  | { type: 'text'; value: string }
  | { type: 'choice-single'; value: string | null }
  | { type: 'choice-multi'; value: string[] }
  | { type: 'dimension'; value: Record<string, string> }
  | { type: 'image'; value: string[] }
  | { type: 'table'; value: Record<string, string>[] }

export type SectionStatus = 'pending' | 'active' | 'complete' | 'skipped'

export interface SectionState {
  id: SectionId
  status: SectionStatus
  fields: Record<string, FieldValue>
}

export interface StudioFormState {
  sections: Record<SectionId, SectionState>
  currentSectionId: SectionId
  completed: boolean
}
`

// ─── 2. src/data/sections.ts ────────────────────────────────
// 用 JSON.stringify 注入数据，TS as 断言保证类型。
const sectionsData = JSON.stringify(sections, null, 2)
const orderData = JSON.stringify(sectionOrder, null, 2)

const sectionsContent = `/**
 * @generated 由 frontend/scripts/gen-schema.mjs 从 schema.json 生成，勿手改。
 * 改后端 schema 后：python -m backend.survey.export && npm run gen:schema
 */
import type { SectionDef, SectionId } from '../types/schema'

export const SECTIONS: SectionDef[] = ${sectionsData} as SectionDef[]

export const SECTION_ORDER: SectionId[] = ${orderData} as SectionId[]

export const SECTION_BY_ID: Record<SectionId, SectionDef> = Object.fromEntries(
  SECTIONS.map((s) => [s.id, s]),
) as Record<SectionId, SectionDef>
`

// ─── write ──────────────────────────────────────────────────
writeFileSync(OUT_TYPES, typesContent, 'utf-8')
writeFileSync(OUT_SECTIONS, sectionsContent, 'utf-8')

const fieldCount = sections.reduce((acc, s) => acc + s.fields.length, 0)
console.log(`已生成前端 schema:`)
console.log(`  ${OUT_TYPES}`)
console.log(`  ${OUT_SECTIONS}`)
console.log(`  章节: ${sections.length}  字段: ${fieldCount}`)
