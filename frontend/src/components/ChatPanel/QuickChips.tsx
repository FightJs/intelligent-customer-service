import type { SuggestionOption } from '../../api/client'

interface Props {
  options: SuggestionOption[]
  onPick: (option: SuggestionOption) => void
  disabled?: boolean
}

/** 输入框上方的预选项 chip 行（codex 风格）。点击触发 onPick，由父组件决定发什么。 */
export default function QuickChips({ options, onPick, disabled }: Props) {
  if (!options.length) return null
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          disabled={disabled}
          onClick={() => onPick(o)}
          className="px-3 py-1.5 text-xs rounded-pill transition-colors bg-active-surface text-secondary hover:bg-brand-soft hover:text-primary disabled:opacity-40 disabled:hover:bg-active-surface"
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
