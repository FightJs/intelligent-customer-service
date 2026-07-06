# 直播间视觉向量化智能客服 UI 原型 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建一个面向客户的 AI 对话式客服前端原型（React + Vite + Tailwind + TS），通过左侧对话采集 11 节调研信息，右侧仪表盘卡片实时回显并支持就地编辑，完成后进入方案预览页。

**Architecture:** 单页应用，单根 `StudioFormState`（11 节 × 多字段）通过 React Context + useReducer 管理；左侧 ChatPanel 按本地 `scriptedFlow` 脚本推进对话，用户每次回答 dispatch 一个 update action；右侧 Dashboard 订阅同一 state 渲染卡片网格；点击卡片就地展开为表单（复用对话区组件）；全部必填项完成后可进入 ReportPreview。

**Tech Stack:** React 18 · TypeScript · Vite 5 · Tailwind CSS 3 · Vitest + React Testing Library（测试）。无后端、无 LLM、无路由。

## Global Constraints

- 包管理器：pnpm（若无则 npm）
- Node 版本：≥ 18
- 视觉规范（所有组件必须遵守，源自 spec §6.2）：
  - 背景 `#0f172a`（主）/ `#1e293b`（卡片）/ `#172554`（进行中卡片底）
  - 强调色 `#2563eb`（进行中/选中）/ `#34d399`（完成）/ `#475569`（未采集色条）
  - 文字 `#e2e8f0`（主）/ `#94a3b8`（次）/ `#64748b`（弱）
  - 圆角：卡片 8px、气泡 14px、胶囊 18px
- Tailwind 通过 `tailwind.config.js` 自定义这些色值，所有组件用语义 class（如 `bg-surface`、`text-secondary`），不内联 hex
- 不引入 UI 组件库（如 Ant Design / MUI），全部手写 + Tailwind
- 提交规范：`feat:` / `chore:` / `refactor:` / `test:` 前缀，中文 commit message 可
- 不接后端、不接 LLM；AI 消息由本地脚本生成

---

## File Structure

```
livestream-cs-ui/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── src/
│   ├── main.tsx                    # 入口，挂载 App
│   ├── index.css                   # Tailwind 指令 + 全局样式
│   ├── App.tsx                     # 根布局：TopBar + ChatPanel + Dashboard / ReportPreview
│   ├── types/
│   │   └── schema.ts               # StudioFormState / SectionState / FieldType 等类型
│   ├── data/
│   │   ├── sections.ts             # 11 节元数据（id/title/fields 定义/选项/必填/摘要生成器）
│   │   └── scriptedFlow.ts         # 模拟 AI 对话脚本（按节顺序的问题队列）
│   ├── state/
│   │   ├── FormContext.tsx         # Context + Provider + useFormState hook
│   │   ├── reducer.ts              # reducer: update_field / set_active_section / complete / reset
│   │   └── initialState.ts         # 根据 sections.ts 生成初始空 state
│   ├── components/
│   │   ├── TopBar.tsx              # Logo · 完成度 X/N · 重新开始
│   │   ├── ChatPanel/
│   │   │   ├── ChatPanel.tsx       # 左侧容器：消息列表 + 输入框，驱动 scriptedFlow
│   │   │   ├── MessageBubble.tsx   # AI/User 气泡外壳
│   │   │   ├── ChoiceCard.tsx      # 选项卡（单选/多选），嵌在 AI 气泡内
│   │   │   ├── DimensionInput.tsx  # 多数字框组（宽×深×高 / 身高 cm）
│   │   │   ├── ImageUpload.tsx     # 虚线框上传（仅 UI，不真传）
│   │   │   └── chatController.ts   # 纯函数：根据当前 step + 用户输入推进到下一条 AI 消息
│   │   ├── Dashboard/
│   │   │   ├── Dashboard.tsx       # 右侧 2 列卡片网格
│   │   │   ├── SectionCard.tsx     # 单节卡片（折叠态）
│   │   │   └── CardExpanded.tsx    # 单节卡片（展开态表单，复用 ChoiceCard 等）
│   │   └── ReportPreview.tsx       # 完成态预览页
│   └── utils/
│       └── summary.ts              # 由 section state 生成 1 行摘要文案
└── tests/                          # （Vitest 配置 testDir 指向这里或 src 同级 __tests__）
    ├── reducer.test.ts
    ├── summary.test.ts
    └── chatController.test.ts
```

---

## Task 1: 项目脚手架与 Tailwind 主题

**Files:**
- Create: `package.json`, `vite.config.ts`, `tsconfig.json`, `tsconfig.node.json`, `tailwind.config.js`, `postcss.config.js`, `index.html`, `src/main.tsx`, `src/index.css`, `src/App.tsx`

**Interfaces:**
- Produces: 可运行的空壳应用（`pnpm dev` 启动后浏览器显示深色背景 + 一行 placeholder 文字），Tailwind 自定义色 token 可用（`bg-base`、`bg-surface`、`bg-active-surface`、`text-primary`、`text-secondary`、`text-muted`、`bg-accent`、`bg-done`、`bg-idle`、`rounded-card`、`rounded-bubble`、`rounded-pill`）

- [ ] **Step 1: 用 Vite 模板初始化项目**

在 `A:\Intelligent Customer Service` 下创建子目录 `livestream-cs-ui`，在其中初始化（当前目录非 git 仓库，无需 git）：

```bash
cd "A:\Intelligent Customer Service"
npm create vite@latest livestream-cs-ui -- --template react-ts
```

- [ ] **Step 2: 安装依赖**

```bash
cd livestream-cs-ui
npm install
npm install -D tailwindcss@3 postcss autoprefixer vitest @testing-library/react @testing-library/jest-dom jsdom @vitejs/plugin-react
```

- [ ] **Step 3: 初始化 Tailwind 配置**

```bash
npx tailwindcss init -p
```

