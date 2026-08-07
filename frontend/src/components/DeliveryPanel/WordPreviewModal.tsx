import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Download, FileType, Loader2, X } from 'lucide-react'
import { renderAsync } from 'docx-preview'
import { generateUrl } from '../../api/client'

interface WordPreviewModalProps {
  sessionId: string
  onClose: () => void
}

function getFilename(response: Response): string {
  const contentDisposition = response.headers.get('content-disposition') || ''
  const match = contentDisposition.match(/filename\*=UTF-8''(.+)/)
  return match ? decodeURIComponent(match[1]) : '需求确认书.docx'
}

/** 实验性 DOCX 预览：直接渲染当前会话生成的文件流，不向第三方发送文档。 */
export default function WordPreviewModal({ sessionId, onClose }: WordPreviewModalProps) {
  const documentRef = useRef<HTMLDivElement>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filename, setFilename] = useState('需求确认书.docx')
  const [downloading, setDownloading] = useState(false)
  const [isScrolling, setIsScrolling] = useState(false)
  const scrollTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    let cancelled = false
    const previewContainer = documentRef.current
    if (!previewContainer) return

    async function renderDocument(container: HTMLDivElement) {
      setLoading(true)
      setError('')
      container.replaceChildren()

      try {
        const response = await generateUrl('word', sessionId)
        if (!response.ok) throw new Error(`生成失败：${response.status}`)

        const blob = await response.blob()
        const nextFilename = getFilename(response)
        await renderAsync(blob, container, container, {
          className: 'docx',
          inWrapper: true,
          breakPages: true,
          ignoreLastRenderedPageBreak: false,
          useBase64URL: true,
        })

        if (!cancelled) setFilename(nextFilename)
      } catch (renderError) {
        if (!cancelled) setError(renderError instanceof Error ? renderError.message : '文档预览失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void renderDocument(previewContainer)
    return () => {
      cancelled = true
      previewContainer.replaceChildren()
    }
  }, [sessionId])

  useEffect(() => () => {
    if (scrollTimer.current !== null) clearTimeout(scrollTimer.current)
  }, [])

  useEffect(() => {
    function handleKeydown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeydown)
    return () => window.removeEventListener('keydown', handleKeydown)
  }, [onClose])

  async function handleDownload() {
    setDownloading(true)
    try {
      const response = await generateUrl('word', sessionId)
      if (!response.ok) throw new Error(`生成失败：${response.status}`)
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = getFilename(response)
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : '下载失败')
    } finally {
      setDownloading(false)
    }
  }

  function handleBodyScroll() {
    setIsScrolling(true)
    if (scrollTimer.current !== null) clearTimeout(scrollTimer.current)
    scrollTimer.current = setTimeout(() => setIsScrolling(false), 700)
  }

  return createPortal(
    <div className="word-preview-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="word-preview-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="word-preview-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="word-preview-header">
          <div className="word-preview-title">
            <span className="word-preview-file-icon" aria-hidden="true"><FileType size={18} /></span>
            <div className="min-w-0">
              <h2 id="word-preview-title">需求确认书</h2>
              <p>{filename} <span>实验预览</span></p>
            </div>
          </div>
          <div className="word-preview-actions">
            <button
              type="button"
              className="word-preview-download"
              onClick={() => void handleDownload()}
              disabled={loading || downloading}
            >
              {downloading ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
              下载
            </button>
            <button type="button" className="word-preview-close" onClick={onClose} aria-label="关闭预览">
              <X size={19} />
            </button>
          </div>
        </header>

        <div className={`word-preview-body${isScrolling ? ' is-scrolling' : ''}`} onScroll={handleBodyScroll}>
          {loading && (
            <div className="word-preview-status" role="status">
              <Loader2 size={18} className="animate-spin" />
              正在生成并渲染 Word 文档…
            </div>
          )}
          {error && <p className="word-preview-error" role="alert">{error}</p>}
          <div ref={documentRef} className={`word-preview-document${loading || error ? ' is-hidden' : ''}`} />
        </div>
      </section>
    </div>,
    document.body,
  )
}
