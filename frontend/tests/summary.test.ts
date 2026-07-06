import { describe, it, expect } from 'vitest'
import { makeSummary, filledCount } from '../src/utils/summary'
import type { SectionState, SectionDef } from '../src/types/schema'

const def: SectionDef = {
  id: 'venue', title: '四、场地条件', order: 4,
  fields: [
    {
      id: 'area', label: '面积', type: 'choice-single', required: true,
      options: [{ value: '10-20', label: '10-20㎡' }],
    },
    {
      id: 'size', label: '尺寸', type: 'dimension', required: true,
      dims: ['宽', '深', '高'], unit: 'm',
    },
  ],
}

describe('makeSummary', () => {
  it('全空返回未采集', () => {
    const s: SectionState = {
      id: 'venue', status: 'pending',
      fields: {
        area: { type: 'choice-single', value: null },
        size: { type: 'dimension', value: { 宽: '', 深: '', 高: '' } },
      },
    }
    expect(makeSummary(s, def)).toBe('未采集')
  })

  it('部分填返回带省略号', () => {
    const s: SectionState = {
      id: 'venue', status: 'active',
      fields: {
        area: { type: 'choice-single', value: '10-20' },
        size: { type: 'dimension', value: { 宽: '', 深: '', 高: '' } },
      },
    }
    expect(makeSummary(s, def)).toBe('10-20㎡…')
  })

  it('全填返回拼接', () => {
    const s: SectionState = {
      id: 'venue', status: 'complete',
      fields: {
        area: { type: 'choice-single', value: '10-20' },
        size: { type: 'dimension', value: { 宽: '4.5', 深: '5', 高: '3' } },
      },
    }
    expect(makeSummary(s, def)).toBe('10-20㎡ · 宽4.5×深5×高3')
  })
})

describe('filledCount', () => {
  it('统计必填已填数', () => {
    const s: SectionState = {
      id: 'venue', status: 'active',
      fields: {
        area: { type: 'choice-single', value: '10-20' },
        size: { type: 'dimension', value: { 宽: '', 深: '', 高: '' } },
      },
    }
    expect(filledCount(s, def)).toEqual({ filled: 1, total: 2 })
  })
})
