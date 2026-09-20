export type KnowledgeStatus = 'pending' | 'embedding' | 'ready' | 'failed'
export type KnowledgeCategory = 'equipment' | 'scheme' | 'vertical'

export interface KnowledgeDoc {
  id: string
  filename: string
  category: KnowledgeCategory
  status: KnowledgeStatus
  chunks: number
  updatedAt: string
  note?: string
}

export const CATEGORY_LABEL: Record<KnowledgeCategory, string> = {
  equipment: '设备参数',
  scheme: '搭建方案',
  vertical: '垂类知识',
}

export const CATEGORY_COLLECTION: Record<KnowledgeCategory, string> = {
  equipment: 'equipment_specs',
  scheme: 'setup_schemes',
  vertical: 'vertical_knowledge',
}

export const KB_STATUS_META: Record<
  KnowledgeStatus,
  { label: string; badge: 'done' | 'accent' | 'warning' | 'danger' | 'muted' }
> = {
  ready: { label: '就绪', badge: 'done' },
  embedding: { label: '向量化中', badge: 'warning' },
  pending: { label: '待处理', badge: 'muted' },
  failed: { label: '失败', badge: 'danger' },
}

export const MOCK_KNOWLEDGE: KnowledgeDoc[] = [
  {
    id: 'kb_1',
    filename: '鞋靴布光与鞋墙陈列手册.pdf',
    category: 'vertical',
    status: 'ready',
    chunks: 42,
    updatedAt: '2026-09-08 11:20',
    note: '含三点布光、色温、鞋墙层次；按小标题切块',
  },
  {
    id: 'kb_2',
    filename: '爱图仕灯光参数表-2026.pdf',
    category: 'equipment',
    status: 'ready',
    chunks: 68,
    updatedAt: '2026-09-07 09:15',
    note: '整行一块，结构化字段进 metadata',
  },
  {
    id: 'kb_3',
    filename: '跃步25㎡实战篮球鞋套餐方案.pdf',
    category: 'scheme',
    status: 'ready',
    chunks: 12,
    updatedAt: '2026-09-06 16:40',
    note: '含三档 package_tiers 与 equipment_ids',
  },
  {
    id: 'kb_4',
    filename: '食品直播间动线规范.pdf',
    category: 'vertical',
    status: 'embedding',
    chunks: 0,
    updatedAt: '2026-09-10 14:55',
    note: '切块完成，正在写入 Milvus',
  },
  {
    id: 'kb_5',
    filename: '声卡与收音设备清单.pdf',
    category: 'equipment',
    status: 'pending',
    chunks: 0,
    updatedAt: '2026-09-10 15:02',
    note: '等待队列',
  },
  {
    id: 'kb_6',
    filename: '珠宝直播间安全与布光.pdf',
    category: 'vertical',
    status: 'failed',
    chunks: 0,
    updatedAt: '2026-09-05 10:11',
    note: 'Embedding 服务超时，可重新向量化',
  },
]

export function formatNow() {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}