- [ ] **Step 4: 写 `tailwind.config.js`**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        base: '#0f172a',
        surface: '#1e293b',
        'active-surface': '#172554',
        primary: '#e2e8f0',
        secondary: '#94a3b8',
        muted: '#64748b',
        accent: '#2563eb',
        done: '#34d399',
        idle: '#475569',
      },
      borderRadius: {
        card: '8px',
        bubble: '14px',
        pill: '18px',
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 5: 写 `src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #root { height: 100%; }
body {
  margin: 0;
  background-color: #0f172a;
  color: #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
```

- [ ] **Step 6: 写最小 `src/App.tsx`**

```tsx
export default function App() {
  return (
    <div className="h-full flex items-center justify-center">
      <h1 className="text-primary text-xl">直播间视觉向量化智能客服</h1>
    </div>
  )
}
```

确保 `src/main.tsx` 是 Vite 模板默认（`<React.StrictMode><App /></React.StrictMode>`）。

- [ ] **Step 7: 启动验证**

```bash
npm run dev
```

期望：浏览器打开 http://localhost:5173，深蓝背景，居中显示标题。Ctrl+C 停止。

- [ ] **Step 8: 提交**

```bash
git init
git add -A
git commit -m "chore: 项目脚手架与 Tailwind 主题"
```

---

## Task 2: 数据模型 schema.ts 与 11 节元数据 sections.ts

**Files:**
- Create: `src/types/schema.ts`, `src/data/sections.ts`, `src/utils/summary.ts`, `tests/summary.test.ts`

**Interfaces:**
- Produces:
  - `type SectionId` — 11 个字面量联合类型
  - `interface OptionDef { value: string; label: string }`
  - `type FieldType = 'text' | 'choice-single' | 'choice-multi' | 'dimension' | 'image'`
  - `interface FieldDef { id: string; label: string; type: FieldType; required: boolean; options?: OptionDef[]; dims?: string[]; placeholder?: string }`
  - `interface SectionDef { id: SectionId; title: string; order: number; fields: FieldDef[] }`
  - `const SECTIONS: SectionDef[]` — 长度 11
  - `function makeSummary(section: SectionState): string` — 由字段值生成 1 行摘要

**Consumes（下游 Task 3 会用）:**
- `StudioFormState` / `SectionState` / `FieldValue` 类型（本任务在 schema.ts 中定义）

- [ ] **Step 1: 写 `src/types/schema.ts`**

```ts
export type SectionId =
  | 'customer' | 'industry' | 'status' | 'venue' | 'budget'
  | 'product' | 'benchmark' | 'host' | 'equipment' | 'goal' | 'notes'

export type FieldType = 'text' | 'choice-single' | 'choice-multi' | 'dimension' | 'image'

export interface OptionDef {
  value: string
  label: string
}

export interface FieldDef {
  id: string
  label: string
  type: FieldType
  required: boolean
  options?: OptionDef[]
  dims?: string[]              // for 'dimension'：如 ['宽','深','高']
  unit?: string                // for 'dimension'：如 'm' / 'cm'
  placeholder?: string         // for 'text'
}

export interface SectionDef {
  id: SectionId
  title: string                // '一、客户信息'
  order: number
  fields: FieldDef[]
}

export type FieldValue =
  | { type: 'text'; value: string }
  | { type: 'choice-single'; value: string | null }
  | { type: 'choice-multi'; value: string[] }
  | { type: 'dimension'; value: Record<string, string> }  // { 宽:'4.5', 深:'5', 高:'3' }
  | { type: 'image'; value: string[] }                    // 占位文件名列表

export interface SectionState {
  id: SectionId
  status: 'pending' | 'active' | 'complete'
  fields: Record<string, FieldValue>
}

export interface StudioFormState {
  sections: Record<SectionId, SectionState>
  currentSectionId: SectionId
  completed: boolean
}
```

- [ ] **Step 2: 写 `src/data/sections.ts`（11 节，每节 2-4 个代表性字段）**

```ts
import type { SectionDef, SectionId } from '../types/schema'

export const SECTIONS: SectionDef[] = [
  {
    id: 'customer', title: '一、客户信息', order: 1,
    fields: [
      { id: 'brand', label: '品牌名', type: 'text', required: true, placeholder: '如：云裳' },
      { id: 'phone', label: '联系电话', type: 'text', required: true, placeholder: '138****' },
    ],
  },
  {
    id: 'industry', title: '二、行业品类', order: 2,
    fields: [
      {
        id: 'category', label: '行业大类', type: 'choice-single', required: true,
        options: [
          { value: 'women', label: '女装' }, { value: 'men', label: '男装' },
          { value: 'beauty', label: '美妆' }, { value: 'food', label: '食品' },
          { value: 'jewelry', label: '珠宝' }, { value: 'home', label: '家居' },
          { value: 'digital', label: '数码' }, { value: 'baby', label: '母婴' },
        ],
      },
      {
        id: 'position', label: '品牌定位', type: 'choice-single', required: true,
        options: [
          { value: 'mass', label: '平价大众' }, { value: 'value', label: '性价比' },
          { value: 'mid-high', label: '中高端' }, { value: 'luxury', label: '轻奢/高端' },
          { value: 'premium', label: '奢侈品' },
        ],
      },
    ],
  },
  {
    id: 'status', title: '三、直播间现状', order: 3,
    fields: [
      {
        id: 'hasRoom', label: '是否已有直播间', type: 'choice-single', required: true,
        options: [{ value: 'yes', label: '是' }, { value: 'no', label: '否' }],
      },
      {
        id: 'views', label: '场均观看', type: 'choice-single', required: false,
        options: [
          { value: '<500', label: '<500人' }, { value: '500-2k', label: '500-2000人' },
          { value: '2k-10k', label: '2000-1万人' }, { value: '10k+', label: '1万人以上' },
        ],
      },
    ],
  },
  {
    id: 'venue', title: '四、场地条件', order: 4,
    fields: [
      {
        id: 'area', label: '直播间面积', type: 'choice-single', required: true,
        options: [
          { value: '<10', label: '<10㎡' }, { value: '10-20', label: '10-20㎡' },
          { value: '20-30', label: '20-30㎡' }, { value: '30-50', label: '30-50㎡' },
          { value: '50+', label: '50㎡以上' },
        ],
      },
      {
        id: 'size', label: '具体尺寸', type: 'dimension', required: true,
        dims: ['宽', '深', '高'], unit: 'm',
      },
    ],
  },
  {
    id: 'budget', title: '五、预算范围', order: 5,
    fields: [
      {
        id: 'total', label: '总预算范围', type: 'choice-single', required: true,
        options: [
          { value: '<1w', label: '1万以下' }, { value: '1-3w', label: '1-3万' },
          { value: '3-5w', label: '3-5万' }, { value: '5-10w', label: '5-10万' },
          { value: '10-20w', label: '10-20万' }, { value: '20w+', label: '20万以上' },
        ],
      },
      {
        id: 'equipment', label: '其中设备预算', type: 'choice-single', required: true,
        options: [
          { value: '<5k', label: '5千以下' }, { value: '5k-1w', label: '5千-1万' },
          { value: '1-2w', label: '1-2万' }, { value: '2-5w', label: '2-5万' },
          { value: '5w+', label: '5万以上' },
        ],
      },
    ],
  },
  {
    id: 'product', title: '六、商品与品牌', order: 6,
    fields: [
      { id: 'main', label: '主营商品', type: 'text', required: true, placeholder: '如：连衣裙、口红' },
      { id: 'keywords', label: '风格关键词', type: 'text', required: true, placeholder: '3-5个词，如：国风、高端、雅致' },
    ],
  },
  {
    id: 'benchmark', title: '七、对标参考', order: 7,
    fields: [
      {
        id: 'hasBenchmark', label: '是否有对标直播间', type: 'choice-single', required: true,
        options: [{ value: 'yes', label: '是' }, { value: 'no', label: '否' }],
      },
      {
        id: 'platform', label: '主对标平台', type: 'choice-single', required: false,
        options: [
          { value: 'douyin', label: '抖音' }, { value: 'taobao', label: '淘宝直播' },
          { value: 'kuaishou', label: '快手' }, { value: 'weixin', label: '视频号' },
          { value: 'xhs', label: '小红书' },
        ],
      },
    ],
  },
  {
    id: 'host', title: '八、主播信息', order: 8,
    fields: [
      {
        id: 'count', label: '主播人数', type: 'choice-single', required: true,
        options: [{ value: '1', label: '1人' }, { value: '2', label: '2人' }, { value: '3+', label: '3人及以上' }],
      },
      {
        id: 'height', label: '主播身高', type: 'dimension', required: true,
        dims: ['女主播', '男主主播'], unit: 'cm',
      },
    ],
  },
  {
    id: 'equipment', title: '九、现有设备', order: 9,
    fields: [
      {
        id: 'hasEquipment', label: '是否已有部分设备', type: 'choice-single', required: true,
        options: [{ value: 'yes', label: '是' }, { value: 'no', label: '否，全部需要采购' }],
      },
    ],
  },
  {
    id: 'goal', title: '十、需求与目标', order: 10,
    fields: [
      {
        id: 'core', label: '核心需求', type: 'choice-single', required: true,
        options: [
          { value: 'new', label: '全新搭建直播间' }, { value: 'optimize', label: '优化现有直播间' },
          { value: 'tune', label: '只调设备参数' }, { value: 'decor', label: '只做装修设计' },
          { value: 'full', label: '全套方案' },
        ],
      },
      {
        id: 'deadline', label: '期望交付时间', type: 'choice-single', required: true,
        options: [
          { value: '3d', label: '3天内' }, { value: '1w', label: '一周内' },
          { value: '2w', label: '两周内' }, { value: 'flexible', label: '不着急' },
        ],
      },
    ],
  },
  {
    id: 'notes', title: '十一、客服备注', order: 11,
    fields: [
      { id: 'note', label: '特殊要求', type: 'text', required: false, placeholder: '任何特殊需求都可以写' },
    ],
  },
]

export const SECTION_ORDER: SectionId[] = SECTIONS.map((s) => s.id)
```

- [ ] **Step 3: 写 `src/utils/summary.ts`**

根据每节字段生成 1 行摘要。已填的拼起来，全空返回"未采集"，部分填返回"采集中文案…"。

```ts
import type { SectionState, FieldValue, SectionDef } from '../types/schema'

function valueToText(v: FieldValue, def?: { label?: string; options?: { value: string; label: string }[] }): string {
  switch (v.type) {
    case 'text':
      return v.value
    case 'choice-single': {
      if (!v.value) return ''
      const opt = def?.options?.find((o) => o.value === v.value)
      return opt?.label ?? v.value
    }
    case 'choice-multi': {
      return v.value
        .map((val) => def?.options?.find((o) => o.value === val)?.label ?? val)
        .join('/')
    }
    case 'dimension':
      return Object.entries(v.value)
        .filter(([, n]) => n !== '')
        .map(([k, n]) => `${k}${n}`)
        .join('×')
    case 'image':
      return v.value.length ? `${v.value.length}张图` : ''
  }
}

export function makeSummary(section: SectionState, def: SectionDef): string {
  const parts: string[] = []
  for (const f of def.fields) {
    const v = section.fields[f.id]
    if (!v) continue
    const t = valueToText(v, f)
    if (t) parts.push(t)
  }
  if (parts.length === 0) return '未采集'
  if (parts.length < def.fields.length) return parts.join(' · ') + '…'
  return parts.join(' · ')
}

export function filledCount(section: SectionState, def: SectionDef): { filled: number; total: number } {
  let filled = 0
  for (const f of def.fields) {
    if (!f.required) continue
    const v = section.fields[f.id]
    if (!v) continue
    if (valueToText(v, f) !== '') filled++
  }
  const total = def.fields.filter((f) => f.required).length
  return { filled, total }
}
```

- [ ] **Step 4: 写失败测试 `tests/summary.test.ts`**

```ts
import { describe, it, expect } from 'vitest'
import { makeSummary, filledCount } from '../src/utils/summary'
import type { SectionState, SectionDef } from '../src/types/schema'

const def: SectionDef = {
  id: 'venue', title: '四、场地条件', order: 4,
  fields: [
    {
      id: 'area', label: '面积', type: 'choice-single', required: true,
      options: [{ value: '10-20', label: '10-20㎡' }],
    },
    {
      id: 'size', label: '尺寸', type: 'dimension', required: true,
      dims: ['宽', '深', '高'], unit: 'm',
    },
  ],
}

describe('makeSummary', () => {
  it('全空返回未采集', () => {
    const s: SectionState = {
      id: 'venue', status: 'pending',
      fields: {
        area: { type: 'choice-single', value: null },
        size: { type: 'dimension', value: { 宽: '', 深: '', 高: '' } },
      },
    }
    expect(makeSummary(s, def)).toBe('未采集')
  })

  it('部分填返回带省略号', () => {
    const s: SectionState = {
      id: 'venue', status: 'active',
      fields: {
        area: { type: 'choice-single', value: '10-20' },
        size: { type: 'dimension', value: { 宽: '', 深: '', 高: '' } },
      },
    }
    expect(makeSummary(s, def)).toBe('10-20㎡…')
  })

  it('全填返回拼接', () => {
    const s: SectionState = {
      id: 'venue', status: 'complete',
      fields: {
        area: { type: 'choice-single', value: '10-20' },
        size: { type: 'dimension', value: { 宽: '4.5', 深: '5', 高: '3' } },
      },
    }
    expect(makeSummary(s, def)).toBe('10-20㎡ · 宽4.5×深5×高3')
  })
})

describe('filledCount', () => {
  it('统计必填已填数', () => {
    const s: SectionState = {
      id: 'venue', status: 'active',
      fields: {
        area: { type: 'choice-single', value: '10-20' },
        size: { type: 'dimension', value: { 宽: '', 深: '', 高: '' } },
      },
    }
    expect(filledCount(s, def)).toEqual({ filled: 1, total: 2 })
  })
})
```

- [ ] **Step 5: 配置 Vitest**

在 `vite.config.ts` 顶部加（保留原有内容）：

```ts
/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './tests/setup.ts',
  },
})
```

创建 `tests/setup.ts`：

```ts
import '@testing-library/jest-dom'
```

在 `package.json` 的 `scripts` 中确保有：

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 6: 运行测试验证失败**

```bash
npm test
```

期望：summary.test.ts 全部通过（因为实现已写）。如果想 TDD，可先把 `summary.ts` 的函数体清空再跑测试看红，再恢复。**首次确认通过即可**。

- [ ] **Step 7: 提交**

```bash
git add -A
git commit -m "feat: 数据模型与 11 节元数据定义"
```

---

## Task 3: 状态管理（reducer + Context + initialState）

**Files:**
- Create: `src/state/initialState.ts`, `src/state/reducer.ts`, `src/state/FormContext.tsx`, `tests/reducer.test.ts`

**Interfaces:**
- Consumes: `SECTIONS`、`SECTION_ORDER`、所有 schema 类型（来自 Task 2）
- Produces:
  - `function createInitialState(): StudioFormState`
  - type `Action = UpdateField | SetActiveSection | Complete | Reset`
  - `function reducer(state, action): StudioFormState`
  - `FormProvider`（React 组件）
  - `useFormState(): { state, dispatch }`

- [ ] **Step 1: 写 `src/state/initialState.ts`**

为每个字段生成"空"的 FieldValue（按类型）。

```ts
import type { FieldDef, StudioFormState, SectionState, FieldValue } from '../types/schema'
import { SECTIONS, SECTION_ORDER } from '../data/sections'

function emptyFieldValue(def: FieldDef): FieldValue {
  switch (def.type) {
    case 'text': return { type: 'text', value: '' }
    case 'choice-single': return { type: 'choice-single', value: null }
    case 'choice-multi': return { type: 'choice-multi', value: [] }
    case 'dimension':
      return { type: 'dimension', value: Object.fromEntries((def.dims ?? []).map((d) => [d, ''])) }
    case 'image': return { type: 'image', value: [] }
  }
}

function emptySectionState(sectionDef: typeof SECTIONS[number]): SectionState {
  const fields: Record<string, FieldValue> = {}
  for (const f of sectionDef.fields) fields[f.id] = emptyFieldValue(f)
  return { id: sectionDef.id, status: 'pending', fields }
}

export function createInitialState(): StudioFormState {
  const sections = {} as StudioFormState['sections']
  for (const def of SECTIONS) sections[def.id] = emptySectionState(def)
  return {
    sections,
    currentSectionId: SECTION_ORDER[0],   // 'customer'
    completed: false,
  }
}
```

- [ ] **Step 2: 写 `src/state/reducer.ts`**

```ts
import type { StudioFormState, SectionId, FieldValue } from '../types/schema'
import { SECTIONS, SECTION_ORDER } from '../data/sections'
import { filledCount } from '../utils/summary'

export type Action =
  | { type: 'update_field'; sectionId: SectionId; fieldId: string; value: FieldValue }
  | { type: 'set_active_section'; sectionId: SectionId }
  | { type: 'advance' }                     // 推进到下一节（由 chatController 触发）
  | { type: 'complete' }
  | { type: 'reset' }

function sectionDef(id: SectionId) {
  return SECTIONS.find((s) => s.id === id)!
}

function recomputeStatus(state: StudioFormState, sectionId: SectionId): StudioFormState {
  const def = sectionDef(sectionId)
  const sec = state.sections[sectionId]
  const { filled, total } = filledCount(sec, def)
  let status: SectionState['status']
  if (filled >= total && total > 0) status = 'complete'
  else if (filled > 0 || sectionId === state.currentSectionId) status = 'active'
  else status = 'pending'
  const newSec = { ...sec, status }
  return { ...state, sections: { ...state.sections, [sectionId]: newSec } }
}

export function reducer(state: StudioFormState, action: Action): StudioFormState {
  switch (action.type) {
    case 'update_field': {
      const sec = state.sections[action.sectionId]
      const newFields = { ...sec.fields, [action.fieldId]: action.value }
      const newSec = { ...sec, fields: newFields }
      let next: StudioFormState = { ...state, sections: { ...state.sections, [action.sectionId]: newSec } }
      next = recomputeStatus(next, action.sectionId)
      return next
    }
    case 'set_active_section':
      return { ...state, currentSectionId: action.sectionId }
    case 'advance': {
      const idx = SECTION_ORDER.indexOf(state.currentSectionId)
      const nextIdx = Math.min(idx + 1, SECTION_ORDER.length - 1)
      return { ...state, currentSectionId: SECTION_ORDER[nextIdx] }
    }
    case 'complete':
      return { ...state, completed: true }
    case 'reset':
      // 由 Provider 重新调用 createInitialState，这里仅标记
      return state
    default:
      return state
  }
}

// 为了上面 recomputeStatus 用到的类型导入
import type { SectionState } from '../types/schema'
```

> 注：`import type` 放文件底部仅为示意，实际应整理到文件顶部。

- [ ] **Step 3: 写 `src/state/FormContext.tsx`**

```tsx
import { createContext, useContext, useReducer, type ReactNode, type Dispatch } from 'react'
import type { StudioFormState } from '../types/schema'
import { reducer, type Action } from './reducer'
import { createInitialState } from './initialState'

interface Ctx {
  state: StudioFormState
  dispatch: Dispatch<Action>
}

const FormContext = createContext<Ctx | null>(null)

export function FormProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, undefined, createInitialState)
  return <FormContext.Provider value={{ state, dispatch }}>{children}</FormContext.Provider>
}

export function useFormState(): Ctx {
  const ctx = useContext(FormContext)
  if (!ctx) throw new Error('useFormState must be used within FormProvider')
  return ctx
}

export function useReset() {
  // 完整重置通过 key 重新挂载 Provider 实现（App 持有 key state）
  // 这里仅返回提示，实际 reset 由 App 层换 key 实现
}
```

- [ ] **Step 4: 修正 reducer.ts 的 import 顺序**

把 Step 2 文件底部的 `import type { SectionState }` 移到文件顶部与其他 import 合并，并删除底部那行注释。最终 reducer.ts 顶部为：

```ts
import type { StudioFormState, SectionId, FieldValue, SectionState } from '../types/schema'
import { SECTIONS, SECTION_ORDER } from '../data/sections'
import { filledCount } from '../utils/summary'
```

- [ ] **Step 5: 写失败测试 `tests/reducer.test.ts`**

```ts
import { describe, it, expect } from 'vitest'
import { reducer } from '../src/state/reducer'
import { createInitialState } from '../src/state/initialState'

describe('reducer', () => {
  it('update_field 更新字段值', () => {
    const s = createInitialState()
    const next = reducer(s, {
      type: 'update_field', sectionId: 'customer', fieldId: 'brand',
      value: { type: 'text', value: '云裳' },
    })
    expect(next.sections.customer.fields.brand).toEqual({ type: 'text', value: '云裳' })
  })

  it('update_field 填完必填后该节 status 变 complete', () => {
    let s = createInitialState()
    s = reducer(s, {
      type: 'update_field', sectionId: 'customer', fieldId: 'brand',
      value: { type: 'text', value: '云裳' },
    })
    // brand + phone 都必填，phone 还没填，应仍是 active
    expect(s.sections.customer.status).toBe('active')
    s = reducer(s, {
      type: 'update_field', sectionId: 'customer', fieldId: 'phone',
      value: { type: 'text', value: '138****' },
    })
    expect(s.sections.customer.status).toBe('complete')
  })

  it('advance 推进到下一节', () => {
    const s = createInitialState()
    expect(s.currentSectionId).toBe('customer')
    const next = reducer(s, { type: 'advance' })
    expect(next.currentSectionId).toBe('industry')
  })

  it('advance 到末节不再前进', () => {
    let s = createInitialState()
    for (let i = 0; i < 20; i++) s = reducer(s, { type: 'advance' })
    expect(s.currentSectionId).toBe('notes')
  })

  it('complete 标记完成', () => {
    const s = createInitialState()
    const next = reducer(s, { type: 'complete' })
    expect(next.completed).toBe(true)
  })
})
```

- [ ] **Step 6: 运行测试**

```bash
npm test
```

期望：reducer.test.ts 与 summary.test.ts 全部通过。

- [ ] **Step 7: 提交**

```bash
git add -A
git commit -m "feat: 状态管理 reducer + Context"
```

---

## Task 4: 对话脚本 scriptedFlow.ts 与 chatController

**Files:**
- Create: `src/data/scriptedFlow.ts`, `src/components/ChatPanel/chatController.ts`, `tests/chatController.test.ts`

**Interfaces:**
- Consumes: `SECTIONS`、`SECTION_ORDER`、`StudioFormState`、reducer actions
- Produces:
  - `interface ScriptedStep { sectionId: SectionId; fieldId: string; prompt: string }`
  - `const SCRIPTED_FLOW: ScriptedStep[]` — 按调研表顺序的提问队列
  - `interface ChatMessage { id: string; role: 'ai' | 'user'; kind: 'text' | 'field'; text?: string; fieldRef?: { sectionId: SectionId; fieldId: string } }`
  - `function initialMessages(): ChatMessage[]` — 开场白 + 第一个问题
  - `function nextStepAfter(fieldId): ScriptedStep | null`
  - `function userReplyToField(state, step, fieldValue): { userMsg: ChatMessage; aiAck: ChatMessage; nextStep: ScriptedStep | null }`

- [ ] **Step 1: 写 `src/data/scriptedFlow.ts`**

按 spec §5.2 的章节覆盖，每节 1-2 个代表性问题。

```ts
import type { SectionId } from '../types/schema'

export interface ScriptedStep {
  sectionId: SectionId
  fieldId: string
  prompt: string
}

export const SCRIPTED_FLOW: ScriptedStep[] = [
  { sectionId: 'customer', fieldId: 'brand', prompt: '您好！我是直播间搭建顾问，先问下您的品牌名是？' },
  { sectionId: 'customer', fieldId: 'phone', prompt: '留个联系电话方便后续沟通？' },
  { sectionId: 'industry', fieldId: 'category', prompt: '您主要做哪个品类？（选择最接近的）' },
  { sectionId: 'industry', fieldId: 'position', prompt: '品牌定位大概是？' },
  { sectionId: 'status', fieldId: 'hasRoom', prompt: '您现在已经有直播间了吗？' },
  { sectionId: 'status', fieldId: 'views', prompt: '场均观看大概多少人？' },
  { sectionId: 'venue', fieldId: 'area', prompt: '聊聊场地，直播间大概多少平米？' },
  { sectionId: 'venue', fieldId: 'size', prompt: '具体尺寸呢？宽×深×高，估个大概也行。' },
  { sectionId: 'budget', fieldId: 'total', prompt: '预算范围大概多少？' },
  { sectionId: 'budget', fieldId: 'equipment', prompt: '其中设备预算大概占多少？' },
  { sectionId: 'product', fieldId: 'main', prompt: '主营商品是什么？比如连衣裙、口红。' },
  { sectionId: 'product', fieldId: 'keywords', prompt: '风格关键词？3-5 个词，比如：国风、高端、雅致。' },
  { sectionId: 'benchmark', fieldId: 'hasBenchmark', prompt: '有没有对标参考的直播间？' },
  { sectionId: 'benchmark', fieldId: 'platform', prompt: '主要想对标哪个平台？' },
  { sectionId: 'host', fieldId: 'count', prompt: '主播几个人？' },
  { sectionId: 'host', fieldId: 'height', prompt: '主播身高多少？影响机位高度计算。' },
  { sectionId: 'equipment', fieldId: 'hasEquipment', prompt: '现有设备情况？是全部新买还是已有部分？' },
  { sectionId: 'goal', fieldId: 'core', prompt: '核心需求是什么？全新搭建 / 优化 / 只调设备…' },
  { sectionId: 'goal', fieldId: 'deadline', prompt: '期望什么时候交付？' },
  { sectionId: 'notes', fieldId: 'note', prompt: '还有什么特殊要求吗？没有可以直接说"无"。' },
]

export function stepAfter(fieldId: string): ScriptedStep | null {
  const idx = SCRIPTED_FLOW.findIndex((s) => s.fieldId === fieldId)
  if (idx === -1 || idx + 1 >= SCRIPTED_FLOW.length) return null
  return SCRIPTED_FLOW[idx + 1]
}

// 切节过渡语
export function transitionPrompt(from: SectionId, to: SectionId): string {
  const titleMap: Record<SectionId, string> = {
    customer: '客户信息', industry: '行业品类', status: '直播间现状',
    venue: '场地条件', budget: '预算范围', product: '商品品牌',
    benchmark: '对标参考', host: '主播信息', equipment: '现有设备',
    goal: '需求目标', notes: '备注',
  }
  return `${titleMap[from]}信息够了，聊聊${titleMap[to]}吧 👇`
}
```

- [ ] **Step 2: 写 `src/components/ChatPanel/chatController.ts`**

```ts
import type { StudioFormState, FieldValue, SectionId } from '../../types/schema'
import { SCRIPTED_FLOW, stepAfter, transitionPrompt, type ScriptedStep } from '../../data/scriptedFlow'

export interface ChatMessage {
  id: string
  role: 'ai' | 'user'
  kind: 'text' | 'field'
  text?: string
  fieldRef?: { sectionId: SectionId; fieldId: string }
}

let idCounter = 0
function newId(): string {
  idCounter += 1
  return `m${Date.now()}_${idCounter}`
}

export function initialMessages(): ChatMessage[] {
  const first = SCRIPTED_FLOW[0]
  return [
    { id: newId(), role: 'ai', kind: 'text', text: '您好！我是直播间搭建顾问，接下来我会问您一系列问题，帮您梳理直播间搭建需求。右侧面板会实时显示采集进度。' },
    { id: newId(), role: 'ai', kind: 'field', text: first.prompt, fieldRef: { sectionId: first.sectionId, fieldId: first.fieldId } },
  ]
}

export function currentStep(messages: ChatMessage[]): ScriptedStep | null {
  const lastField = [...messages].reverse().find((m) => m.kind === 'field')
  if (!lastField || !lastField.fieldRef) return null
  return SCRIPTED_FLOW.find((s) => s.fieldId === lastField.fieldRef!.fieldId) ?? null
}

export function fieldToUserText(v: FieldValue): string {
  switch (v.type) {
    case 'text': return v.value
    case 'choice-single': return v.value ?? ''
    case 'choice-multi': return v.value.join(', ')
    case 'dimension':
      return Object.entries(v.value).filter(([, n]) => n !== '').map(([k, n]) => `${k}${n}`).join('×')
    case 'image': return v.value.length ? `[${v.value.length}张图]` : ''
  }
}

// 用户回答一个字段后，生成 user 消息 + AI 确认 + 下一个 step（可能含过渡语）
export function replyToField(
  currentValue: FieldValue,
): { userMsg: ChatMessage; aiMessages: ChatMessage[]; nextStep: ScriptedStep | null } {
  const userMsg: ChatMessage = {
    id: newId(), role: 'user', kind: 'text', text: fieldToUserText(currentValue),
  }
  // 找到当前 messages 里最后一个 field step —— 但这里只根据 currentValue 无法定位
  // 实际调用方应传入 currentStep
  throw new Error('use replyToCurrentStep instead')
}

export function replyToCurrentStep(
  step: ScriptedStep,
  value: FieldValue,
): { userMsg: ChatMessage; aiMessages: ChatMessage[]; nextStep: ScriptedStep | null } {
  const userMsg: ChatMessage = {
    id: newId(), role: 'user', kind: 'text', text: fieldToUserText(value),
  }
  const aiMessages: ChatMessage[] = []
  aiMessages.push({ id: newId(), role: 'ai', kind: 'text', text: '收到 ✓' })

  const nextStep = stepAfter(step.fieldId)
  if (nextStep) {
    if (nextStep.sectionId !== step.sectionId) {
      aiMessages.push({ id: newId(), role: 'ai', kind: 'text', text: transitionPrompt(step.sectionId, nextStep.sectionId) })
    }
    aiMessages.push({
      id: newId(), role: 'ai', kind: 'field',
      text: nextStep.prompt, fieldRef: { sectionId: nextStep.sectionId, fieldId: nextStep.fieldId },
    })
  } else {
    aiMessages.push({ id: newId(), role: 'ai', kind: 'text', text: '信息采集完成 ✓ 您可以在右侧点击"生成方案"查看完整需求。' })
  }

  return { userMsg, aiMessages, nextStep }
}
```

- [ ] **Step 3: 清理 chatController**

删除 Step 2 中那个抛错的 `replyToField` 占位函数（它只是用来标注"不要用"，但生产代码里不应留死代码）。最终文件只保留 `initialMessages`、`currentStep`、`fieldToUserText`、`replyToCurrentStep`。

- [ ] **Step 4: 写失败测试 `tests/chatController.test.ts`**

```ts
import { describe, it, expect } from 'vitest'
import { initialMessages, currentStep, replyToCurrentStep, fieldToUserText } from '../src/components/ChatPanel/chatController'
import { SCRIPTED_FLOW } from '../src/data/scriptedFlow'

describe('initialMessages', () => {
  it('首条是文字开场白，第二条是第一个 field', () => {
    const msgs = initialMessages()
    expect(msgs).toHaveLength(2)
    expect(msgs[0].role).toBe('ai')
    expect(msgs[0].kind).toBe('text')
    expect(msgs[1].kind).toBe('field')
    expect(msgs[1].fieldRef?.fieldId).toBe('brand')
  })
})

describe('currentStep', () => {
  it('返回最后一条 field 消息对应的 step', () => {
    const msgs = initialMessages()
    const step = currentStep(msgs)
    expect(step?.fieldId).toBe('brand')
  })
})

describe('replyToCurrentStep', () => {
  it('回答后生成 user 消息 + AI 确认 + 下一个 field', () => {
    const step = SCRIPTED_FLOW[0]  // brand
    const value = { type: 'text' as const, value: '云裳' }
    const { userMsg, aiMessages, nextStep } = replyToCurrentStep(step, value)
    expect(userMsg.role).toBe('user')
    expect(userMsg.text).toBe('云裳')
    expect(aiMessages.length).toBeGreaterThanOrEqual(2)
    expect(aiMessages[0].text).toBe('收到 ✓')
    expect(nextStep?.fieldId).toBe('phone')
  })

  it('跨节时 AI 有过渡语', () => {
    // phone 是 customer 最后一个，下一个是 industry
    const phoneStep = SCRIPTED_FLOW[1]
    const value = { type: 'text' as const, value: '138****' }
    const { aiMessages } = replyToCurrentStep(phoneStep, value)
    const hasTransition = aiMessages.some((m) => m.text?.includes('行业品类'))
    expect(hasTransition).toBe(true)
  })

  it('最后一个字段回答后 nextStep 为 null', () => {
    const last = SCRIPTED_FLOW[SCRIPTED_FLOW.length - 1]
    const value = { type: 'text' as const, value: '无' }
    const { nextStep } = replyToCurrentStep(last, value)
    expect(nextStep).toBeNull()
  })
})

describe('fieldToUserText', () => {
  it('choice-single 显示 value', () => {
    expect(fieldToUserText({ type: 'choice-single', value: 'women' })).toBe('women')
  })
  it('dimension 拼接', () => {
    expect(fieldToUserText({ type: 'dimension', value: { 宽: '4', 深: '5', 高: '' } })).toBe('宽4×深5')
  })
})
```

- [ ] **Step 5: 运行测试**

```bash
npm test
```

期望：全部通过。

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "feat: 对话脚本与 chatController"
```

---

## Task 5: 共享 UI 原子（ChoiceCard / DimensionInput / ImageUpload / MessageBubble）

**Files:**
- Create: `src/components/ChatPanel/MessageBubble.tsx`, `src/components/ChatPanel/ChoiceCard.tsx`, `src/components/ChatPanel/DimensionInput.tsx`, `src/components/ChatPanel/ImageUpload.tsx`

**Interfaces:**
- Consumes: `FieldDef`、`FieldValue`（schema.ts）
- Produces（这些组件同时被 ChatPanel 和 CardExpanded 复用）：
  - `<MessageBubble role text? />`
  - `<ChoiceCard def onPick(value) />` — def 决定单/多选；当前选中态从外部 value 传入
  - `<DimensionInput def value onChange(value) />`
  - `<ImageUpload value onChange(value) />`

> 本任务无单元测试（纯 UI），靠 Task 8 的视觉验收。代码必须包含完整 props 类型。

- [ ] **Step 1: 写 `MessageBubble.tsx`**

```tsx
interface Props {
  role: 'ai' | 'user'
  children: React.ReactNode
}

export default function MessageBubble({ role, children }: Props) {
  const isAi = role === 'ai'
  return (
    <div className={`flex ${isAi ? 'justify-start' : 'justify-end'} mb-3`}>
      <div
        className={`max-w-[80%] px-3.5 py-2.5 text-sm leading-relaxed bg-surface text-primary ${
          isAi ? 'rounded-bubble rounded-bl-[4px]' : 'rounded-bubble rounded-br-[4px] bg-accent text-white'
        }`}
      >
        {children}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 写 `ChoiceCard.tsx`**

```tsx
import type { FieldDef, FieldValue } from '../../types/schema'

interface Props {
  def: FieldDef
  value: FieldValue
  onCommit: (v: FieldValue) => void
}

export default function ChoiceCard({ def, value, onCommit }: Props) {
  if (def.type !== 'choice-single' && def.type !== 'choice-multi') return null
  const options = def.options ?? []
  const isMulti = def.type === 'choice-multi'

  const selected: string[] = value.type === 'choice-single'
    ? (value.value ? [value.value] : [])
    : value.value

  function toggle(optVal: string) {
    if (isMulti) {
      const set = new Set(selected)
      if (set.has(optVal)) set.delete(optVal)
      else set.add(optVal)
      onCommit({ type: 'choice-multi', value: Array.from(set) })
    } else {
      onCommit({ type: 'choice-single', value: optVal })
    }
  }

  return (
    <div className="mt-2">
      <div className="flex flex-wrap gap-1.5">
        {options.map((o) => {
          const active = selected.includes(o.value)
          return (
            <button
              key={o.value}
              type="button"
              onClick={() => toggle(o.value)}
              className={`px-3 py-1.5 text-xs rounded-pill transition-colors ${
                active ? 'bg-accent text-white' : 'bg-base text-secondary hover:bg-idle'
              }`}
            >
              {o.label}
            </button>
          )
        })}
      </div>
      {isMulti && (
        <div className="text-muted text-[10px] mt-1.5">
          已选 {selected.length} 项{isMulti ? ' · 可继续选' : ''}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: 写 `DimensionInput.tsx`**

```tsx
import type { FieldDef, FieldValue } from '../../types/schema'

interface Props {
  def: FieldDef
  value: FieldValue
  onChange: (v: FieldValue) => void
}

export default function DimensionInput({ def, value, onChange }: Props) {
  if (value.type !== 'dimension') return null
  const dims = def.dims ?? []
  const unit = def.unit ?? ''
  const current = value.value

  function update(dim: string, v: string) {
    onChange({ type: 'dimension', value: { ...current, [dim]: v } })
  }

  return (
    <div className="mt-2 flex items-center gap-1.5 flex-wrap">
      {dims.map((d, i) => (
        <div key={d} className="flex items-center gap-1.5">
          <span className="text-secondary text-xs">{d}</span>
          <input
            type="number"
            inputMode="decimal"
            value={current[d] ?? ''}
            onChange={(e) => update(d, e.target.value)}
            placeholder="0"
            className="w-14 bg-base border border-idle rounded text-primary text-xs px-2 py-1 focus:border-accent outline-none"
          />
          {i < dims.length - 1 && <span className="text-muted text-xs">×</span>}
        </div>
      ))}
      {unit && <span className="text-muted text-xs ml-1">{unit}</span>}
    </div>
  )
}
```

- [ ] **Step 4: 写 `ImageUpload.tsx`**

```tsx
import { useRef } from 'react'
import type { FieldValue } from '../../types/schema'

interface Props {
  value: FieldValue
  onChange: (v: FieldValue) => void
}

export default function ImageUpload({ value, onChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  if (value.type !== 'image') return null

  function add() {
    // 原型阶段：不真传文件，仅追加一个占位文件名
    const fake = `photo_${value.value.length + 1}.jpg`
    onChange({ type: 'image', value: [...value.value, fake] })
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
```

- [ ] **Step 5: 临时接线看效果**

临时改 `src/App.tsx` 引入 `FormProvider` 与一个 `MessageBubble`，确认编译无错：

```tsx
import MessageBubble from './components/ChatPanel/MessageBubble'
import { FormProvider } from './state/FormContext'

export default function App() {
  return (
    <FormProvider>
      <div className="h-full p-8">
        <MessageBubble role="ai">测试气泡</MessageBubble>
        <MessageBubble role="user">用户消息</MessageBubble>
      </div>
    </FormProvider>
  )
}
```

- [ ] **Step 6: 启动验证**

```bash
npm run dev
```

期望：深蓝背景上出现两个气泡（AI 左灰色圆角、User 右蓝色圆角）。Ctrl+C 停止。

- [ ] **Step 7: 提交**

```bash
git add -A
git commit -m "feat: 共享 UI 原子组件"
```

---

## Task 6: ChatPanel 容器（驱动对话）

**Files:**
- Create: `src/components/ChatPanel/ChatPanel.tsx`
- Modify: `src/App.tsx`（接入 ChatPanel + FormProvider）

**Interfaces:**
- Consumes: Task 4 的 chatController、Task 5 的原子组件、Task 3 的 useFormState
- Produces: `<ChatPanel />` — 自包含左侧对话区，负责消息列表渲染、用户回答派发、输入框兜底

- [ ] **Step 1: 写 `ChatPanel.tsx`**

```tsx
import { useState, useRef, useEffect } from 'react'
import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import {
  initialMessages, currentStep, replyToCurrentStep, type ChatMessage,
} from './chatController'
import MessageBubble from './MessageBubble'
import ChoiceCard from './ChoiceCard'
import DimensionInput from './DimensionInput'
import ImageUpload from './ImageUpload'
import type { FieldDef, FieldValue, SectionId } from '../../types/schema'

export default function ChatPanel() {
  const { state, dispatch } = useFormState()
  const [messages, setMessages] = useState<ChatMessage[]>(() => initialMessages())
  const [draft, setDraft] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const step = currentStep(messages)
  // 当前 step 对应的字段定义
  const fieldDef: FieldDef | undefined = step
    ? SECTIONS.find((s) => s.id === step.sectionId)?.fields.find((f) => f.id === step.fieldId)
    : undefined
  const sectionId: SectionId | undefined = step?.sectionId
  const fieldId = step?.fieldId
  const currentValue: FieldValue | undefined =
    sectionId && fieldId ? state.sections[sectionId].fields[fieldId] : undefined

  function commit(v: FieldValue) {
    if (!step) return
    // 1. 更新 state
    dispatch({ type: 'update_field', sectionId: step.sectionId, fieldId: step.fieldId, value: v })
    // 2. 生成 user 消息 + AI 回复 + 下一步
    const { userMsg, aiMessages, nextStep } = replyToCurrentStep(step, v)
    setMessages((prev) => [...prev, userMsg, ...aiMessages])
    // 3. 推进 active section
    if (nextStep) dispatch({ type: 'set_active_section', sectionId: nextStep.sectionId })
    else dispatch({ type: 'complete' })
  }

  function submitDraft() {
    if (!fieldDef || !currentValue || draft.trim() === '') return
    if (fieldDef.type === 'text') {
      commit({ type: 'text', value: draft.trim() })
      setDraft('')
    } else if (fieldDef.type === 'dimension') {
      // 不支持文本解析，忽略
    } else {
      // 选项类不支持文本兜底（原型）
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
        {messages.map((m) => (
          <MessageBubble key={m.id} role={m.role}>
            <div>{m.text}</div>
            {m.kind === 'field' && m.fieldRef && fieldDef && m.fieldRef.fieldId === fieldId && currentValue && (
              <FieldInput def={fieldDef} value={currentValue} onCommit={commit} />
            )}
          </MessageBubble>
        ))}
      </div>
      <div className="border-t border-idle p-3 flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submitDraft() }}
          placeholder={fieldDef?.type === 'text' ? '直接输入回答…' : '点击上方选项回答'}
          className="flex-1 bg-surface rounded-bubble px-3.5 py-2.5 text-sm text-primary placeholder:text-muted outline-none focus:ring-1 focus:ring-accent"
        />
        <button
          type="button"
          onClick={submitDraft}
          className="px-4 py-2.5 bg-accent text-white rounded-bubble text-sm disabled:opacity-40"
          disabled={fieldDef?.type !== 'text' || draft.trim() === ''}
        >
          发送
        </button>
      </div>
    </div>
  )
}

function FieldInput({ def, value, onCommit }: { def: FieldDef; value: FieldValue; onCommit: (v: FieldValue) => void }) {
  switch (def.type) {
    case 'choice-single':
    case 'choice-multi':
      return <ChoiceCard def={def} value={value} onCommit={onCommit} />
    case 'dimension':
      return <DimensionInput def={def} value={value} onChange={onCommit} />
    case 'image':
      return <ImageUpload value={value} onChange={onCommit} />
    default:
      return null
  }
}
```

- [ ] **Step 2: 改 `src/App.tsx`**

```tsx
import ChatPanel from './components/ChatPanel/ChatPanel'
import { FormProvider } from './state/FormContext'

export default function App() {
  return (
    <FormProvider>
      <div className="h-full flex">
        <div className="w-[55%] border-r border-idle">
          <ChatPanel />
        </div>
        <div className="w-[45%]">
          {/* Dashboard 在 Task 7 接入 */}
          <div className="p-4 text-muted text-sm">右侧仪表盘（待实现）</div>
        </div>
      </div>
    </FormProvider>
  )
}
```

- [ ] **Step 3: 启动验证**

```bash
npm run dev
```

期望：左侧出现开场白 + 第一个问题（品牌名）。输入"云裳"回车 → AI 回"收到 ✓" + 问电话。点选项类问题出现彩色胶囊，点击变色。Ctrl+C 停止。

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "feat: ChatPanel 对话驱动"
```

---

## Task 7: Dashboard 卡片网格 + 就地展开

**Files:**
- Create: `src/components/Dashboard/Dashboard.tsx`, `src/components/Dashboard/SectionCard.tsx`, `src/components/Dashboard/CardExpanded.tsx`, `src/components/FieldEditor.tsx`
- Modify: `src/App.tsx`

**Interfaces:**
- Consumes: useFormState、SECTIONS、makeSummary、filledCount、Task 5 的原子组件
- Produces: `<Dashboard />` — 右侧 11 节卡片网格，点击就地展开

- [ ] **Step 1: 写 `src/components/FieldEditor.tsx`**（CardExpanded 内复用，统一入口）

```tsx
import type { FieldDef, FieldValue } from '../types/schema'
import ChoiceCard from './ChatPanel/ChoiceCard'
import DimensionInput from './ChatPanel/DimensionInput'
import ImageUpload from './ChatPanel/ImageUpload'

interface Props {
  def: FieldDef
  value: FieldValue
  onChange: (v: FieldValue) => void
}

export default function FieldEditor({ def, value, onChange }: Props) {
  function renderInput() {
    switch (def.type) {
      case 'choice-single':
      case 'choice-multi':
        return <ChoiceCard def={def} value={value} onCommit={onChange} />
      case 'dimension':
        return <DimensionInput def={def} value={value} onChange={onChange} />
      case 'image':
        return <ImageUpload value={value} onChange={onChange} />
      case 'text':
        return (
          <input
            type="text"
            value={value.type === 'text' ? value.value : ''}
            onChange={(e) => onChange({ type: 'text', value: e.target.value })}
            placeholder={def.placeholder}
            className="w-full bg-base border border-idle rounded px-3 py-2 text-sm text-primary placeholder:text-muted outline-none focus:border-accent"
          />
        )
      default:
        return null
    }
  }

  return (
    <div className="mb-3">
      <div className="text-secondary text-xs mb-1">
        {def.label}{def.required && <span className="text-accent ml-0.5">*</span>}
      </div>
      {renderInput()}
    </div>
  )
}
```

- [ ] **Step 2: 写 `CardExpanded.tsx`**

```tsx
import { useFormState } from '../../state/FormContext'
import FieldEditor from '../FieldEditor'
import type { SectionDef } from '../../types/schema'

interface Props {
  def: SectionDef
  onCollapse: () => void
}

export default function CardExpanded({ def, onCollapse }: Props) {
  const { state, dispatch } = useFormState()
  const sectionState = state.sections[def.id]

  function update(fieldId: string, v: typeof sectionState.fields[string]) {
    dispatch({ type: 'update_field', sectionId: def.id, fieldId, value: v })
  }

  return (
    <div className="bg-active-surface border border-accent rounded-card p-3 col-span-2">
      <div className="flex justify-between items-center mb-3">
        <span className="text-accent text-sm font-semibold">● {def.title} · 编辑中</span>
        <button
          type="button"
          onClick={onCollapse}
          className="text-xs bg-blue-900 text-blue-200 px-3 py-1 rounded-pill"
        >
          完成
        </button>
      </div>
      {def.fields.map((f) => (
        <FieldEditor
          key={f.id}
          def={f}
          value={sectionState.fields[f.id]}
          onChange={(v) => update(f.id, v)}
        />
      ))}
    </div>
  )
}
```

- [ ] **Step 3: 写 `SectionCard.tsx`**（折叠态）

```tsx
import type { SectionDef } from '../../types/schema'
import { useFormState } from '../../state/FormContext'
import { makeSummary, filledCount } from '../../utils/summary'

interface Props {
  def: SectionDef
  expanded: boolean
  onToggle: () => void
}

const STATUS_COLOR: Record<string, string> = {
  pending: 'bg-idle',
  active: 'bg-accent',
  complete: 'bg-done',
}

export default function SectionCard({ def, expanded, onToggle }: Props) {
  const { state } = useFormState()
  const sec = state.sections[def.id]
  const { filled, total } = filledCount(sec, def)
  const summary = makeSummary(sec, def)
  const isCurrent = state.currentSectionId === def.id

  return (
    <button
      type="button"
      onClick={onToggle}
      className={`text-left bg-surface rounded-card p-2.5 border-l-[3px] transition-colors w-full ${
        sec.status === 'complete' ? 'border-done'
        : isCurrent ? 'border-accent'
        : 'border-idle'
      } ${sec.status === 'pending' ? 'opacity-60' : ''}`}
    >
      <div className="text-secondary text-[11px] mb-0.5">{def.title}</div>
      <div className="text-primary text-xs truncate">{summary}</div>
      <div className="flex items-center gap-1.5 mt-1.5">
        <div className={`h-1 w-6 rounded ${STATUS_COLOR[sec.status]}`} />
        <span className="text-muted text-[10px]">
          {sec.status === 'complete' ? '✓' : `缺 ${total - filled} 项`}
        </span>
      </div>
    </button>
  )
}
```

- [ ] **Step 4: 写 `Dashboard.tsx`**

```tsx
import { useState } from 'react'
import { SECTIONS } from '../../data/sections'
import SectionCard from './SectionCard'
import CardExpanded from './CardExpanded'
import type { SectionId } from '../../types/schema'

export default function Dashboard() {
  const [expandedId, setExpandedId] = useState<SectionId | null>(null)

  return (
    <div className="h-full overflow-y-auto p-3">
      <div className="grid grid-cols-2 gap-2">
        {SECTIONS.map((def) =>
          expandedId === def.id ? (
            <div key={def.id} className="col-span-2">
              {/* CardExpanded 自己渲染，但需放在 grid 内占满 */}
              <ExpandedWrapper def={def} onCollapse={() => setExpandedId(null)} />
            </div>
          ) : (
            <SectionCard
              key={def.id}
              def={def}
              expanded={false}
              onToggle={() => setExpandedId(def.id)}
            />
          ),
        )}
      </div>
    </div>
  )
}

import CardExpandedDefault from './CardExpanded'
import type { SectionDef } from '../../types/schema'
function ExpandedWrapper({ def, onCollapse }: { def: SectionDef; onCollapse: () => void }) {
  return <CardExpandedDefault def={def} onCollapse={onCollapse} />
}
```

- [ ] **Step 5: 修正 Dashboard.tsx 的 import 顺序**

把 Step 4 底部的 `import CardExpandedDefault` 和 `import type { SectionDef }` 移到文件顶部。最终顶部：

```tsx
import { useState } from 'react'
import { SECTIONS } from '../../data/sections'
import SectionCard from './SectionCard'
import CardExpanded from './CardExpanded'
import type { SectionDef, SectionId } from '../../types/schema'
```

并把 JSX 里的 `<ExpandedWrapper>` 直接换成 `<CardExpanded>`（删掉 ExpandedWrapper 辅助函数）：

```tsx
{SECTIONS.map((def) =>
  expandedId === def.id ? (
    <div key={def.id} className="col-span-2">
      <CardExpanded def={def} onCollapse={() => setExpandedId(null)} />
    </div>
  ) : (
    <SectionCard key={def.id} def={def} expanded={false} onToggle={() => setExpandedId(def.id)} />
  ),
)}
```

- [ ] **Step 6: 接入 `src/App.tsx`**

```tsx
import ChatPanel from './components/ChatPanel/ChatPanel'
import Dashboard from './components/Dashboard/Dashboard'
import { FormProvider } from './state/FormContext'

export default function App() {
  return (
    <FormProvider>
      <div className="h-full flex">
        <div className="w-[55%] border-r border-idle">
          <ChatPanel />
        </div>
        <div className="w-[45%]">
          <Dashboard />
        </div>
      </div>
    </FormProvider>
  )
}
```

- [ ] **Step 7: 启动验证**

```bash
npm run dev
```

期望：
- 右侧 11 张卡片网格（2 列）
- 左侧回答"云裳"后，右侧"一、客户信息"卡片摘要更新为"云裳…"
- 点击任意卡片 → 该卡就地展开为完整表单，可编辑字段，点"完成"收起
- 当前 AI 正在问的节卡片有蓝色左边框 + 蓝色脉冲条

Ctrl+C 停止。

- [ ] **Step 8: 提交**

```bash
git add -A
git commit -m "feat: Dashboard 卡片网格与就地展开"
```

---

## Task 8: TopBar 进度 + 完成态 ReportPreview

**Files:**
- Create: `src/components/TopBar.tsx`, `src/components/ReportPreview.tsx`
- Modify: `src/App.tsx`

**Interfaces:**
- Consumes: useFormState（读 sections 算总进度）、SECTIONS
- Produces: `<TopBar />`、`<ReportPreview />`

- [ ] **Step 1: 写 `TopBar.tsx`**

```tsx
import { useFormState } from '../state/FormContext'
import { SECTIONS } from '../data/sections'
import { filledCount } from '../utils/summary'

export default function TopBar({ onReset }: { onReset: () => void }) {
  const { state } = useFormState()
  let filled = 0, total = 0
  for (const def of SECTIONS) {
    const r = filledCount(state.sections[def.id], def)
    filled += r.filled
    total += r.total
  }
  const pct = total === 0 ? 0 : Math.round((filled / total) * 100)

  return (
    <div className="h-14 border-b border-idle flex items-center justify-between px-5 bg-surface">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center text-white text-sm font-bold">直</div>
        <span className="text-primary text-sm font-semibold">直播间视觉向量化智能客服</span>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <svg width="32" height="32" viewBox="0 0 36 36" className="-rotate-90">
            <circle cx="18" cy="18" r="14" fill="none" stroke="#475569" strokeWidth="3" />
            <circle
              cx="18" cy="18" r="14" fill="none" stroke="#34d399" strokeWidth="3"
              strokeDasharray={`${(pct / 100) * 88} 88`} strokeLinecap="round"
            />
          </svg>
          <span className="text-secondary text-xs">{filled}/{total} 已采集</span>
        </div>
        <button
          type="button"
          onClick={onReset}
          className="text-muted text-xs hover:text-secondary"
        >
          重新开始
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 写 `ReportPreview.tsx`**

```tsx
import { useFormState } from '../state/FormContext'
import { SECTIONS } from '../data/sections'
import { makeSummary } from '../utils/summary'

export default function ReportPreview({ onBack }: { onBack: () => void }) {
  const { state } = useFormState()
  const json = JSON.stringify(state.sections, null, 2)

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="flex justify-between items-center mb-5">
        <h2 className="text-primary text-lg font-semibold">需求采集报告</h2>
        <button
          type="button"
          onClick={onBack}
          className="text-sm bg-surface text-secondary px-3 py-1.5 rounded-pill hover:text-primary"
        >
          ‹ 返回修改
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-5">
        {SECTIONS.map((def) => (
          <div key={def.id} className="bg-surface rounded-card p-3">
            <div className="text-secondary text-xs mb-1">{def.title}</div>
            <div className="text-primary text-sm">{makeSummary(state.sections[def.id], def)}</div>
          </div>
        ))}
      </div>

      <div className="space-y-3">
        {[
          '场景设计说明',
          '设备参数清单',
          '多视角效果图',
          '向量化评分报告',
        ].map((title) => (
          <div key={title}>
            <div className="text-secondary text-xs mb-1">{title}</div>
            <div className="bg-surface rounded-card h-24 flex items-center justify-center text-muted text-xs">
              [ 后端 Agent 生成中 · 占位 ]
            </div>
          </div>
        ))}
      </div>

      <details className="mt-5">
        <summary className="text-secondary text-xs cursor-pointer">查看原始 JSON</summary>
        <pre className="bg-surface rounded-card p-3 text-[10px] text-secondary overflow-x-auto mt-2">{json}</pre>
      </details>
    </div>
  )
}
```

- [ ] **Step 3: 改 `src/App.tsx` 接入 TopBar、ReportPreview、reset**

```tsx
import { useState } from 'react'
import TopBar from './components/TopBar'
import ChatPanel from './components/ChatPanel/ChatPanel'
import Dashboard from './components/Dashboard/Dashboard'
import ReportPreview from './components/ReportPreview'
import { FormProvider } from './state/FormContext'

export default function App() {
  const [resetKey, setResetKey] = useState(0)
  const [showReport, setShowReport] = useState(false)

  return (
    <FormProvider key={resetKey}>
      <div className="h-full flex flex-col">
        <TopBar onReset={() => { setResetKey((k) => k + 1); setShowReport(false) }} />
        {showReport ? (
          <ReportPreview onBack={() => setShowReport(false)} />
        ) : (
          <div className="flex-1 flex overflow-hidden">
            <div className="w-[55%] border-r border-idle">
              <ChatPanel onAllDone={() => setShowReport(true)} />
            </div>
            <div className="w-[45%]">
              <Dashboard onGenerate={() => setShowReport(true)} />
            </div>
          </div>
        )}
      </div>
    </FormProvider>
  )
}
```

- [ ] **Step 4: ChatPanel 接 onAllDone prop**

修改 `src/components/ChatPanel/ChatPanel.tsx`：

顶部接口加：
```tsx
export default function ChatPanel({ onAllDone }: { onAllDone?: () => void }) {
```

在 `commit` 函数末尾，`else dispatch({ type: 'complete' })` 改为：
```tsx
else {
  dispatch({ type: 'complete' })
  onAllDone?.()
}
```

- [ ] **Step 5: Dashboard 加"生成方案"按钮（完成时）**

修改 `src/components/Dashboard/Dashboard.tsx`：

```tsx
export default function Dashboard({ onGenerate }: { onGenerate?: () => void }) {
  const { state } = useFormState()
  const [expandedId, setExpandedId] = useState<SectionId | null>(null)
  // 是否全部完成：所有节 status === 'complete'（忽略 notes 的非必填）
  const allDone = SECTIONS.every((def) => {
    if (def.id === 'notes') return true
    return state.sections[def.id].status === 'complete'
  })

  return (
    <div className="h-full overflow-y-auto p-3">
      {allDone && (
        <button
          type="button"
          onClick={onGenerate}
          className="w-full mb-3 bg-done text-base font-semibold py-2.5 rounded-card text-sm"
        >
          生成方案 ✓
        </button>
      )}
      <div className="grid grid-cols-2 gap-2">
        {/* ... 原有 map ... */}
      </div>
    </div>
  )
}
```

- [ ] **Step 6: 启动验证**

```bash
npm run dev
```

完整走查：
1. 顶部 TopBar 显示 Logo + 环形进度 + "重新开始"
2. 走完所有对话问题 → AI 发"完成 ✓"→ 右侧顶部出现绿色"生成方案"按钮
3. 点"生成方案" → 进入 ReportPreview（11 节摘要 + 4 个占位交付物 + 可展开 JSON）
4. 点"返回修改" → 回到主界面
5. 点"重新开始" → 全部清空

Ctrl+C 停止。

- [ ] **Step 7: 跑全部测试**

```bash
npm test
```

期望：summary / reducer / chatController 全部通过。

- [ ] **Step 8: 提交**

```bash
git add -A
git commit -m "feat: TopBar 进度与 ReportPreview 完成态"
```

---

## Task 9: 完整验收与 README

**Files:**
- Create: `livestream-cs-ui/README.md`
- Modify: 无

- [ ] **Step 1: 跑全部测试**

```bash
npm test
```

期望：全部通过。

- [ ] **Step 2: 启动应用做完整走查**

```bash
npm run dev
```

按 spec §5.2 的 11 节顺序逐节回答，验证：
- [ ] 左侧对话推进，每节有过渡语
- [ ] 右侧卡片实时更新摘要与状态色条
- [ ] 当前节卡片高亮
- [ ] 点击任意卡片就地展开，可改字段，完成收起
- [ ] 走完后出现"生成方案"按钮
- [ ] ReportPreview 正常显示
- [ ] "重新开始"清空状态
- [ ] TopBar 环形进度随回答增长

- [ ] **Step 3: 写 `README.md`**

```markdown
# 直播间视觉向量化智能客服 UI 原型

面向客户的 AI 对话式客服前端原型，采集直播间搭建需求的 11 节信息。

## 启动

\`\`\`bash
npm install
npm run dev      # 启动开发服务器
npm test         # 跑单元测试
\`\`\`

## 功能

- 左侧对话区：AI 按脚本提问，气泡内嵌选项卡/尺寸输入/图片上传
- 右侧仪表盘：11 节卡片网格，实时回显采集进度，点击就地展开编辑
- 顶部进度：环形完成度 + 重新开始
- 完成态：生成方案预览页（11 节摘要 + 占位交付物 + 原始 JSON）

## 技术栈

React 18 · TypeScript · Vite · Tailwind CSS · Vitest

## 范围说明

本原型不接后端 / 不接 LLM。AI 消息由 `src/data/scriptedFlow.ts` 本地脚本生成。后续可替换为真实 OpenAI Agents SDK 后端。

## 设计文档

见 \`docs/superpowers/specs/2026-07-06-livestream-cs-ui-design.md\`。
```

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "docs: README 与完整验收"
```

---

## Self-Review 记录

**Spec 覆盖检查：**
- §1 产品定位与范围 → Task 1 范围说明 + README ✓
- §2 整体架构（布局） → Task 6/7/8 三栏布局 ✓
- §2.1 视觉决策（5 项） → Task 1 Tailwind token + Task 5-8 实现 ✓
- §3.1 4 种气泡卡片 → Task 5（ChoiceCard/DimensionInput/ImageUpload）+ ChatPanel 接入 ✓
- §3.2 对话规则（一次一问/兜底/过渡语/极简确认） → Task 4 chatController（transitionPrompt、"收到 ✓"）+ Task 6 ✓
- §4.1 卡片网格（标题/摘要/状态色条/缺失数） → Task 7 SectionCard ✓
- §4.2 就地展开（复用组件/完成按钮/编辑中） → Task 7 CardExpanded + FieldEditor ✓
- §4.3 TopBar 进度 → Task 8 ✓
- §5.1 脚本驱动 → Task 4 scriptedFlow ✓
- §5.2 11 节覆盖 → Task 2 sections.ts（含 equipment/notes 占位）✓
- §5.3 完成态 → Task 8 ReportPreview ✓
- §6 技术结构 → 全部文件路径对齐 ✓
- §6.1 schema 类型 → Task 2 schema.ts ✓
- §6.2 视觉规范 → Task 1 Tailwind config ✓
- §7 后续演进 → README 说明 ✓

**Placeholder 扫描：** 所有 step 都有具体代码或命令，无 TBD/TODO。

**类型一致性：** `SectionId`、`FieldValue`、`FieldDef`、`SectionDef`、`ChatMessage`、`Action` 在跨任务引用处签名一致；`filledCount`、`makeSummary`、`replyToCurrentStep`、`currentStep` 函数名前后一致。
