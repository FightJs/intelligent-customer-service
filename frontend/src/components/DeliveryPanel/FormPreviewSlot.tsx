import { useRef, useState } from 'react'
import styled from 'styled-components'
import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import { filledCount, makeSummary } from '../../utils/summary'

interface FormPreviewSlotProps {
  onPreview?: () => void
}

const FILE_ICONS = [
  <svg key="img" className="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <rect x={3} y={3} width={18} height={18} rx={2} ry={2} />
    <circle cx="8.5" cy="8.5" r="1.5" />
    <polyline points="21 15 16 10 5 21" />
  </svg>,
  <svg key="video" className="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <polygon points="23 7 16 12 23 17 23 7" />
    <rect x={1} y={5} width={15} height={14} rx={2} ry={2} />
  </svg>,
  <svg key="code" className="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <polyline points="16 18 22 12 16 6" />
    <polyline points="8 6 2 12 8 18" />
  </svg>,
  <svg key="pdf" className="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1={16} y1={13} x2={8} y2={13} />
    <line x1={16} y1={17} x2={8} y2={17} />
    <polyline points="10 9 9 9 8 9" />
  </svg>,
  <svg key="ppt" className="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <rect x={2} y={3} width={20} height={14} rx={2} ry={2} />
    <line x1={8} y1={21} x2={16} y2={21} />
    <line x1={12} y1={17} x2={12} y2={21} />
  </svg>,
]

const CARD_TOP = 66
const DRAG_THRESHOLD = 4

interface DragState {
  pointerId: number
  startX: number
  startY: number
  baseX: number
  baseY: number
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value))
}

