/// <reference types="@testing-library/jest-dom/vitest" />
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import DeliveryPanel from '../src/components/DeliveryPanel/DeliveryPanel'
import { FormProvider } from '../src/state/FormContext'

describe('DeliveryPanel', () => {
  it('does not expose client-side deliverable download actions', () => {
    render(
      <FormProvider>
        <DeliveryPanel />
      </FormProvider>,
    )

    expect(screen.getByText('方案概要')).toBeInTheDocument()
    expect(screen.queryByText(/交付物生成/)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '场景设计说明' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '设备参数清单' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '需求确认书' })).not.toBeInTheDocument()
  })
})
