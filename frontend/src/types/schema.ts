export type SectionId =
  | 'customer' | 'industry' | 'status' | 'venue' | 'budget'
  | 'product' | 'benchmark' | 'host' | 'equipment' | 'goal' | 'notes'

export type FieldType = 'text' | 'choice-single' | 'choice-multi' | 'dimension' | 'image'

export interface OptionDef {
  value: string
  label: string
}

export interface FieldDef {
  id: string
  label: string
  type: FieldType
  required: boolean
  options?: OptionDef[]
  dims?: string[]              // for 'dimension'：如 ['宽','深','高']
  unit?: string                // for 'dimension'：如 'm' / 'cm'
  placeholder?: string         // for 'text'
}

export interface SectionDef {
  id: SectionId
  title: string                // '一、客户信息'
  order: number
  fields: FieldDef[]
}

export type FieldValue =
  | { type: 'text'; value: string }
  | { type: 'choice-single'; value: string | null }
  | { type: 'choice-multi'; value: string[] }
  | { type: 'dimension'; value: Record<string, string> }  // { 宽:'4.5', 深:'5', 高:'3' }
  | { type: 'image'; value: string[] }                    // 占位文件名列表

export interface SectionState {
  id: SectionId
  status: 'pending' | 'active' | 'complete'
  fields: Record<string, FieldValue>
}

export interface StudioFormState {
  sections: Record<SectionId, SectionState>
  currentSectionId: SectionId
  completed: boolean
}
