import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import SectionRow from '../src/components/ProgressCard/SectionRow'
import type { SectionDef, SectionState } from '../src/types/schema'
import { SECTIONS } from '../src/data/sections'

function makeSection(def: SectionDef, status: SectionState['status']): SectionState {
  return { id: def.id, status, fields: SECTIONS.find((s) => s.id === def.id)!.fields.reduce((acc, f) => {
    acc[f.id] = { type: 'text', value: '' } as never
    return acc
  }, {} as SectionState['fields']) }
}

describe('SectionRow', () => {
  const customerDef = SECTIONS.find((s) => s.id === 'customer')!

  it('渲染图标 + 标题', () => {
    const section = makeSection(customerDef, 'pending')
    const { getByText, container } = render(
      <SectionRow def={customerDef} section={section} expanded={false} onToggle={() => {}} />
    )
    expect(getByText(customerDef.title)).toBeTruthy()
    expect(container.querySelector('[data-status="pending"]')).toBeTruthy()
  })

  it('complete 章节显示进度 X/Y', () => {
    const section = makeSection(customerDef, 'complete')
    const { getByText } = render(
      <SectionRow def={customerDef} section={section} expanded={false} onToggle={() => {}} />
    )
    // filledCount 全空 → 0/total
    expect(getByText(/0\/\d+/)).toBeTruthy()
  })

  it('active 章节通过图标区分,不再加行底色', () => {
    const section = makeSection(customerDef, 'active')
    const { container } = render(
      <SectionRow def={customerDef} section={section} expanded={false} onToggle={() => {}} />
    )
    const row = container.querySelector('[data-section-row]')
    expect(row?.className).not.toContain('bg-active-surface')
    expect(container.querySelector('[data-status="active"]')).toBeTruthy()
  })

  it('点击行触发 onToggle', () => {
    const section = makeSection(customerDef, 'pending')
    const onToggle = vi.fn()
    const { container } = render(
      <SectionRow def={customerDef} section={section} expanded={false} onToggle={onToggle} />
    )
    const row = container.querySelector('[data-section-row]') as HTMLElement
    fireEvent.click(row)
    expect(onToggle).toHaveBeenCalledTimes(1)
  })

  it('expanded=true 时显示 FieldDetail', () => {
    const section = makeSection(customerDef, 'pending')
    const { container } = render(
      <SectionRow def={customerDef} section={section} expanded={true} onToggle={() => {}} />
    )
    expect(container.querySelector('[data-field-detail]')).toBeTruthy()
  })
})
