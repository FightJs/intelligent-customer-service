import { useEffect, useState, type KeyboardEvent } from 'react'
import styled from 'styled-components'
import { SECTIONS } from '../../data/sections'

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

export default function FormPreviewSlot({ isPreviewOpen = false, onPreview }: FormPreviewSlotProps) {
  const [isOpen, setIsOpen] = useState(false)

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

  return (
    <StyledWrapper>
      <div
        className="folder-card"
        role="button"
        tabIndex={0}
        aria-label="预览需求表"
        onClickCapture={openPreview}
        onKeyDown={handleKeyDown}
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
          <span className="hint-text">点击查看</span>
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
              <svg className="file-icon" viewBox="0 0 24 24" fill="none">
                <path
                  d="M6 3h8l4 4v14H6V3Zm8 0v5h4M9 13h6M9 17h6"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
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
            <div className="folder-title">客户需求表</div>
            <div className="folder-hint">实时更新 · 点击查看</div>
            <div className="counter">
              <span className="status-dot" />
              <span className="counter-label">SECTIONS</span>
              <span className="counter-number">{String(SECTIONS.length).padStart(2, '0')}</span>
            </div>
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
  }

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
    color: #60a5fa;
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
    color: #1458b8;
    filter: drop-shadow(0 8px 13px rgb(0 0 0 / .34));
  }

  .folder-back { bottom: 0; }
  .folder-front { bottom: 0; height: 100%; }

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

  .folder-title,
  .folder-hint {
    position: absolute;
    left: 50%;
    width: max-content;
    transform: translateX(-50%);
    color: #fff;
    text-shadow: 0 1px 3px rgb(0 0 0 / .25);
  }

  .folder-title {
    top: 18px;
    font-size: 13px;
    font-weight: 800;
  }

  .folder-hint {
    top: 36px;
    font-size: 9px;
    font-weight: 600;
    opacity: .8;
  }

  .counter {
    position: absolute;
    top: -12px;
    right: -10px;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 7px;
    border-radius: 50px;
    color: #0b1220;
    background: #a9c7ff;
    box-shadow: 0 7px 14px rgb(0 0 0 / .22), inset 0 1px 1px rgb(255 255 255 / .3);
    transform: scale(0) translateY(20px);
    opacity: 0;
    transition: transform .5s cubic-bezier(.34, 1.56, .64, 1), opacity .5s ease;
  }

  .folder-toggle:checked ~ .folder-container .counter {
    transform: scale(1) translateY(0);
    opacity: 1;
    transition-delay: .2s;
  }

  .status-dot {
    position: relative;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #34d399;
    box-shadow: 0 0 8px #34d399;
  }

  .status-dot::after {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    background: #34d399;
    content: '';
    animation: pulse 2s infinite;
  }

  .counter-label { font-size: 7px; font-weight: 800; }
  .counter-number { color: #fff; font-size: 11px; font-weight: 900; }

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

  .file-1 { z-index: 25; background: #2563eb; transition-delay: .15s; }
  .file-2 { z-index: 24; background: #3b82f6; transition-delay: .1s; }
  .file-3 { z-index: 23; background: #4facfe; transition-delay: .05s; }
  .file-4 { z-index: 22; background: #1678d3; transition-delay: .02s; }
  .file-5 { z-index: 21; background: #1458b8; }

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

  .file-icon {
    position: absolute;
    top: 9px;
    right: 9px;
    width: 15px;
    height: 15px;
    color: rgb(255 255 255 / .52);
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

  @keyframes pulse {
    from { transform: scale(1); opacity: 1; }
    to { transform: scale(3); opacity: 0; }
  }

  @media (prefers-reduced-motion: reduce) {
    .folder-container,
    .folder-front-wrapper,
    .file,
    .counter,
    .file-text,
    .file-tag,
    .shine,
    .hint-wrapper {
      animation: none;
      transition: none;
    }
  }
`
