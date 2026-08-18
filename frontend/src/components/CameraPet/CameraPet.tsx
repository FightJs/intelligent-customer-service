import { useEffect, useMemo, useRef, useState } from 'react'
import { useDraggable } from '../../hooks/useDraggable'
import { useZStack } from '../../hooks/useZStack'
import type { CameraPetActivity } from './types'
import './CameraPet.css'

type DragDirection = 'up' | 'down' | 'left' | 'right'
type CameraPetAction = CameraPetActivity | 'click' | 'wave' | `move-${DragDirection}`

const ACTION_LABELS: Record<CameraPetAction, string> = {
  idle: '待机',
  click: '拍照回应',
  wave: '挥手',
  'move-up': '向上移动',
  'move-down': '向下移动',
  'move-left': '向左移动',
  'move-right': '向右移动',
  thinking: '思考中',
  output: '输出内容',
  waiting: '等待中',
}

interface CameraPetProps {
  activity?: CameraPetActivity
}

export default function CameraPet({ activity = 'idle' }: CameraPetProps) {
  const bounds = useMemo(() => ({
    width: 168,
    minHeight: 176,
    topMargin: 56,
    margin: 8,
  }), [])
  const { pos, dragging, onDragStart } = useDraggable({
    storageKey: 'camera-pet.pos',
    defaultPos: { x: 16, y: 96 },
    bounds,
  })
  const { z, bringToFront } = useZStack({ id: 'camera-pet', defaultZ: 30 })
  const [overrideAction, setOverrideAction] = useState<'click' | 'wave' | null>(null)
  const [dragDirection, setDragDirection] = useState<DragDirection | null>(null)
  const overrideTimerRef = useRef<number | null>(null)
  const dragOriginRef = useRef(pos)
  const previousPosRef = useRef(pos)

  useEffect(() => () => {
    if (overrideTimerRef.current !== null) window.clearTimeout(overrideTimerRef.current)
  }, [])

  useEffect(() => {
    if (!dragging) {
      previousPosRef.current = pos
      setDragDirection(null)
      return
    }

    const previous = previousPosRef.current
    const dx = pos.x - previous.x
    const dy = pos.y - previous.y
    if (Math.hypot(dx, dy) > 1) {
      setDragDirection(
        Math.abs(dx) > Math.abs(dy)
          ? (dx > 0 ? 'right' : 'left')
          : (dy > 0 ? 'down' : 'up'),
      )
    }
    previousPosRef.current = pos
  }, [dragging, pos])

  function triggerAction(action: 'click' | 'wave') {
    if (overrideTimerRef.current !== null) window.clearTimeout(overrideTimerRef.current)
    setOverrideAction(action)
    overrideTimerRef.current = window.setTimeout(
      () => setOverrideAction(null),
      action === 'click' ? 900 : 1200,
    )
  }

  function handleMouseDown(event: React.MouseEvent<HTMLButtonElement>) {
    dragOriginRef.current = pos
    bringToFront()
    onDragStart(event)
  }

  function hasDragged() {
    const origin = dragOriginRef.current
    return Math.hypot(pos.x - origin.x, pos.y - origin.y) > 6
  }

  const action: CameraPetAction = dragging && dragDirection
    ? `move-${dragDirection}`
    : overrideAction ?? activity

  return (
    <div
      className={`camera-pet-shell camera-pet-action-${action}${dragging ? ' is-dragging' : ''}`}
      style={{ transform: `translate3d(${pos.x}px, ${pos.y}px, 0)`, zIndex: z }}
    >
      <button
        type="button"
        className="camera-pet-button"
        onMouseDown={handleMouseDown}
        onClick={() => {
          if (!hasDragged()) triggerAction('click')
        }}
        onDoubleClick={() => {
          if (!hasDragged()) triggerAction('wave')
        }}
        aria-label={`镜头小摄，当前状态：${ACTION_LABELS[action]}。拖拽移动，单击拍照回应，双击挥手。`}
        title="拖拽移动，单击拍照回应，双击挥手"
      >
        <svg className="camera-pet-svg" viewBox="0 0 240 240" role="img" aria-label="镜头小摄">
          <defs>
            <linearGradient id="cameraPetGradient" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#3d9b88" />
              <stop offset="1" stopColor="#1f7a5a" />
            </linearGradient>
          </defs>
          <g className="camera-pet-mover">
            <g className="camera-pet-legs">
              <path className="camera-pet-leg camera-pet-leg-left" d="M86 170 L80 201" />
              <path className="camera-pet-leg camera-pet-leg-right" d="M132 170 L137 201" />
              <path className="camera-pet-feet" d="M73 201 H89 M129 201 H145" />
            </g>
            <g className="camera-pet-body-nod">
              <path className="camera-pet-handle" d="M88 91 V70 Q88 58 100 58 H132 Q144 58 144 70 V91" />
              <path className="camera-pet-arm camera-pet-arm-left" d="M58 129 Q39 139 43 160" />
              <path className="camera-pet-arm camera-pet-arm-right" d="M190 147 Q207 154 202 172" />
              <rect className="camera-pet-body" x="56" y="88" width="122" height="82" rx="22" />
              <rect className="camera-pet-screen" x="75" y="106" width="58" height="43" rx="13" />
              <g className="camera-pet-face">
                <g className="camera-pet-eyes">
                  <circle className="camera-pet-eye camera-pet-eye-left" cx="94" cy="123" r="5.5" />
                  <circle className="camera-pet-eye camera-pet-eye-right" cx="116" cy="123" r="5.5" />
                  <path className="camera-pet-wink-eye" d="M88 123 Q94 118 100 123" />
                </g>
                <path className="camera-pet-mouth camera-pet-mouth-default" d="M96 137 Q105 143 114 137" />
                <path className="camera-pet-playful-mouth" d="M94 136 Q105 148 116 136" />
              </g>
              <g className="camera-pet-output-lines">
                <rect className="camera-pet-output-line camera-pet-output-line-1" x="83" y="114" width="42" height="5" rx="2.5" />
                <rect className="camera-pet-output-line camera-pet-output-line-2" x="83" y="126" width="34" height="5" rx="2.5" />
                <rect className="camera-pet-output-line camera-pet-output-line-3" x="83" y="138" width="45" height="5" rx="2.5" />
              </g>
              <g className="camera-pet-lens">
                <circle className="camera-pet-lens-outer" cx="169" cy="129" r="36" />
                <circle className="camera-pet-lens-ring" cx="169" cy="129" r="27" />
                <circle className="camera-pet-lens-glass" cx="169" cy="129" r="18" />
                <circle className="camera-pet-lens-highlight" cx="163" cy="121" r="6" />
              </g>
              <circle className="camera-pet-photo-flash" cx="169" cy="129" r="43" />
              <g className="camera-pet-sparkles" aria-hidden="true">
                <path className="camera-pet-sparkle camera-pet-sparkle-1" d="M205 76 L208 84 L216 87 L208 90 L205 98 L202 90 L194 87 L202 84 Z" />
                <path className="camera-pet-sparkle camera-pet-sparkle-2" d="M212 151 L214.5 157 L221 159.5 L214.5 162 L212 168 L209.5 162 L203 159.5 L209.5 157 Z" />
                <path className="camera-pet-sparkle camera-pet-sparkle-3" d="M141 67 L143 72 L148 74 L143 76 L141 81 L139 76 L134 74 L139 72 Z" />
              </g>
              <circle className="camera-pet-record-light" cx="148" cy="83" r="6" />
            </g>
          </g>
        </svg>
      </button>
    </div>
  )
}