export default function FormPreviewSlot({ onPreview }: FormPreviewSlotProps) {
  const { state } = useFormState()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [dragging, setDragging] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const cardRef = useRef<HTMLDivElement>(null)
  const dragRef = useRef<DragState | null>(null)
  const movedRef = useRef(false)

  function handlePointerDown(e: React.PointerEvent<HTMLDivElement>) {
    const target = e.target as HTMLElement
    if (target.closest('.folder-search') || target.closest('.file')) return
    dragRef.current = {
      pointerId: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      baseX: offset.x,
      baseY: offset.y,
    }
    movedRef.current = false
    e.currentTarget.setPointerCapture(e.pointerId)
    setDragging(true)
  }

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    const drag = dragRef.current
    if (!drag || e.pointerId !== drag.pointerId) return
    const dx = e.clientX - drag.startX
    const dy = e.clientY - drag.startY
    if (!movedRef.current && Math.hypot(dx, dy) > DRAG_THRESHOLD) {
      movedRef.current = true
    }
    if (!movedRef.current) return
    const container = containerRef.current
    const card = cardRef.current
    if (!container || !card) return
    // 只在本列范围内移动：水平居中基准 ± 可用宽度的一半
    const maxX = Math.max(0, (container.clientWidth - card.offsetWidth) / 2)
    // 顶部保留 66px 展开空间，向下不越过本行，避免盖住交付物卡片
    const maxY = Math.max(0, container.clientHeight - CARD_TOP - card.offsetHeight)
    setOffset({
      x: clamp(drag.baseX + dx, -maxX, maxX),
      y: clamp(drag.baseY + dy, 0, maxY),
    })
  }

  function endDrag(e: React.PointerEvent<HTMLDivElement>) {
    if (dragRef.current && e.pointerId === dragRef.current.pointerId) {
      dragRef.current = null
      setDragging(false)
    }
  }

  function consumeClickIfDragged() {
    if (movedRef.current) {
      movedRef.current = false
      return true
    }
    return false
  }

  const progress = SECTIONS.reduce(
    (result, def) => {
      const count = filledCount(state.sections[def.id], def)
      return { filled: result.filled + count.filled, total: result.total + count.total }
    },
    { filled: 0, total: 0 },
  )

  // 取前 5 个 section 作为文件夹里的文件（真实标题 + 摘要）
  const files = SECTIONS.slice(0, 5)
    .map((def) => {
      const title = def.title.split('、')[1] ?? def.title
      const summary = makeSummary(state.sections[def.id], def)
      return { id: def.id, title, summary }
    })
    .filter((f) => {
      const q = query.trim().toLowerCase()
      if (!q) return true
      return f.title.toLowerCase().includes(q) || f.summary.toLowerCase().includes(q)
    })

  function toggle() {
    setOpen((v) => !v)
  }

  return (
    <StyledWrapper ref={containerRef}>
      <div
        ref={cardRef}
        className={`folder-card${open ? ' is-open' : ''}${dragging ? ' is-dragging' : ''}`}
        role="button"
        tabIndex={0}
        aria-expanded={open}
        aria-label="预览需求表"
        style={{
          left: `calc(50% + ${offset.x}px)`,
          top: `calc(${CARD_TOP}px + ${offset.y}px)`,
        }}
        onClick={(e) => {
          if (consumeClickIfDragged()) {
            e.preventDefault()
            return
          }
          toggle()
        }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            toggle()
          }
        }}
      >
        <input
          type="checkbox"
          className="folder-toggle"
          checked={open}
          onChange={toggle}
          readOnly
          aria-hidden="true"
          tabIndex={-1}
        />
        <div className="hint-wrapper">
          <span className="hint-text">点击打开</span>
          <svg className="hint-arrow" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M 35 5 C 35 5, 15 5, 10 25 M 10 25 L 3 18 M 10 25 L 18 22" stroke="#60a5fa" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <div className="folder-container">
          <svg className="folder-back" viewBox="0 0 50 40" fill="none">
            <path d="M0 4C0 1.79086 1.79086 0 4 0H16.524C17.721 0 18.8415 0.54051 19.574 1.4673L22.426 5.0654C23.1585 5.99219 24.279 6.5327 25.476 6.5327H46C48.2091 6.5327 50 8.32356 50 10.5327V36C50 38.2091 48.2091 40 46 40H4C1.79086 40 0 38.2091 0 36V4Z" fill="#0056b3" />
          </svg>
          <div className="folder-search" onClick={(e) => e.stopPropagation()}>
            <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth={3}>
              <circle cx={11} cy={11} r={8} />
              <line x1={21} y1={21} x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              placeholder="搜索板块…"
              className="search-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          {files.map((f, i) => (
            <div
              key={f.id}
              className={`file file-${i + 1}`}
              role="button"
              tabIndex={0}
              aria-label={`预览${f.title}`}
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                if (consumeClickIfDragged()) return
                onPreview?.()
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  e.stopPropagation()
                  onPreview?.()
                }
              }}
            >
              <div className="shine" />
              {FILE_ICONS[i % FILE_ICONS.length]}
              <div className="file-text">{f.title}</div>
              <div className="file-tag">{f.summary === '未采集' ? '未采集' : f.summary}</div>
            </div>
          ))}
          <div className="folder-front-wrapper">
            <svg className="folder-front" viewBox="0 0 50 34" fill="none">
              <path d="M0 4C0 1.79086 1.79086 0 4 0H46C48.2091 0 50 1.79086 50 4V30C50 32.2091 48.2091 34 46 34H4C1.79086 34 0 32.2091 0 30V4Z" fill="rgba(0, 123, 255, 0.65)" />
            </svg>
            <div className="folder-label" />
            <div className="counter">
              <div className="status-dot" />
              <span className="counter-label">已采集</span>
              <span className="counter-number">{progress.filled}/{progress.total}</span>
            </div>
          </div>
        </div>
      </div>
    </StyledWrapper>
  )
}

