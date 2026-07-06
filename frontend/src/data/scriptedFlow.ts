import type { SectionId } from '../types/schema'

export interface ScriptedStep {
  sectionId: SectionId
  fieldId: string
  prompt: string
}

export const SCRIPTED_FLOW: ScriptedStep[] = [
  { sectionId: 'customer', fieldId: 'brand', prompt: '您好！我是直播间搭建顾问，先问下您的品牌名是？' },
  { sectionId: 'customer', fieldId: 'phone', prompt: '留个联系电话方便后续沟通？' },
  { sectionId: 'industry', fieldId: 'category', prompt: '您主要做哪个品类？（选择最接近的）' },
  { sectionId: 'industry', fieldId: 'position', prompt: '品牌定位大概是？' },
  { sectionId: 'status', fieldId: 'hasRoom', prompt: '您现在已经有直播间了吗？' },
  { sectionId: 'status', fieldId: 'views', prompt: '场均观看大概多少人？' },
  { sectionId: 'venue', fieldId: 'area', prompt: '聊聊场地，直播间大概多少平米？' },
  { sectionId: 'venue', fieldId: 'size', prompt: '具体尺寸呢？宽×深×高，估个大概也行。' },
  { sectionId: 'budget', fieldId: 'total', prompt: '预算范围大概多少？' },
  { sectionId: 'budget', fieldId: 'equipment', prompt: '其中设备预算大概占多少？' },
  { sectionId: 'product', fieldId: 'main', prompt: '主营商品是什么？比如连衣裙、口红。' },
  { sectionId: 'product', fieldId: 'keywords', prompt: '风格关键词？3-5 个词，比如：国风、高端、雅致。' },
  { sectionId: 'benchmark', fieldId: 'hasBenchmark', prompt: '有没有对标参考的直播间？' },
  { sectionId: 'benchmark', fieldId: 'platform', prompt: '主要想对标哪个平台？' },
  { sectionId: 'host', fieldId: 'count', prompt: '主播几个人？' },
  { sectionId: 'host', fieldId: 'height', prompt: '主播身高多少？影响机位高度计算。' },
  { sectionId: 'equipment', fieldId: 'hasEquipment', prompt: '现有设备情况？是全部新买还是已有部分？' },
  { sectionId: 'goal', fieldId: 'core', prompt: '核心需求是什么？全新搭建 / 优化 / 只调设备…' },
  { sectionId: 'goal', fieldId: 'deadline', prompt: '期望什么时候交付？' },
  { sectionId: 'notes', fieldId: 'note', prompt: '还有什么特殊要求吗？没有可以直接说"无"。' },
]

export function stepAfter(fieldId: string): ScriptedStep | null {
  const idx = SCRIPTED_FLOW.findIndex((s) => s.fieldId === fieldId)
  if (idx === -1 || idx + 1 >= SCRIPTED_FLOW.length) return null
  return SCRIPTED_FLOW[idx + 1]
}

export function transitionPrompt(from: SectionId, to: SectionId): string {
  const titleMap: Record<SectionId, string> = {
    customer: '客户信息', industry: '行业品类', status: '直播间现状',
    venue: '场地条件', budget: '预算范围', product: '商品品牌',
    benchmark: '对标参考', host: '主播信息', equipment: '现有设备',
    goal: '需求目标', notes: '备注',
  }
  return `${titleMap[from]}信息够了，聊聊${titleMap[to]}吧 👇`
}
