import { useEffect, useRef, useState } from 'react'
import { Search, X } from 'lucide-react'

interface SearchInputProps {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  /** 防抖延迟（ms），默认 350 */
  debounce?: number
}

/** 搜索框：输入即时更新本地 state，防抖后回调（避免每键一次都打后端）。 */
export default function SearchInput({
  value,
  onChange,
  placeholder = '搜索…',
  debounce = 350,
}: SearchInputProps) {
  const [local, setLocal] = useState(value)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 外部 value 变化时（如重置）同步本地
  useEffect(() => {
    setLocal(value)
  }, [value])

  function handleInput(v: string) {
    setLocal(v)
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => onChange(v), debounce)
  }

  // 卸载清定时器
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])

  return (
    <div className="relative flex-1 min-w-[180px]">
      <Search
        size={15}
        className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none"
      />
      <input
        type="text"
        value={local}
        onChange={(e) => handleInput(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-card bg-surface py-2 pl-9 pr-8 text-sm text-primary placeholder:text-muted outline-none ring-1 ring-idle focus:ring-accent"
      />
      {local && (
        <button
          type="button"
          onClick={() => handleInput('')}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-secondary"
          aria-label="清除"
        >
          <X size={14} />
        </button>
      )}
    </div>
  )
}
