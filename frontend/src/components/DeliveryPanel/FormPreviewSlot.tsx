import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent as ReactMouseEvent,
} from 'react'
import styled from 'styled-components'

interface FormPreviewSlotProps {
  isPreviewOpen?: boolean
  onPreview?: () => void
}

const FOLDER_FILES = [
  { className: 'file-5', label: '需求总览', tag: '实时更新' },
  { className: 'file-4', label: '场景设计说明', tag: '设计结构' },
  { className: 'file-3', label: '设备参数清单', tag: '设备结构' },
  { className: 'file-2', label: '需求确认书', tag: '确认内容' },
  { className: 'file-1', label: '品牌与商品', tag: '采集信息' },
] as const

const MAX_HORIZONTAL_OFFSET = 120
const DRAG_THRESHOLD = 4

export default function FormPreviewSlot({ isPreviewOpen = false, onPreview }: FormPreviewSlotProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [dragging, setDragging] = useState(false)
  const boundaryRef = useRef<HTMLDivElement>(null)
  const folderRef = useRef<HTMLDivElement>(null)
  const suppressPreviewRef = useRef(false)

  useEffect(() => {
    setIsOpen(isPreviewOpen)
  }, [isPreviewOpen])

  function openPreview() {
    setIsOpen(true)
    onPreview?.()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      openPreview()
    }
  }

  function handleDragStart(event: ReactMouseEvent<HTMLDivElement>) {
    if (event.button !== 0) return

    const start = {
      clientX: event.clientX,
      clientY: event.clientY,
      offsetX: dragOffset.x,
      offsetY: dragOffset.y,
      dragged: false,
    }

    function handleDragMove(moveEvent: MouseEvent) {
      const deltaX = moveEvent.clientX - start.clientX
      const deltaY = moveEvent.clientY - start.clientY

      if (!start.dragged && Math.hypot(deltaX, deltaY) >= DRAG_THRESHOLD) {
        start.dragged = true
        setDragging(true)
        document.body.style.cursor = 'grabbing'
        document.body.style.userSelect = 'none'
      }

      if (!start.dragged) return

      const boundaryRect = boundaryRef.current?.getBoundingClientRect()
      const folderRect = folderRef.current?.getBoundingClientRect()
      const maxX = boundaryRect && folderRect
        ? Math.min(MAX_HORIZONTAL_OFFSET, Math.max(0, (boundaryRect.width - folderRect.width) / 2))
        : MAX_HORIZONTAL_OFFSET
      const maxY = boundaryRect && folderRect
        ? Math.max(0, (boundaryRect.height - folderRect.height) / 2)
        : MAX_HORIZONTAL_OFFSET

      setDragOffset({
        x: Math.max(-maxX, Math.min(maxX, start.offsetX + deltaX)),
        y: Math.max(-maxY, Math.min(maxY, start.offsetY + deltaY)),
      })
    }

    function handleDragEnd() {
      if (start.dragged) {
        suppressPreviewRef.current = true
        setDragging(false)
      }

      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      document.removeEventListener('mousemove', handleDragMove)
      document.removeEventListener('mouseup', handleDragEnd)
    }

    document.addEventListener('mousemove', handleDragMove)
    document.addEventListener('mouseup', handleDragEnd)
  }

  function handlePreview(event: ReactMouseEvent<HTMLDivElement>) {
    if (suppressPreviewRef.current) {
      event.preventDefault()
      event.stopPropagation()
      suppressPreviewRef.current = false
      return
    }

    openPreview()
  }

  return (
    <StyledWrapper ref={boundaryRef}>
      <div
        ref={folderRef}
        className={`folder-card${dragging ? ' is-dragging' : ''}`}
        role="button"
        tabIndex={0}
        aria-label="预览需求表"
        onMouseDown={handleDragStart}
        onClickCapture={handlePreview}
        onKeyDown={handleKeyDown}
        style={{
          transform: `translate3d(${dragOffset.x}px, ${dragOffset.y}px, 0) scale(.82)`,
        }}
      >
        <input
          className="folder-toggle"
          type="checkbox"
          checked={isOpen}
          readOnly
          tabIndex={-1}
          aria-hidden="true"
        />

        <div className="hint-wrapper" aria-hidden="true">
          <span className="hint-text">点击预览需求表</span>
          <svg className="hint-arrow" viewBox="0 0 40 40" fill="none">
            <path
              d="M35 5C35 5 15 5 10 25M10 25 3 18M10 25l8-3"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        <div className="folder-container" aria-hidden="true">
          <svg className="folder-back" viewBox="0 0 50 40" fill="none">
            <path
              d="M0 4C0 1.79 1.79 0 4 0h12.5c1.2 0 2.32.54 3.05 1.47l2.85 3.6c.73.93 1.85 1.47 3.05 1.47H46c2.21 0 4 1.79 4 4v25.46c0 2.21-1.79 4-4 4H4c-2.21 0-4-1.79-4-4V4Z"
              fill="currentColor"
            />
          </svg>

          {FOLDER_FILES.map(({ className, label, tag }) => (
            <div className={`file ${className}`} key={className}>
              <div className="shine" />
              <div className="file-text">{label}</div>
              <div className="file-tag">{tag}</div>
            </div>
          ))}

          <div className="folder-front-wrapper">
            <svg className="folder-front" viewBox="0 0 50 34" fill="none">
              <path
                d="M0 4C0 1.79 1.79 0 4 0h42c2.21 0 4 1.79 4 4v26c0 2.21-1.79 4-4 4H4c-2.21 0-4-1.79-4-4V4Z"
                fill="currentColor"
              />
            </svg>
            <div className="folder-label" />
          </div>
        </div>
      </div>
    </StyledWrapper>
  )
}

