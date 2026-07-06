import { useState } from 'react'
import { useFormState } from '../../state/FormContext'
import type { FieldValue } from '../../types/schema'

const PACKAGES = [
  { value: 'basic', label: '基础套餐', price: 5000 },
  { value: 'standard', label: '标准套餐', price: 15000 },
  { value: 'full', label: '全包套餐', price: 30000 },
]

function readText(v: FieldValue | undefined): string {
  if (v && v.type === 'text') return v.value
  return ''
}

export default function OrderForm() {
  const { state } = useFormState()
  const customerSec = state.sections.customer
  const initialName = readText(customerSec.fields.brand)
  const initialPhone = readText(customerSec.fields.phone)

  const [name, setName] = useState(initialName)
  const [phone, setPhone] = useState(initialPhone)
  const [pkg, setPkg] = useState('standard')
  const [note, setNote] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [orderNo, setOrderNo] = useState('')

  const selectedPkg = PACKAGES.find((p) => p.value === pkg)!
  const totalPrice = selectedPkg.price

  function submit() {
    const rand = Math.floor(1000 + Math.random() * 9000)
    setOrderNo(`ORD-${rand}`)
    setSubmitted(true)
  }

  const inputCls = 'w-full bg-base border border-idle rounded px-3 py-2 text-sm text-primary placeholder:text-muted outline-none focus:border-accent'

  return (
    <div className="bg-surface rounded-card p-4">
      <div className="text-secondary text-xs mb-3">订单信息</div>

      <div className="mb-3">
        <label className="block text-muted text-[11px] mb-1">客户名</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={submitted}
          className={inputCls}
        />
      </div>

      <div className="mb-3">
        <label className="block text-muted text-[11px] mb-1">联系电话</label>
        <input
          type="text"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          disabled={submitted}
          className={inputCls}
        />
      </div>

      <div className="mb-3">
        <label className="block text-muted text-[11px] mb-1">服务套餐</label>
        <select
          value={pkg}
          onChange={(e) => setPkg(e.target.value)}
          disabled={submitted}
          className={inputCls}
        >
          {PACKAGES.map((p) => (
            <option key={p.value} value={p.value}>{p.label} · ¥{p.price}</option>
          ))}
        </select>
      </div>

      <div className="mb-3">
        <label className="block text-muted text-[11px] mb-1">预估总价</label>
        <input
          type="text"
          value={`¥ ${totalPrice.toLocaleString()}`}
          readOnly
          className={`${inputCls} opacity-70`}
        />
      </div>

      <div className="mb-4">
        <label className="block text-muted text-[11px] mb-1">备注</label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          disabled={submitted}
          rows={2}
          placeholder="特殊要求..."
          className={`${inputCls} resize-none`}
        />
      </div>

      {submitted && (
        <div className="mb-3 text-done text-xs flex items-center gap-1.5">
          <span>✓</span>
          <span>订单 {orderNo} 已发送</span>
        </div>
      )}

      <button
        type="button"
        onClick={submit}
        disabled={submitted}
        className={`w-full py-2.5 rounded-card text-sm font-semibold transition-colors ${
          submitted ? 'bg-done text-base cursor-default' : 'bg-accent text-white hover:bg-accent'
        }`}
      >
        {submitted ? '✓ 已发送' : '发送订单'}
      </button>
    </div>
  )
}
