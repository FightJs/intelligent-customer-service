import { useEffect, useState } from 'react'
import type { SuggestionOption } from '../../api/client'

interface Props {
  options: SuggestionOption[]
  onPick: (option: SuggestionOption) => void
  onPickMany?: (options: SuggestionOption[]) => void
  multiple?: boolean
  disabled?: boolean
}

/** 输入框上方的预选项 chip 行（codex 风格）。点击触发 onPick，由父组件决定发什么。 */
export default function QuickChips({
  options,
  onPick,
  onPickMany,
  multiple = false,
  disabled,
}: Props) {
  const [selectedValues, setSelectedValues] = useState<string[]>([])
  const optionKey = options.map((option) => option.value).join('\u0000')

  useEffect(() => {
    setSelectedValues([])
  }, [multiple, optionKey])

  if (!options.length) return null

  const toggleOption = (option: SuggestionOption) => {
    if (!multiple) {
      onPick(option)
      return
    }
    setSelectedValues((current) => (
      current.includes(option.value)
        ? current.filter((value) => value !== option.value)
        : [...current, option.value]
    ))
  }

  const confirmSelection = () => {
    const selected = options.filter((option) => selectedValues.includes(option.value))
    if (selected.length === 0) return
    onPickMany?.(selected)
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          disabled={disabled}
          aria-pressed={multiple ? selectedValues.includes(o.value) : undefined}
          onClick={() => toggleOption(o)}
          className={`px-3 py-1.5 text-xs rounded-pill transition-colors disabled:opacity-40 ${
            selectedValues.includes(o.value)
              ? 'bg-accent text-white'
              : 'bg-active-surface text-secondary hover:bg-brand-soft hover:text-primary disabled:hover:bg-active-surface'
          }`}
        >
          {o.label}
        </button>
      ))}
      {multiple && (
        <button
          type="button"
          disabled={disabled || selectedValues.length === 0}
          onClick={confirmSelection}
          className="px-3 py-1.5 text-xs font-semibold rounded-pill bg-accent text-white transition-opacity disabled:opacity-40"
        >
          确认选择{selectedValues.length > 0 ? `（${selectedValues.length}）` : ''}
        </button>
      )}
    </div>
  )
}
