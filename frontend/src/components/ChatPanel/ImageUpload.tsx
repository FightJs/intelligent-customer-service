import { useRef } from 'react'
import type { FieldValue } from '../../types/schema'

interface Props {
  value: FieldValue
  onChange: (v: FieldValue) => void
}

export default function ImageUpload({ value, onChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  if (value.type !== 'image') return null
  const files = value.value

  function add() {
    const fake = `photo_${files.length + 1}.jpg`
    onChange({ type: 'image', value: [...files, fake] })
  }

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={add}
        className="w-full border border-dashed border-idle rounded-card px-3 py-3.5 text-muted text-xs hover:border-accent hover:text-secondary transition-colors"
      >
        点击或拖拽上传 · 多张更佳
      </button>
      {value.value.length > 0 && (
        <div className="text-secondary text-[10px] mt-1">已添加 {value.value.length} 张占位图</div>
      )}
      <input ref={inputRef} type="file" className="hidden" />
    </div>
  )
}
