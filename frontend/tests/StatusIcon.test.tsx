import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import StatusIcon from '../src/components/ProgressCard/StatusIcon'

describe('StatusIcon', () => {
  it('pending 渲染空心圆环', () => {
    const { container } = render(<StatusIcon status="pending" />)
    const svg = container.querySelector('svg')
    expect(svg).not.toBeNull()
    expect(svg?.getAttribute('data-status')).toBe('pending')
  })

  it('active 渲染半圆带 animate-pulse class', () => {
    const { container } = render(<StatusIcon status="active" />)
    const wrapper = container.querySelector('[data-status="active"]')
    expect(wrapper?.className).toContain('animate-pulse')
  })

  it('complete 渲染对勾', () => {
    const { container } = render(<StatusIcon status="complete" />)
    expect(container.querySelector('[data-status="complete"]')).not.toBeNull()
  })

  it('skipped 渲染横杠 + opacity-50', () => {
    const { container } = render(<StatusIcon status="skipped" />)
    const wrapper = container.querySelector('[data-status="skipped"]')
    expect(wrapper?.className).toContain('opacity-50')
  })

  it('size prop 应用到 svg', () => {
    const { container } = render(<StatusIcon status="pending" size={20} />)
    const svg = container.querySelector('svg')
    expect(svg?.getAttribute('width')).toBe('20')
    expect(svg?.getAttribute('height')).toBe('20')
  })
})
