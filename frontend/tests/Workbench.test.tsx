/// <reference types="@testing-library/jest-dom/vitest" />
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../src/components/BreathingScreen', () => ({
  default: () => <div>呼吸页</div>,
}))
vi.mock('../src/components/TopBar', () => ({ default: () => <header /> }))
vi.mock('../src/components/AdminEntryButton', () => ({ default: () => <div /> }))
vi.mock('../src/components/ChatPanel/ChatPanel', () => ({ default: () => <div>工作台内容</div> }))
vi.mock('../src/components/ProgressCard/ProgressCard', () => ({ default: () => <div /> }))
vi.mock('../src/components/CenterCard/CenterCard', () => ({
  default: ({ children }: { children: React.ReactNode }) => <section>{children}</section>,
}))
vi.mock('../src/components/DeliveryPanel/FormPreviewSlot', () => ({ default: () => <div /> }))
vi.mock('../src/components/DeliveryPanel/DeliverableSlot', () => ({ default: () => <div /> }))
vi.mock('../src/components/GridBackground', () => ({ default: () => <div /> }))
vi.mock('../src/hooks/useZStack', () => ({ ZStackProvider: ({ children }: { children: React.ReactNode }) => <>{children}</> }))
vi.mock('../src/state/FormContext', () => ({ FormProvider: ({ children }: { children: React.ReactNode }) => <>{children}</> }))
vi.mock('../src/state/theme', () => ({ useTheme: () => ({ theme: 'dark', toggleTheme: vi.fn() }) }))
vi.mock('../src/state/AuthContext', () => ({
  useAuth: () => ({ user: { role: 'admin' }, logout: vi.fn() }),
}))

import Workbench from '../src/screens/Workbench'

describe('Workbench', () => {
  it('直接访问工作台时不重复展示呼吸页', () => {
    render(
      <MemoryRouter initialEntries={['/workbench']}>
        <Workbench />
      </MemoryRouter>,
    )

    expect(screen.getByText('工作台内容')).toBeInTheDocument()
    expect(screen.queryByText('呼吸页')).not.toBeInTheDocument()
  })
})
