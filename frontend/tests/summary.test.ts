import { describe, it, expect } from 'vitest'
import { makeSummary, filledCount, valueToText } from '../src/utils/summary'
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

describe('valueToText', () => {
  it('text 返回原文', () => {
    expect(valueToText({ type: 'text', value: '云裳' })).toBe('云裳')
  })

  it('choice-single 空值返回空串', () => {
    expect(valueToText({ type: 'choice-single', value: null })).toBe('')
  })

  it('choice-single 命中 option 返回 label', () => {
    const def = { options: [{ value: 'douyin', label: '抖音' }] }
    expect(valueToText({ type: 'choice-single', value: 'douyin' }, def)).toBe('抖音')
  })

  it('choice-multi 拼接 label', () => {
    const def = { options: [{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }] }
    expect(valueToText({ type: 'choice-multi', value: ['a', 'b'] }, def)).toBe('A/B')
  })

  it('dimension 过滤空值并拼接', () => {
    const v = { type: 'dimension', value: { 宽: '4.5', 深: '', 高: '3' } } as const
    expect(valueToText(v)).toBe('宽4.5×高3')
  })

  it('image 空数组返回空串', () => {
    expect(valueToText({ type: 'image', value: [] })).toBe('')
  })

  it('image 非空返回张数', () => {
    expect(valueToText({ type: 'image', value: ['a', 'b'] })).toBe('2张图')
  })

  it('table 空数组返回空串', () => {
    expect(valueToText({ type: 'table', value: [] })).toBe('')
  })

  it('table 非空返回行数', () => {
    expect(valueToText({ type: 'table', value: [{ a: '1' }] })).toBe('1行')
  })
})
