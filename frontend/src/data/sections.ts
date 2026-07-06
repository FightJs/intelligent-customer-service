import type { SectionDef, SectionId } from '../types/schema'

export const SECTIONS: SectionDef[] = [
  {
    id: 'customer', title: '一、客户信息', order: 1,
    fields: [
      { id: 'brand', label: '品牌名', type: 'text', required: true, placeholder: '如：云裳' },
      { id: 'phone', label: '联系电话', type: 'text', required: true, placeholder: '138****' },
    ],
  },
  {
    id: 'industry', title: '二、行业品类', order: 2,
    fields: [
      {
        id: 'category', label: '行业大类', type: 'choice-single', required: true,
        options: [
          { value: 'women', label: '女装' }, { value: 'men', label: '男装' },
          { value: 'beauty', label: '美妆' }, { value: 'food', label: '食品' },
          { value: 'jewelry', label: '珠宝' }, { value: 'home', label: '家居' },
          { value: 'digital', label: '数码' }, { value: 'baby', label: '母婴' },
        ],
      },
      {
        id: 'position', label: '品牌定位', type: 'choice-single', required: true,
        options: [
          { value: 'mass', label: '平价大众' }, { value: 'value', label: '性价比' },
          { value: 'mid-high', label: '中高端' }, { value: 'luxury', label: '轻奢/高端' },
          { value: 'premium', label: '奢侈品' },
        ],
      },
    ],
  },
  {
    id: 'status', title: '三、直播间现状', order: 3,
    fields: [
      {
        id: 'hasRoom', label: '是否已有直播间', type: 'choice-single', required: true,
        options: [{ value: 'yes', label: '是' }, { value: 'no', label: '否' }],
      },
      {
        id: 'views', label: '场均观看', type: 'choice-single', required: false,
        options: [
          { value: '<500', label: '<500人' }, { value: '500-2k', label: '500-2000人' },
          { value: '2k-10k', label: '2000-1万人' }, { value: '10k+', label: '1万人以上' },
        ],
      },
    ],
  },
  {
    id: 'venue', title: '四、场地条件', order: 4,
    fields: [
      {
        id: 'area', label: '直播间面积', type: 'choice-single', required: true,
        options: [
          { value: '<10', label: '<10㎡' }, { value: '10-20', label: '10-20㎡' },
          { value: '20-30', label: '20-30㎡' }, { value: '30-50', label: '30-50㎡' },
          { value: '50+', label: '50㎡以上' },
        ],
      },
      {
        id: 'size', label: '具体尺寸', type: 'dimension', required: true,
        dims: ['宽', '深', '高'], unit: 'm',
      },
    ],
  },
  {
    id: 'budget', title: '五、预算范围', order: 5,
    fields: [
      {
        id: 'total', label: '总预算范围', type: 'choice-single', required: true,
        options: [
          { value: '<1w', label: '1万以下' }, { value: '1-3w', label: '1-3万' },
          { value: '3-5w', label: '3-5万' }, { value: '5-10w', label: '5-10万' },
          { value: '10-20w', label: '10-20万' }, { value: '20w+', label: '20万以上' },
        ],
      },
      {
        id: 'equipment', label: '其中设备预算', type: 'choice-single', required: true,
        options: [
          { value: '<5k', label: '5千以下' }, { value: '5k-1w', label: '5千-1万' },
          { value: '1-2w', label: '1-2万' }, { value: '2-5w', label: '2-5万' },
          { value: '5w+', label: '5万以上' },
        ],
      },
    ],
  },
  {
    id: 'product', title: '六、商品与品牌', order: 6,
    fields: [
      { id: 'main', label: '主营商品', type: 'text', required: true, placeholder: '如：连衣裙、口红' },
      { id: 'keywords', label: '风格关键词', type: 'text', required: true, placeholder: '3-5个词，如：国风、高端、雅致' },
    ],
  },
  {
    id: 'benchmark', title: '七、对标参考', order: 7,
    fields: [
      {
        id: 'hasBenchmark', label: '是否有对标直播间', type: 'choice-single', required: true,
        options: [{ value: 'yes', label: '是' }, { value: 'no', label: '否' }],
      },
      {
        id: 'platform', label: '主对标平台', type: 'choice-single', required: false,
        options: [
          { value: 'douyin', label: '抖音' }, { value: 'taobao', label: '淘宝直播' },
          { value: 'kuaishou', label: '快手' }, { value: 'weixin', label: '视频号' },
          { value: 'xhs', label: '小红书' },
        ],
      },
    ],
  },
  {
    id: 'host', title: '八、主播信息', order: 8,
    fields: [
      {
        id: 'count', label: '主播人数', type: 'choice-single', required: true,
        options: [{ value: '1', label: '1人' }, { value: '2', label: '2人' }, { value: '3+', label: '3人及以上' }],
      },
      {
        id: 'height', label: '主播身高', type: 'dimension', required: true,
        dims: ['女主播', '男主主播'], unit: 'cm',
      },
    ],
  },
  {
    id: 'equipment', title: '九、现有设备', order: 9,
    fields: [
      {
        id: 'hasEquipment', label: '是否已有部分设备', type: 'choice-single', required: true,
        options: [{ value: 'yes', label: '是' }, { value: 'no', label: '否，全部需要采购' }],
      },
    ],
  },
  {
    id: 'goal', title: '十、需求与目标', order: 10,
    fields: [
      {
        id: 'core', label: '核心需求', type: 'choice-single', required: true,
        options: [
          { value: 'new', label: '全新搭建直播间' }, { value: 'optimize', label: '优化现有直播间' },
          { value: 'tune', label: '只调设备参数' }, { value: 'decor', label: '只做装修设计' },
          { value: 'full', label: '全套方案' },
        ],
      },
      {
        id: 'deadline', label: '期望交付时间', type: 'choice-single', required: true,
        options: [
          { value: '3d', label: '3天内' }, { value: '1w', label: '一周内' },
          { value: '2w', label: '两周内' }, { value: 'flexible', label: '不着急' },
        ],
      },
    ],
  },
  {
    id: 'notes', title: '十一、客服备注', order: 11,
    fields: [
      { id: 'note', label: '特殊要求', type: 'text', required: false, placeholder: '任何特殊需求都可以写' },
    ],
  },
]

export const SECTION_ORDER: SectionId[] = SECTIONS.map((s) => s.id)