const StyledWrapper = styled.div`
  display: grid;
  width: 100%;
  height: 100%;
  min-height: 0;
  place-items: center;

  .folder-card {
    position: relative;
    display: flex;
    width: 190px;
    height: 154px;
    align-items: center;
    justify-content: center;
    perspective: 1200px;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    /* 内部文件卡片均为绝对定位像素值,整体等比缩放而非逐一改值 */
    transform-origin: center;
  }

  .folder-card.is-dragging { cursor: grabbing; }

  .folder-card:focus-visible {
    outline: 2px solid rgb(var(--color-accent));
    outline-offset: 5px;
    border-radius: 8px;
  }

  .folder-toggle {
    position: absolute;
    width: 1px;
    height: 1px;
    opacity: 0;
    pointer-events: none;
  }

  .hint-wrapper {
    position: absolute;
    top: -8px;
    right: -10px;
    z-index: 100;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1px;
    color: rgb(var(--color-accent));
    pointer-events: none;
    transform: rotate(4deg);
    transition: opacity .3s ease, transform .3s ease;
  }

  .hint-text {
    font-size: 10px;
    font-weight: 800;
    letter-spacing: .04em;
    white-space: nowrap;
  }

  .hint-arrow {
    width: 28px;
    height: 28px;
  }

  .folder-toggle:checked ~ .hint-wrapper {
    opacity: 0;
    transform: translateY(-8px) rotate(4deg);
  }

  .folder-container {
    position: relative;
    width: 100%;
    height: 100%;
    transform-style: preserve-3d;
    transition: transform .6s cubic-bezier(.23, 1, .32, 1);
    backface-visibility: hidden;
    will-change: transform;
  }

  .folder-toggle:checked ~ .folder-container {
    transform: rotateX(10deg) rotateY(-5deg);
  }

  .folder-back,
  .folder-front {
    position: absolute;
    left: 0;
    width: 100%;
    filter: drop-shadow(0 8px 13px rgb(0 0 0 / .34));
  }

  /* 后层更深:露出的部分与前层形成层次 */
  .folder-back { bottom: 0; color: rgb(var(--color-accent-strong)); }

  /* 前层半透明玻璃盖板:透出内部文件卡片,标题与徽章保持不透明(兄弟元素不受影响) */
  .folder-front {
    bottom: 0;
    height: 100%;
    color: rgb(var(--color-accent));
    opacity: .55;
    backdrop-filter: blur(1px);
  }

  .folder-front-wrapper::after {
    position: absolute;
    inset: 0 0 -4px;
    border-radius: 8px;
    box-shadow: inset 0 1px 1px rgb(255 255 255 / .35);
    content: '';
    pointer-events: none;
  }

  .folder-front-wrapper {
    position: absolute;
    bottom: -4px;
    z-index: 90;
    width: 100%;
    height: 129px;
    transform-origin: bottom;
    transition: transform .5s cubic-bezier(.175, .885, .32, 1.275);
  }

  .folder-toggle:checked ~ .folder-container .folder-front-wrapper {
    transform: rotateX(-50deg);
  }

  .folder-label {
    position: absolute;
    top: 8px;
    left: 12px;
    width: 34px;
    height: 4px;
    border-radius: 10px;
    background: rgb(255 255 255 / .56);
  }

  .file {
    position: absolute;
    bottom: 5px;
    left: 10%;
    z-index: 0;
    width: 80%;
    height: 98px;
    overflow: hidden;
    border-radius: 6px;
    box-shadow: inset 0 1px 1px rgb(255 255 255 / .3), 0 4px 12px rgb(0 0 0 / .3);
    transition: transform .6s cubic-bezier(.68, -.55, .265, 1.55), filter .25s ease;
  }

  .file-1 { z-index: 25; background: rgb(var(--color-accent)); transition-delay: .15s; }
  .file-2 { z-index: 24; background: rgb(var(--color-done)); transition-delay: .1s; }
  .file-3 { z-index: 23; background: rgb(var(--color-warning)); transition-delay: .05s; }
  .file-4 { z-index: 22; background: rgb(var(--color-accent-strong)); transition-delay: .02s; }
  .file-5 { z-index: 21; background: rgb(var(--color-secondary)); }

  .folder-toggle:checked ~ .folder-container .file-1 { transform: translateY(-78px) rotate(-10deg) translateX(-15px) translateZ(20px); }
  .folder-toggle:checked ~ .folder-container .file-2 { transform: translateY(-61px) rotate(8deg) translateX(18px) translateZ(10px); }
  .folder-toggle:checked ~ .folder-container .file-3 { transform: translateY(-45px) rotate(-15deg) translateX(-8px); }
  .folder-toggle:checked ~ .folder-container .file-4 { transform: translateY(-29px) rotate(12deg) translateX(12px); }
  .folder-toggle:checked ~ .folder-container .file-5 { transform: translateY(-12px) rotate(-5deg); }

  .shine {
    position: absolute;
    top: 0;
    left: -100%;
    width: 50%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgb(255 255 255 / .35), transparent);
    transform: skewX(-20deg);
  }

  .folder-toggle:checked ~ .folder-container .shine {
    left: 150%;
    transition: left .8s ease-in-out;
    transition-delay: .3s;
  }

  .file-text {
    padding: 12px;
    color: #fff;
    font-size: 10px;
    font-weight: 800;
    text-shadow: 0 1px 3px rgb(0 0 0 / .2);
    opacity: 0;
    transform: translateY(5px);
    transition: opacity .3s ease .4s, transform .3s ease .4s;
  }

  .folder-toggle:checked ~ .folder-container .file-text {
    opacity: 1;
    transform: translateY(0);
  }

  .file-tag {
    position: absolute;
    right: 8px;
    bottom: 8px;
    padding: 3px 6px;
    border-radius: 4px;
    color: rgb(255 255 255 / .9);
    background: rgb(0 0 0 / .38);
    font-size: 7px;
    font-weight: 700;
    opacity: 0;
    transform: translateX(10px);
    transition: opacity .3s ease .4s, transform .3s ease .4s;
  }

  .folder-toggle:checked ~ .folder-container .file-tag {
    opacity: 1;
    transform: translateX(0);
  }

  @media (prefers-reduced-motion: reduce) {
    .folder-container,
    .folder-front-wrapper,
    .file,
    .file-text,
    .file-tag,
    .shine,
    .hint-wrapper {
      animation: none;
      transition: none;
    }
  }
`
