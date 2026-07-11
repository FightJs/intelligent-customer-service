/**
 * @generated 由 frontend/scripts/gen-schema.mjs 从 schema.json 生成，勿手改。
 * 改后端 schema 后：python -m backend.survey.export && npm run gen:schema
 */

export type SectionId = 'budget' | 'customer' | 'equipment' | 'goal' | 'host' | 'industry' | 'notes' | 'product' | 'status' | 'venue'

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
