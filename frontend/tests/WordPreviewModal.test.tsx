/// <reference types="@testing-library/jest-dom/vitest" />
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { generateUrlMock, renderAsyncMock } = vi.hoisted(() => ({
  generateUrlMock: vi.fn(),
  renderAsyncMock: vi.fn(),
}))

vi.mock('../src/api/client', () => ({ generateUrl: generateUrlMock }))
vi.mock('docx-preview', () => ({ renderAsync: renderAsyncMock }))

import WordPreviewModal from '../src/components/DeliveryPanel/WordPreviewModal'

describe('WordPreviewModal', () => {
  beforeEach(() => {
    generateUrlMock.mockReset()
    renderAsyncMock.mockReset()
  })

  it('缺少会话 ID 时显示错误且不请求空的 DOCX 地址', async () => {
    render(<WordPreviewModal sessionId="" onClose={vi.fn()} />)

    expect(await screen.findByRole('alert')).toHaveTextContent('当前会话尚未建立，无法预览 Word 文档')
    expect(screen.queryByRole('button', { name: '下载' })).not.toBeInTheDocument()
    expect(generateUrlMock).not.toHaveBeenCalled()
    expect(renderAsyncMock).not.toHaveBeenCalled()
  })
})
