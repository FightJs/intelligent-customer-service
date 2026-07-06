import { describe, it, expect } from 'vitest'
import { reducer } from '../src/state/reducer'
import { createInitialState } from '../src/state/initialState'

describe('reducer', () => {
  it('update_field 更新字段值', () => {
    const s = createInitialState()
    const next = reducer(s, {
      type: 'update_field', sectionId: 'customer', fieldId: 'brand',
      value: { type: 'text', value: '云裳' },
    })
    expect(next.sections.customer.fields.brand).toEqual({ type: 'text', value: '云裳' })
  })

  it('update_field 填完必填后该节 status 变 complete', () => {
    let s = createInitialState()
    s = reducer(s, {
      type: 'update_field', sectionId: 'customer', fieldId: 'brand',
      value: { type: 'text', value: '云裳' },
    })
    expect(s.sections.customer.status).toBe('active')
    s = reducer(s, {
      type: 'update_field', sectionId: 'customer', fieldId: 'phone',
      value: { type: 'text', value: '138****' },
    })
    expect(s.sections.customer.status).toBe('complete')
  })

  it('advance 推进到下一节', () => {
    const s = createInitialState()
    expect(s.currentSectionId).toBe('customer')
    const next = reducer(s, { type: 'advance' })
    expect(next.currentSectionId).toBe('industry')
  })

  it('advance 到末节不再前进', () => {
    let s = createInitialState()
    for (let i = 0; i < 20; i++) s = reducer(s, { type: 'advance' })
    expect(s.currentSectionId).toBe('notes')
  })

  it('complete 标记完成', () => {
    const s = createInitialState()
    const next = reducer(s, { type: 'complete' })
    expect(next.completed).toBe(true)
  })
})
