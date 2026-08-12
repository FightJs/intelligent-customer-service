import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import SectionRow from '../src/components/ProgressCard/SectionRow'
import type { SectionDef, SectionState } from '../src/types/schema'
import { SECTIONS } from '../src/data/sections'
import { createInitialState } from '../src/state/initialState'

function makeSection(def: SectionDef, status: SectionState['status']): SectionState {
  return { id: def.id, status, fields: SECTIONS.find((s) => s.id === def.id)!.fields.reduce((acc, f) => {
    acc[f.id] = { type: 'text', value: '' } as never
    return acc
  }, {} as SectionState['fields']) }
}

function makeState(def: SectionDef, status: SectionState['status']) {
  const state = createInitialState()
  state.sections[def.id] = makeSection(def, status)
  return state
}

describe('SectionRow', () => {
  const customerDef = SECTIONS.find((s) => s.id === 'customer')!

  it('渲染图标 + 标题', () => {
    const state = makeState(customerDef, 'pending')
    const { getByText, container } = render(
      <SectionRow def={customerDef} state={state} expanded={false} onToggle={() => {}} />
    )
    expect(getByText(customerDef.title)).toBeTruthy()
    expect(container.querySelector('[data-status="pending"]')).toBeTruthy()
  })

  it('complete 章节显示进度 X/Y', () => {
    const state = makeState(customerDef, 'complete')
    const { getByText } = render(
      <SectionRow def={customerDef} state={state} expanded={false} onToggle={() => {}} />
    )
    // filledCount 全空 → 0/total
    expect(getByText(/0\/\d+/)).toBeTruthy()
  })

  it('active 章节通过图标区分,不再加行底色', () => {
    const state = makeState(customerDef, 'active')
    const { container } = render(
      <SectionRow def={customerDef} state={state} expanded={false} onToggle={() => {}} />
    )
    const row = container.querySelector('[data-section-row]')
    expect(row?.className).not.toContain('bg-active-surface')
    expect(container.querySelector('[data-status="active"]')).toBeTruthy()
  })

  it('点击行触发 onToggle', () => {
    const state = makeState(customerDef, 'pending')
    const onToggle = vi.fn()
    const { container } = render(
      <SectionRow def={customerDef} state={state} expanded={false} onToggle={onToggle} />
    )
    const row = container.querySelector('[data-section-row]') as HTMLElement
    fireEvent.click(row)
    expect(onToggle).toHaveBeenCalledTimes(1)
  })

  it('expanded=true 时显示 FieldDetail', () => {
    const state = makeState(customerDef, 'pending')
    const { container } = render(
      <SectionRow def={customerDef} state={state} expanded={true} onToggle={() => {}} />
    )
    expect(container.querySelector('[data-field-detail]')).toBeTruthy()
  })
})