const StyledWrapper = styled.div`
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;

  .folder-card {
    width: 148px;
    height: 112px;
    perspective: 1200px;
    cursor: pointer;
    position: absolute;
    top: ${CARD_TOP}px;
    left: 50%;
    transform: translate(-50%, 0);
    touch-action: none;
    user-select: none;
    -webkit-user-select: none;
    -webkit-tap-highlight-color: transparent;
  }

  .folder-card.is-dragging {
    cursor: grabbing;
    transition: none;
  }

  .folder-card:focus-visible {
    outline: 2px solid #60a5fa;
    outline-offset: 4px;
    border-radius: 8px;
  }

  .folder-toggle {
    display: none;
  }

  /* hint text */
  .hint-wrapper {
    position: absolute;
    top: -34px;
    right: -10px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    transition:
      opacity 0.3s ease,
      transform 0.3s ease;
    pointer-events: none;
    z-index: 100;
    animation: floatHint 2.5s ease-in-out infinite;
  }

  .hint-text {
    font-family: "Inter", -apple-system, sans-serif;
    color: #60a5fa;
    font-size: 10px;
    font-weight: 900;
    text-decoration: underline;
    letter-spacing: 0.5px;
    white-space: nowrap;
    position: relative;
    right: -25px;
    top: 10px;
    transform: rotate(45deg);
  }
  .hint-arrow {
    height: 26px;
    width: 26px;
  }

  @keyframes floatHint {
    0%,
    100% {
      transform: translateY(0);
    }
    50% {
      transform: translateY(6px);
    }
  }

  .folder-toggle:checked ~ .hint-wrapper {
    opacity: 0;
    transform: translateY(-10px);
  }

  /* folder card logics are here */
  .folder-container {
    position: relative;
    width: 100%;
    height: 100%;
    transform-style: preserve-3d;
    transition: transform 0.6s cubic-bezier(0.23, 1, 0.32, 1);
    backface-visibility: hidden;
    will-change: transform;
  }

  .folder-toggle:checked ~ .folder-container {
    transform: rotateX(10deg) rotateY(-5deg);
  }

  .folder-back {
    position: absolute;
    bottom: 0;
    width: 100%;
    filter: drop-shadow(0 10px 20px rgba(0, 0, 0, 0.4));
  }

  .folder-front-wrapper {
    position: absolute;
    bottom: -7px;
    width: 100%;
    z-index: 90;
    transform-origin: bottom;
    transition: transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    border-radius: 12px;
  }

  .folder-label {
    position: absolute;
    top: 10px;
    left: 10px;
    width: 30px;
    height: 4px;
    background: rgba(255, 255, 255, 0.5);
    border-radius: 10px;
  }

  /* this counts files */
  .counter {
    position: absolute;
    top: -56px;
    right: 8px;
    background-color: #a18cd1;
    padding: 4px 8px;
    border-radius: 50px;
    display: flex;
    align-items: center;
    gap: 8px;
    box-shadow:
      0 10px 20px rgba(0, 0, 0, 0.3),
      inset 0 1px 1px rgba(255, 255, 255, 0.2);
    transform: scale(0) translateY(20px);
    opacity: 0;
    transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
    z-index: 100;
    pointer-events: auto;
  }

  .folder-toggle:checked ~ .folder-container .counter {
    transform: scale(1) translateY(0);
    opacity: 1;
    transition-delay: 0.2s;
  }

  .status-dot {
    width: 6px;
    height: 6px;
    background: #34d399;
    border-radius: 50%;
    position: relative;
    box-shadow: 0 0 10px #34d399;
  }

  .status-dot::after {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: #34d399;
    border-radius: 50%;
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0% {
      transform: scale(1);
      opacity: 1;
    }
    100% {
      transform: scale(3);
      opacity: 0;
    }
  }

  .counter-label {
    font-family: "Inter", sans-serif;
    font-size: 8px;
    font-weight: 800;
    color: black;
    text-transform: capitalize;
  }

  .counter-number {
    font-family: "Inter", sans-serif;
    font-size: 12px;
    font-weight: 900;
    color: #ffffff;
    text-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
  }

  .counter:hover {
    background: rgba(255, 255, 255, 0.2);
    border-color: #60a5fa;
    transform: scale(1.1) translateY(-5px) !important;
    cursor: help;
  }

  .counter:hover .counter-number {
    color: #60a5fa;
    transition: color 0.3s ease;
  }

  /* files with <hidden secrects /> */
  .file {
    position: absolute;
    bottom: 4px;
    left: 10%;
    width: 80%;
    height: 72px;
    border-radius: 6px;
    overflow: hidden;
    box-shadow:
      inset 0 1px 1px rgba(255, 255, 255, 0.3),
      0 4px 12px rgba(0, 0, 0, 0.3);
    transition: all 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55);
    z-index: 0;
  }

  .file:focus-visible {
    outline: 2px solid #60a5fa;
    outline-offset: 2px;
  }

  .file-1 {
    background: #ff5f6d;
    z-index: 25;
    transition-delay: 0.15s;
  }
  .file-2 {
    background: #ffc371;
    z-index: 24;
    transition-delay: 0.1s;
  }
  .file-3 {
    background: #4facfe;
    z-index: 23;
    transition-delay: 0.05s;
  }
  .file-4 {
    background: #00f2fe;
    z-index: 22;
    transition-delay: 0.02s;
  }
  .file-5 {
    background: #a18cd1;
    z-index: 21;
    transition-delay: 0s;
  }

  .shine {
    position: absolute;
    top: 0;
    left: -100%;
    width: 50%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
    transform: skewX(-20deg);
    transition: none;
  }

  .folder-toggle:checked ~ .folder-container .shine {
    left: 150%;
    transition: left 0.8s ease-in-out;
    transition-delay: 0.3s;
  }

  .file-text {
    font-family: "Inter", sans-serif;
    font-size: 8px;
    color: white;
    padding: 9px;
    font-weight: 800;
    text-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    opacity: 0;
    transform: translateY(5px);
    transition: all 0.3s ease 0.4s;
    max-width: calc(100% - 34px);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .folder-toggle:checked ~ .folder-container .file-text {
    opacity: 1;
    transform: translateY(0);
  }

  /* active state (click on card folder) */
  .folder-toggle:checked ~ .folder-container .folder-front-wrapper {
    transform: rotateX(-50deg);
  }

  .folder-toggle:checked ~ .folder-container .file-1 {
    transform: translateY(-58px) rotate(-10deg) translateX(-14px) translateZ(20px);
  }
  .folder-toggle:checked ~ .folder-container .file-2 {
    transform: translateY(-45px) rotate(8deg) translateX(16px) translateZ(10px);
  }
  .folder-toggle:checked ~ .folder-container .file-3 {
    transform: translateY(-33px) rotate(-15deg) translateX(-8px);
  }
  .folder-toggle:checked ~ .folder-container .file-4 {
    transform: translateY(-21px) rotate(12deg) translateX(12px);
  }
  .folder-toggle:checked ~ .folder-container .file-5 {
    transform: translateY(-9px) rotate(-5deg);
  }

  /*  Hover Interaction */
  .folder-toggle:checked ~ .folder-container .file:hover {
    cursor: pointer;
    filter: brightness(1.1);
  }

  .folder-toggle:checked ~ .folder-container .file-1:hover {
    transform: translateY(-66px) rotate(-10deg) translateX(-14px) translateZ(20px);
  }
  .folder-toggle:checked ~ .folder-container .file-2:hover {
    transform: translateY(-53px) rotate(8deg) translateX(16px) translateZ(10px);
  }
  .folder-toggle:checked ~ .folder-container .file-3:hover {
    transform: translateY(-41px) rotate(-15deg) translateX(-8px);
  }
  .folder-toggle:checked ~ .folder-container .file-4:hover {
    transform: translateY(-29px) rotate(12deg) translateX(12px);
  }
  .folder-toggle:checked ~ .folder-container .file-5:hover {
    transform: translateY(-17px) rotate(-5deg);
  }

  /* extras styles for files  */
  .file-icon {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 12px;
    height: 12px;
    color: rgba(255, 255, 255, 0.4);
    transition: color 0.3s ease;
  }

  .file-tag {
    position: absolute;
    bottom: 10px;
    right: 10px;
    background: rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    color: rgba(255, 255, 255, 0.9);
    font-family: "Inter", -apple-system, sans-serif;
    font-size: 6.5px;
    font-weight: 700;
    padding: 2px 5px;
    border-radius: 4px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    opacity: 0;
    transform: translateX(10px);
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    pointer-events: none;
    max-width: 70%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* when folder is OPEN and you HOVER a file */
  .folder-toggle:checked ~ .folder-container .file:hover .file-icon {
    color: rgba(255, 255, 255, 0.9);
  }
  .folder-toggle:checked ~ .folder-container .file-tag {
    opacity: 1;
  }

  /* search bar */
  .folder-search {
    position: absolute;
    top: -36px;
    left: 10%;
    width: 30px;
    height: 22px;
    background-color: #60a5fa;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-radius: 20px;
    display: flex;
    align-items: center;
    padding: 0 8px;
    transition: all 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);
    opacity: 0;
    z-index: 100;
    border: 1px solid rgba(255, 255, 255, 0.2);
  }

  .search-icon {
    width: 12px;
    height: 12px;
    flex-shrink: 0;
  }

  .search-input {
    background: transparent;
    border: none;
    color: #ffffff;
    font-family: "Inter", sans-serif;
    font-size: 9px;
    margin-left: 8px;
    outline: none;
    transition: width 0.4s ease;
  }
  .search-input::placeholder {
    color: #ffffff;
  }

  .folder-toggle:checked ~ .folder-container .folder-search {
    opacity: 1;
    top: -42px;
    width: 80%;
  }

  .folder-toggle:checked ~ .folder-container .folder-search:focus-within {
    width: 90%;
    background-color: #ff3b30;
  }

  .folder-toggle:checked ~ .folder-container .folder-search:focus-within .search-input {
    width: 100%;
  }
`
