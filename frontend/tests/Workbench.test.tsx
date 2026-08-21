/// <reference types="@testing-library/jest-dom/vitest" />
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const authState = vi.hoisted(() => ({
  role: 'admin' as 'admin' | 'guest',
}))

vi.mock('../src/components/BreathingScreen', () => ({
  default: () => <div>呼吸页</div>,
}))
vi.mock('../src/components/TopBar', () => ({
  default: ({ onReset }: { onReset: () => void }) => (
    <header><button type="button" onClick={onReset}>重新开始测试</button></header>
  ),
}))
vi.mock('../src/components/AdminEntryButton', () => ({ default: () => <div>管理后台入口</div> }))
vi.mock('../src/components/ChatPanel/ChatPanel', () => ({ default: () => <div>工作台内容</div> }))
vi.mock('../src/components/CenterCard/CenterCard', () => ({
  default: ({ children }: { children: React.ReactNode }) => <section>{children}</section>,
}))
vi.mock('../src/components/DeliveryPanel/FormPreviewSlot', () => ({ default: () => <div /> }))
vi.mock('../src/components/DeliveryPanel/DeliverableSlot', () => ({ default: () => <div>订单与结构化内容</div> }))
vi.mock('../src/components/GridBackground', () => ({ default: () => <div /> }))
vi.mock('../src/hooks/useZStack', () => ({
  ZStackProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useZStack: () => ({ z: 10, bringToFront: vi.fn(), isTopmost: true }),
}))
vi.mock('../src/state/FormContext', () => ({ FormProvider: ({ children }: { children: React.ReactNode }) => <>{children}</> }))
vi.mock('../src/state/theme', () => ({ useTheme: () => ({ theme: 'dark', toggleTheme: vi.fn() }) }))
vi.mock('../src/state/AuthContext', () => ({
  useAuth: () => ({ user: { role: authState.role }, logout: vi.fn() }),
}))

import Workbench from '../src/screens/Workbench'

describe('Workbench', () => {
  beforeEach(() => {
    authState.role = 'admin'
    sessionStorage.clear()
  })

  it('直接访问工作台时不重复展示呼吸页', () => {
    render(
      <MemoryRouter initialEntries={['/workbench']}>
        <Workbench />
      </MemoryRouter>,
    )

    expect(screen.getByText('工作台内容')).toBeInTheDocument()
    expect(screen.queryByText('呼吸页')).not.toBeInTheDocument()
  })

  it('游客不显示管理后台、订单和结构化内容', () => {
    authState.role = 'guest'

    render(
      <MemoryRouter initialEntries={['/workbench']}>
        <Workbench />
      </MemoryRouter>,
    )

    expect(screen.getByText('工作台内容')).toBeInTheDocument()
    expect(screen.queryByText('管理后台入口')).not.toBeInTheDocument()
    expect(screen.queryByText('订单与结构化内容')).not.toBeInTheDocument()
  })

  it('重新开始会清除旧会话并创建全新调研上下文', () => {
    sessionStorage.setItem('ics_session_id', 'submitted-session')
    render(
      <MemoryRouter initialEntries={['/workbench']}>
        <Workbench />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: '重新开始测试' }))

    expect(sessionStorage.getItem('ics_session_id')).toBeNull()
  })
})
