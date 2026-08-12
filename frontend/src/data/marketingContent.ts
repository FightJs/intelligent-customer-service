export const marketingNavItems = [
  { label: '能力', href: '#capabilities' },
  { label: '交付', href: '#deliverables' },
  { label: '场景', href: '#scenarios' },
] as const

export const capabilitySteps = [
  {
    index: '01',
    title: '引导式采集',
    description: '围绕行业、空间、预算、视觉偏好等关键条件推进对话。',
    fields: ['行业定位', '空间尺寸', '预算区间'],
  },
  {
    index: '02',
    title: '实时结构化',
    description: '每个回答都落到对应字段，缺口会被主动追问并实时校验。',
    fields: ['需求字段', '方案逻辑', '交付确认'],
  },
  {
    index: '03',
    title: '成套交付',
    description: '将确认后的需求编排成搭建方案、设备清单与评估报告。',
    fields: ['搭建方案', '设备清单', '评分报告'],
  },
] as const

export const workflowSteps = [
  { label: '客户原话', value: '想做一个能承接新品发布的直播间' },
  { label: 'AI 补问', value: '预计同时在线人数与主要展示设备？' },
  { label: '字段确认', value: '预算 8–12 万 · 14 个字段已确认' },
  { label: '交付节点', value: '直播间搭建方案已生成' },
] as const

export const deliverables = [
  { type: '方案 / 01', title: '直播间搭建方案', detail: '空间布局 · 灯光动线 · 视觉方向', accent: 'blue' },
  { type: '清单 / 02', title: '设备配置清单', detail: '镜头 · 收音 · 灯光 · 备用项', accent: 'green' },
  { type: '报告 / 03', title: '需求评分报告', detail: '完整度 92% · 2 项待确认', accent: 'violet' },
] as const

export const scenarios = [
  { index: '01', title: '首次开播', detail: '从一句模糊想法开始，逐步梳理出完整的开播方案。' },
  { index: '02', title: '直播间升级', detail: '保留已有资产，把新增目标和改造边界说清楚。' },
  { index: '03', title: '代运营协作', detail: '让客户、运营与交付团队共享同一份需求判断。' },
] as const

export const trustMetrics = [
  { value: '47 个关键字段', label: '覆盖直播间从目标到交付的完整判断链' },
  { value: '3 类交付物', label: '方案、清单与评分报告同步生成' },
  { value: '1 条信息流', label: '客户、运营和交付团队共享同一上下文' },
] as const

export const faqs = [
  { question: 'AI 会替代人工交付吗？', answer: '不会。AI 负责把需求问清、整理好并生成交付底稿，团队仍然掌握方案判断和最终确认。' },
  { question: '还没有完整预算，也可以开始吗？', answer: '可以。系统会先记录已知信息，再围绕预算、空间和目标逐步补齐缺口。' },
  { question: '咨询结束后会得到什么？', answer: '你会得到一份结构化需求、搭建方案、设备配置清单，以及待确认项和下一步建议。' },
] as const
