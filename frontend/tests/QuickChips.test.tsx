import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import QuickChips from '../src/components/ChatPanel/QuickChips'


const OPTIONS = [
  { value: 'owner', label: '主理人（老板）' },
  { value: 'host', label: '主播' },
  { value: 'operator', label: '运营' },
]


describe('QuickChips', () => {
  it('多选模式勾选多个选项后统一确认', () => {
    const onPick = vi.fn()
    const onPickMany = vi.fn()
    render(
      <QuickChips
        options={OPTIONS}
        onPick={onPick}
        onPickMany={onPickMany}
        multiple
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: '主理人（老板）' }))
    fireEvent.click(screen.getByRole('button', { name: '主播' }))

    expect(onPick).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: '确认选择（2）' })).toBeEnabled()

    fireEvent.click(screen.getByRole('button', { name: '确认选择（2）' }))

    expect(onPickMany).toHaveBeenCalledWith([OPTIONS[0], OPTIONS[1]])
  })

  it('单选模式保持点击即提交', () => {
    const onPick = vi.fn()
    render(<QuickChips options={OPTIONS} onPick={onPick} />)

    fireEvent.click(screen.getByRole('button', { name: '运营' }))

    expect(onPick).toHaveBeenCalledWith(OPTIONS[2])
    expect(screen.queryByRole('button', { name: /确认选择/ })).not.toBeInTheDocument()
  })
})
