import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import PlanDocumentPanel from '../src/components/DeliveryPanel/PlanDocumentPanel'

const plan = {
  meta: {
    room_size: 'medium',
    area_band: '20-30㎡',
    layout_scale: '建议面积 20-35㎡；净高≥2.8m；供电单相 4kW',
  },
  summary: '测试方案',
  layout: {
    zones: [{ name: '主播区', notes: '单主播；坐姿为主' }],
    lighting_plan: '三点布光 4000K',
    camera_plan: '正面半身',
    background_plan: '简洁背景',
  },
  equipment_list: [
    {
      category: '灯光',
      name: 'LED COB 常亮主灯',
      brand: '爱图仕',
      model: 'Aputure 200d',
      qty: 2,
      must_buy: true,
      specs: { 功率: '200W', 色温: '5600K' },
      purchase_price: '¥2800-3600',
      rent_monthly: '¥250-380',
      reason: '中型间主光',
    },
  ],
  package_tiers: [
    {
      tier: '进阶',
      total_range: '3.6w',
      mode: 'mixed',
      monthly_rent_range: '600-900 元/月',
      suitable: '主力档',
      items: [{ name: 'Aputure 200d', qty: 2, model: 'Aputure 200d', brand: '爱图仕' }],
    },
  ],
  rental_channels: [
    { name: '人人租机', note: '全国器材租赁', categories: ['灯光'] },
  ],
  vertical_notes: ['女装主光 45° 侧上'],
  must_buy_list: ['爱图仕 Aputure 200d'],
  setup_steps: ['第1步：确认场地'],
  risks: ['预留耗材预算'],
}

describe('PlanDocumentPanel', () => {
  it('渲染布局规模、型号、必买、套餐、租赁与垂类要点', () => {
    render(<PlanDocumentPanel plan={plan} />)

    expect(screen.getByText('直播间布局与规模')).toBeInTheDocument()
    expect(screen.getByText(/建议面积 20-35㎡/)).toBeInTheDocument()
    expect(screen.getAllByText(/Aputure 200d/).length).toBeGreaterThan(0)
    expect(screen.getByText('200W')).toBeInTheDocument()
    expect(screen.getByText('必买 / 必租核心设备')).toBeInTheDocument()
    expect(screen.getByText('推荐套餐（购买 / 租赁）')).toBeInTheDocument()
    expect(screen.getByText('设备租赁 / 采购渠道')).toBeInTheDocument()
    expect(screen.getByText('人人租机')).toBeInTheDocument()
    expect(screen.getByText('垂类搭建要点')).toBeInTheDocument()
    expect(screen.getByText('女装主光 45° 侧上')).toBeInTheDocument()
  })
})
