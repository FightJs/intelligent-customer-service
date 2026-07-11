import type { FieldDef, FieldValue } from '../../types/schema'

interface Props {
  def: FieldDef
  value: FieldValue
  onChange: (v: FieldValue) => void
}

export default function TableInput({ def, value, onChange }: Props) {
  if (value.type !== 'table') return null
  const columns = def.columns ?? []
  const rows = value.value

  function updateCell(rowIdx: number, colId: string, v: string) {
    const next = rows.map((row, i) =>
      i === rowIdx ? { ...row, [colId]: v } : row,
    )
    onChange({ type: 'table', value: next })
  }

  function addRow() {
    const emptyRow = Object.fromEntries(columns.map((c) => [c.id, '']))
    onChange({ type: 'table', value: [...rows, emptyRow] })
  }

  function removeRow(rowIdx: number) {
    onChange({ type: 'table', value: rows.filter((_, i) => i !== rowIdx) })
  }

  const inputCls =
    'w-full bg-base border border-idle rounded text-primary text-xs px-2 py-1 focus:border-accent outline-none placeholder:text-muted'

  return (
    <div className="mt-2 space-y-2 w-full">
      {rows.map((row, rowIdx) => (
        <div key={rowIdx} className="bg-surface rounded-card p-2 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-muted text-[10px]">第 {rowIdx + 1} 行</span>
            <button
              type="button"
              onClick={() => removeRow(rowIdx)}
              className="text-muted text-[10px] hover:text-primary"
            >
              删除
            </button>
          </div>
          {columns.map((col) => (
            <div key={col.id}>
              <label className="block text-muted text-[10px] mb-0.5">{col.label}</label>
              <input
                type="text"
                value={row[col.id] ?? ''}
                onChange={(e) => updateCell(rowIdx, col.id, e.target.value)}
                placeholder={col.placeholder}
                className={inputCls}
              />
            </div>
          ))}
        </div>
      ))}
      <button
        type="button"
        onClick={addRow}
        className="text-xs text-accent hover:underline"
      >
        + 添加一行设备
      </button>
    </div>
  )
}
