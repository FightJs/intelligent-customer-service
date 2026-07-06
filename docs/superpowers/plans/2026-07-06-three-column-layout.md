# 三栏布局重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 2 栏布局（左 ChatPanel + 右 Dashboard）重构为 3 栏（左 ProgressPanel 只读进度 / 中 ChatPanel / 右 DeliveryPanel 交付物+订单），采集期 2 栏，完成时右栏滑入变 3 栏。

**Architecture:** 删除旧 Dashboard/FieldEditor/ReportPreview，新建 ProgressPanel（只读垂直列表）+ DeliveryPanel（方案概要+交付物+OrderForm）。App 持有 `showDelivery` state，由 ChatPanel 的 `onComplete` 回调触发右栏滑入。reducer/state/data/schema 全部复用不动。ChatPanel 仅一处改动：`onAllDone` 重命名为 `onComplete`。

**Tech Stack:** React 19 · TypeScript · Vite · Tailwind CSS（已有 tokens）· Vitest

## Global Constraints

- 工作目录：`A:\Intelligent Customer Service\livestream-cs-ui`（已有 git repo，11 commits，HEAD `79f1221`）
- git 路径：`C:\Program Files\Git\cmd\git.exe`（直接调用，PATH 可能未刷新）
- Tailwind tokens（来自 tailwind.config.js，必须使用，禁止 inline hex）：
  - 背景：`bg-base`(#0f172a) / `bg-surface`(#1e293b) / `bg-active-surface`(#172554)
  - 强调：`bg-accent`(#2563eb) / `bg-done`(#34d399) / `bg-idle`(#475569)
  - 文字：`text-primary`(#e2e8f0) / `text-secondary`(#94a3b8) / `text-muted`(#64748b)
  - 圆角：`rounded-card`(8px) / `rounded-bubble`(14px) / `rounded-pill`(18px)
- 例外：TopBar 的 SVG stroke 属性允许 inline hex（既有代码，不动）
- Commit 规范：Conventional Commits 前缀，中文 message
- 无注释代码规则（除非用户要求）
- 现有测试 16 个（summary 4 + chatController 7 + reducer 5）必须继续通过；本计划不删测试
- 视觉风格延续：深色科技

---

## File Structure

```
livestream-cs-ui/src/
├── components/
│   ├── ChatPanel/                    # 复用，仅 ChatPanel.tsx 改 prop 名
│   │   ├── ChatPanel.tsx             # MODIFY: onAllDone → onComplete
│   │   ├── MessageBubble.tsx         # 不动
│   │   ├── ChoiceCard.tsx            # 不动
│   │   ├── DimensionInput.tsx        # 不动
│   │   ├── ImageUpload.tsx           # 不动
│   │   └── chatController.ts         # 不动
│   ├── ProgressPanel/                # 新建
│   │   └── ProgressPanel.tsx         # 左栏只读列表
│   ├── DeliveryPanel/                # 新建
│   │   ├── DeliveryPanel.tsx         # 右栏容器（A 概要 + B 交付物 + C 订单）
│   │   └── OrderForm.tsx             # 订单表单子组件
│   ├── TopBar.tsx                    # 不动
│   ├── Dashboard/                    # 删除（整个目录）
│   │   ├── Dashboard.tsx
│   │   ├── SectionCard.tsx
│   │   └── CardExpanded.tsx
│   ├── FieldEditor.tsx               # 删除
│   └── ReportPreview.tsx             # 删除
├── App.tsx                           # MODIFY: 3 栏布局 + showDelivery + 滑入
├── state/                            # 不动
├── data/                             # 不动
├── types/                            # 不动
└── utils/                            # 不动
```

---

## Task 1: ProgressPanel 左栏只读列表

**Files:**
- Create: `src/components/ProgressPanel/ProgressPanel.tsx`
- Modify: 无（先建组件，App 接线在 Task 4）

**Interfaces:**
- Consumes: `useFormState()` → `{ state }`; `SECTIONS` from `../../data/sections`; `makeSummary(section, def)` from `../../utils/summary`; `SectionDef`, `SectionState` types
- Produces: `<ProgressPanel />` 组件，无 props；订阅 FormContext 渲染 11 节只读列表

- [ ] **Step 1: 创建目录与文件**

创建空文件 `src/components/ProgressPanel/ProgressPanel.tsx`。

- [ ] **Step 2: 写组件实现**

```tsx
import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import { makeSummary } from '../../utils/summary'

const STATUS_DOT: Record<string, string> = {
  pending: 'bg-idle',
  active: 'bg-accent',
  complete: 'bg-done',
}

export default function ProgressPanel() {
  const { state } = useFormState()

  return (
    <div className="h-full overflow-y-auto py-2">
      {SECTIONS.map((def) => {
        const sec = state.sections[def.id]
        const summary = makeSummary(sec, def)
        const isCurrent = state.currentSectionId === def.id
        return (
          <div
            key={def.id}
            className={`px-3 py-2 border-l-[3px] ${
              isCurrent ? 'border-accent bg-active-surface' : 'border-transparent'
            }`}
          >
            <div className="flex items-center gap-2">
              <span
                className={`inline-block w-2 h-2 rounded-full ${STATUS_DOT[sec.status]} ${
                  sec.status === 'active' ? 'animate-pulse' : ''
                }`}
              />
              <span className={`text-xs ${isCurrent ? 'text-primary' : 'text-secondary'}`}>
                {def.title}
              </span>
            </div>
            <div className={`text-[11px] mt-0.5 ml-4 truncate ${summary === '未采集' ? 'text-muted' : 'text-secondary'}`}>
              {summary}
            </div>
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 3: 验证编译**

```bash
cd "A:\Intelligent Customer Service\livestream-cs-ui"
npm run build
```

期望：0 错误（新文件未被引用，但 TS 会编译它；若 tsconfig 是 `noEmit`+引用检查，可能报"未使用"——这是正常的，因为 Task 4 才接线。如果 build 因此失败，临时在 App.tsx 加一行 `import ProgressPanel from './components/ProgressPanel/ProgressPanel'` 验证编译，验证后删掉）。

- [ ] **Step 4: 提交**

```bash
git add src/components/ProgressPanel/ProgressPanel.tsx
git commit -m "feat(progress): 左栏只读进度列表组件"
```

---

## Task 2: OrderForm 订单表单子组件

**Files:**
- Create: `src/components/DeliveryPanel/OrderForm.tsx`

**Interfaces:**
- Consumes: `useFormState()` 读 `state.sections.customer.fields.brand.value` 与 `state.sections.customer.fields.phone.value`（用于预填）
- Produces: `<OrderForm />` 组件，无 props；自管理本地 form state + submitted 状态

- [ ] **Step 1: 创建目录与文件**

创建 `src/components/DeliveryPanel/OrderForm.tsx`。

- [ ] **Step 2: 写组件实现**

```tsx
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
```

- [ ] **Step 3: 验证编译**

```bash
npm run build
```

期望：0 错误（同 Task 1 Step 3 的临时引用检查逻辑）。

- [ ] **Step 4: 提交**

```bash
git add src/components/DeliveryPanel/OrderForm.tsx
git commit -m "feat(order): 订单表单子组件（UI 模拟）"
```

---

## Task 3: DeliveryPanel 右栏容器（方案概要 + 交付物 + 订单）

**Files:**
- Create: `src/components/DeliveryPanel/DeliveryPanel.tsx`
- Consumes: Task 2 的 `OrderForm`

**Interfaces:**
- Consumes: `useFormState()`; `SECTIONS`; `makeSummary`; `OrderForm`（Task 2）
- Produces: `<DeliveryPanel />` 组件，无 props；垂直滚动 3 段

- [ ] **Step 1: 创建文件**

创建 `src/components/DeliveryPanel/DeliveryPanel.tsx`。

- [ ] **Step 2: 写组件实现**

```tsx
import { useFormState } from '../../state/FormContext'
import { makeSummary } from '../../utils/summary'
import type { SectionId } from '../../types/schema'
import OrderForm from './OrderForm'

const DELIVERABLES = ['场景设计说明', '设备参数清单', '多视角效果图', '向量化评分报告']

const OVERVIEW_SECTIONS: { id: SectionId; label: string }[] = [
  { id: 'customer', label: '客户' },
  { id: 'industry', label: '品类' },
  { id: 'venue', label: '面积' },
  { id: 'budget', label: '预算' },
  { id: 'goal', label: '交付时间' },
]

export default function DeliveryPanel() {
  const { state } = useFormState()

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {/* A. 方案概要 */}
      <section>
        <h3 className="text-secondary text-xs mb-2">方案概要</h3>
        <div className="grid grid-cols-2 gap-2">
          {OVERVIEW_SECTIONS.map(({ id, label }) => {
            const sec = state.sections[id]
            const def = OVERVIEW_SECTIONS.length // placeholder to use makeSummary
            return (
              <div key={id} className="bg-surface rounded-card p-2.5">
                <div className="text-muted text-[10px]">{label}</div>
                <div className="text-primary text-xs truncate">
                  {makeSummary(sec, require('../../data/sections').SECTIONS.find((s) => s.id === id)!)}
                </div>
              </div>
            )
          })}
        </div>
      </section>

      {/* B. 交付物 */}
      <section>
        <h3 className="text-secondary text-xs mb-2">交付物</h3>
        <div className="space-y-2">
          {DELIVERABLES.map((title) => (
            <div key={title}>
              <div className="text-muted text-[11px] mb-1">{title}</div>
              <div className="bg-surface rounded-card h-16 flex items-center justify-center text-muted text-xs">
                [ Agent 生成中 · 占位 ]
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* C. 订单 */}
      <section>
        <OrderForm />
      </section>
    </div>
  )
}
```

- [ ] **Step 3: 修正不规范的 require 调用**

上面用了 `require(...)` 是反模式（ESM 项目）。改为顶部 import `SECTIONS`：

最终文件顶部：
```tsx
import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import { makeSummary } from '../../utils/summary'
import type { SectionId } from '../../types/schema'
import OrderForm from './OrderForm'
```

A 段的 map 体改为：
```tsx
{OVERVIEW_SECTIONS.map(({ id, label }) => {
  const sec = state.sections[id]
  const def = SECTIONS.find((s) => s.id === id)!
  return (
    <div key={id} className="bg-surface rounded-card p-2.5">
      <div className="text-muted text-[10px]">{label}</div>
      <div className="text-primary text-xs truncate">
        {makeSummary(sec, def)}
      </div>
    </div>
  )
})}
```

删除 `const def = OVERVIEW_SECTIONS.length` 那行占位。

- [ ] **Step 4: 验证编译**

```bash
npm run build
```

期望：0 错误。

- [ ] **Step 5: 提交**

```bash
git add src/components/DeliveryPanel/DeliveryPanel.tsx
git commit -m "feat(delivery): 右栏交付物 + 订单容器"
```

---

## Task 4: ChatPanel prop 重命名 + App 3 栏布局 + 滑入

**Files:**
- Modify: `src/components/ChatPanel/ChatPanel.tsx`（`onAllDone` → `onComplete`）
- Modify: `src/App.tsx`（3 栏布局 + showDelivery + 删除旧 Dashboard/ReportPreview 引用）
- Delete: `src/components/Dashboard/Dashboard.tsx`, `SectionCard.tsx`, `CardExpanded.tsx`, `src/components/FieldEditor.tsx`, `src/components/ReportPreview.tsx`

**Interfaces:**
- Consumes: Task 1 ProgressPanel, Task 3 DeliveryPanel, 现有 ChatPanel/TopBar/FormProvider
- Produces: 完整 3 栏应用，采集期 2 栏，完成时右栏滑入

- [ ] **Step 1: 读当前 ChatPanel.tsx 与 App.tsx**

```bash
# 用 read 工具读取这两个文件，确认 onAllDone 的所有出现位置
```

`src/components/ChatPanel/ChatPanel.tsx` 当前行：
- 函数签名：`export default function ChatPanel({ onAllDone }: { onAllDone?: () => void })`
- 调用处：在 commitAndAdvance 的 else 分支 `onAllDone?.()`

`src/App.tsx` 当前行：
- `<ChatPanel onComplete={() => setShowReport(true)} />`（注：Task 8 fix 已把 onAllDone 改为不传，App 里现在是 `<ChatPanel />`；showReport 由 Dashboard 的 onGenerate 触发）

**确认实际代码再下手**——用 read 工具看真实文件内容。

- [ ] **Step 2: 修改 ChatPanel.tsx — onAllDone → onComplete**

把函数签名改为：
```tsx
export default function ChatPanel({ onComplete }: { onComplete?: () => void }) {
```

把调用处改为：
```tsx
else {
  dispatch({ type: 'complete' })
  setFinished(true)
  onComplete?.()
}
```

- [ ] **Step 3: 重写 App.tsx**

```tsx
import { useState } from 'react'
import TopBar from './components/TopBar'
import ChatPanel from './components/ChatPanel/ChatPanel'
import ProgressPanel from './components/ProgressPanel/ProgressPanel'
import DeliveryPanel from './components/DeliveryPanel/DeliveryPanel'
import { FormProvider } from './state/FormContext'

export default function App() {
  const [resetKey, setResetKey] = useState(0)
  const [showDelivery, setShowDelivery] = useState(false)

  return (
    <FormProvider key={resetKey}>
      <div className="h-full flex flex-col">
        <TopBar onReset={() => { setResetKey((k) => k + 1); setShowDelivery(false) }} />
        <div className="flex-1 flex overflow-hidden">
          {/* 左栏：进度（始终显示）*/}
          <div className={`${showDelivery ? 'w-[20%]' : 'w-[30%]'} border-r border-idle transition-all duration-300`}>
            <ProgressPanel />
          </div>
          {/* 中栏：聊天（始终显示）*/}
          <div className={`${showDelivery ? 'w-[40%]' : 'w-[70%]'} border-r border-idle transition-all duration-300`}>
            <ChatPanel onComplete={() => setShowDelivery(true)} />
          </div>
          {/* 右栏：交付物 + 订单（完成时滑入）*/}
          <div
            className={`bg-base overflow-hidden transition-all duration-300 ${
              showDelivery ? 'w-[40%]' : 'w-0'
            }`}
          >
            {showDelivery && <DeliveryPanel />}
          </div>
        </div>
      </div>
    </FormProvider>
  )
}
```

注意：
- `showDelivery` 同时控制三栏宽度的 flex/grid 比例 + 右栏是否渲染
- 用 `transition-all duration-300` 实现宽度过渡（左/中收窄 + 右栏展开）
- 右栏 `w-0 overflow-hidden` 时 DeliveryPanel 不渲染（避免内部组件在 0 宽时报错）
- 重新开始时 `setShowDelivery(false)` 重置

- [ ] **Step 4: 删除旧组件**

```bash
git rm src/components/Dashboard/Dashboard.tsx
git rm src/components/Dashboard/SectionCard.tsx
git rm src/components/Dashboard/CardExpanded.tsx
git rm src/components/FieldEditor.tsx
git rm src/components/ReportPreview.tsx
```

如果 Dashboard 目录变空，可保留空目录或 `rmdir`（git 不跟踪空目录，无需操作）。

- [ ] **Step 5: 验证编译**

```bash
npm run build
```

期望：0 错误。如果有"未使用导入"报错（比如 App.tsx 仍残留旧 import），删掉。

- [ ] **Step 6: 跑测试**

```bash
npm test
```

期望：16/16 通过（summary 4 + chatController 7 + reducer 5）。这些测试不涉及 UI 组件，不受影响。

- [ ] **Step 7: 启动验证**

```bash
npm run dev
```

手动验证：
1. 打开 http://localhost:5173
2. **采集期**：左栏（30%）显示 11 节进度列表，中栏（70%）是聊天，**无右栏**
3. 左栏当前节（customer）有蓝色左色条 + 高亮底色
4. 回答几个问题：左栏对应节的摘要更新，状态色点变化
5. 走完所有 20 步问答 → 右栏从右侧**滑入**（~300ms），变为 20/40/40 三栏
6. 右栏显示：方案概要（5 字段）+ 4 个交付物占位 + 订单表单（客户名/电话预填）
7. 订单表单选套餐 → 总价更新 → 点"发送订单" → 按钮变绿 ✓ + "订单 ORD-XXXX 已发送" + 表单只读
8. 点 TopBar"重新开始" → 全部清空，回到 2 栏采集态

Ctrl+C 停止。

- [ ] **Step 8: 提交**

```bash
git add -A
git commit -m "feat(layout): 三栏布局重构 + 右栏滑入 + 删除旧 Dashboard/ReportPreview"
```

---

## Task 5: README 更新与最终验收

**Files:**
- Modify: `livestream-cs-ui/README.md`

**Interfaces:** 无新接口

- [ ] **Step 1: 读现有 README**

用 read 工具读 `livestream-cs-ui/README.md`。

- [ ] **Step 2: 更新功能描述段**

把"功能"段从旧的（左聊天/右仪表盘/完成态报告）改为新的三栏描述：

```markdown
## 功能

- **左栏 · 采集进度**：11 节垂直列表，状态色点（灰未采集/蓝进行中/绿完成），当前节高亮，只读
- **中栏 · 对话采集**：AI 按脚本提问，气泡内嵌选项卡/尺寸输入/图片上传；多选·尺寸·图片支持累积后点"确认"再推进
- **右栏 · 交付物 + 订单**（采集完成后从右侧滑入）：
  - 方案概要：客户/品类/面积/预算/交付时间
  - 4 个交付物占位：场景设计/设备清单/效果图/评分报告
  - 订单表单：客户名/电话预填，套餐下拉，总价自动，发送订单（UI 模拟，不调后端）
- **顶部 TopBar**：环形完成度 + `X/47 已采集` + 重新开始
```

技术栈段、范围说明段、设计文档指针不变。

- [ ] **Step 3: 跑全部测试**

```bash
npm test
```

期望：16/16 通过。

- [ ] **Step 4: 跑构建**

```bash
npm run build
```

期望：0 错误。

- [ ] **Step 5: 启动完整走查**

```bash
npm run dev
```

按 spec §9 的验收标准逐项核对：
- [ ] 采集期：左 30% + 中 70%，无右栏
- [ ] 采集完成瞬间：右栏从右滑入（~300ms），变为 20/40/40 三栏
- [ ] 左栏 11 行列表，当前节高亮，状态色点正确
- [ ] 中栏聊天全流程不变（20 步问答、4 种卡片、确认按钮）
- [ ] 右栏方案概要显示 5 个关键字段
- [ ] 右栏 4 个交付物卡片占位
- [ ] 右栏订单表单：客户名/电话预填，套餐下拉，总价自动，发送按钮
- [ ] 点发送：按钮变绿 ✓ + "订单 #ORD-XXXX 已发送"，表单只读
- [ ] 重新开始：清空所有，回到 2 栏采集态

Ctrl+C 停止。

- [ ] **Step 6: 提交**

```bash
git add README.md
git commit -m "docs: 更新 README 为三栏布局"
```

---

## Self-Review 记录

**Spec 覆盖检查（对照 spec 各节）：**
- §2 视觉决策（3 栏/隐藏/滑入/只读/UI 模拟）→ Task 1+3+4 实现 ✓
- §3 整体布局（采集期 2 栏 / 完成期 3 栏 / 滑入 300ms）→ Task 4 App.tsx ✓
- §4 ProgressPanel（垂直列表/状态色点/当前节高亮/只读）→ Task 1 ✓
- §5 ChatPanel（复用 + onComplete）→ Task 4 Step 2 ✓
- §6 DeliveryPanel（A 概要 + B 交付物 + C 订单）→ Task 3 + Task 2 ✓
  - §6.A 方案概要 5 字段 → Task 3 OVERVIEW_SECTIONS ✓
  - §6.B 4 交付物占位 → Task 3 DELIVERABLES ✓
  - §6.C 订单字段 + 发送逻辑 → Task 2 OrderForm ✓
- §7 删除旧组件（Dashboard/FieldEditor/ReportPreview）→ Task 4 Step 4 ✓
- §8 技术改动清单 → 全部对齐 ✓
- §9 验收标准 → Task 5 Step 5 逐项核对 ✓

**Placeholder 扫描：** 所有 step 都有完整代码或具体命令，无 TBD/TODO。"确认实际代码再下手"是合理指引（让 implementer 用 read 工具核对真实文件，因为本计划写时基于推测）。

**类型一致性：**
- `onComplete?: () => void` — Task 4 定义，App.tsx 使用，一致 ✓
- `OrderForm` 无 props — Task 2 定义，Task 3 使用 `<OrderForm />`，一致 ✓
- `DeliveryPanel` 无 props — Task 3 定义，Task 4 App 使用 `<DeliveryPanel />`，一致 ✓
- `ProgressPanel` 无 props — Task 1 定义，Task 4 App 使用 `<ProgressPanel />`，一致 ✓
- `OVERVIEW_SECTIONS` 用 `SectionId` 类型 — Task 3 定义，与 schema.ts 一致 ✓
- `PACKAGES` price 字段 number — Task 2 定义，`totalPrice.toLocaleString()` 使用，一致 ✓

**已知风险（implementer 注意）：**
1. Task 1/2/3 新组件未被 App 引用前，`npm run build` 可能报"declared but never used"或通过（取决于 tsconfig `noUnusedLocals` 范围）。Step 3 已给出临时引用验证的指引。
2. Task 4 Step 3 的 App.tsx 用 `transition-all duration-300` + `w-0`/`w-[40%]` 切换实现滑入。如果 Tailwind 的 JIT 不识别动态拼接的 class（如 `w-[${pct}%]`），这里用的是完整字符串字面量（`w-[20%]`、`w-[30%]` 等），JIT 能识别。不要改成模板字符串拼接。
3. 右栏 `w-0 overflow-hidden` 时 DeliveryPanel 不渲染（`{showDelivery && <DeliveryPanel />}`）。如果先渲染再过渡，内部 useState 会初始化但不可见——不致命，但 OrderForm 的预填值会在组件首次挂载时锁定。本设计选择"完成后才挂载"，预填值正确。
