# 悬浮侧栏 + dark/light 主题改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将固定三栏布局改造为"ChatPanel 充满 + 左右悬浮可折叠卡片 + 可拖拽宽度"，并新增 dark/light 主题切换。

**Architecture:** 用 CSS 变量 + Tailwind 语义 token 实现主题切换（组件代码零改动）；侧栏用绝对定位 overlay 悬浮在 ChatPanel 之上，新建通用 `Sidebar` 容器封装悬浮/折叠/拖拽逻辑；主题与侧栏宽度状态提升到 `App.tsx`，持久化到 localStorage。

**Tech Stack:** React 19 + Vite 8 + Tailwind 3.4 + Vitest 4 + @testing-library/react

## Global Constraints

- 工作分支：`feat/floating-sidebar-dark-light-theme`（已从 main 切出）
- 配色 token：dark 默认（`:root`），`.light` 类覆盖；9 个 token 全部用 `R G B` 空格格式定义，Tailwind 用 `rgb(var(--color-xxx) / <alpha-value>)` 引用
- 持久化 key：`theme`（值 `dark`/`light`）、`sidebar.progress.width`、`sidebar.delivery.width`
- 现有组件类名（`bg-surface`/`text-primary`/`border-idle`/`bg-accent` 等）必须保持不变
- Conventional Commits：`feat:`/`refactor:`/`docs:`，中文描述
- 测试命令：`cd frontend && npm test`（vitest run）；构建验证：`cd frontend && npm run build`

---

## File Structure

| 文件 | 责任 |
|---|---|
| `frontend/src/index.css` | 定义 `:root`（dark）和 `.light` 两套 CSS 变量 |
| `frontend/tailwind.config.js` | 颜色改为 CSS 变量引用（保留 alpha-value） |
| `frontend/src/state/theme.ts` | `useTheme` hook：读写 localStorage + 切换根 class |
| `frontend/src/components/Sidebar.tsx` | 通用悬浮卡片：定位/折叠动画/标题栏/拖拽 resize |
| `frontend/src/App.tsx` | 承载主题、侧栏开关、侧栏宽度状态；组装布局 |
| `frontend/src/components/TopBar.tsx` | 加主题切换按钮；移除进度环 |
| `frontend/src/components/ChatPanel/ChatPanel.tsx` | 加浮在角落的折叠按钮 |
| `frontend/src/components/ProgressPanel/ProgressPanel.tsx` | 顶部加进度环（从 TopBar 迁来） |
| `frontend/tests/theme.test.tsx` | useTheme 单测 |

---

### Task 1: CSS 变量 + Tailwind 配置（主题基础）

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/tailwind.config.js`

**Interfaces:**
- Produces: 9 个 CSS 变量（`--color-base`/`--color-surface`/`--color-active-surface`/`--color-primary`/`--color-secondary`/`--color-muted`/`--color-accent`/`--color-done`/`--color-idle`）在 `:root`（dark）和 `.light` 下定义；Tailwind 颜色 token 改为变量引用，组件类名不变

- [ ] **Step 1: 改写 `frontend/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #root { height: 100%; }

:root {
  --color-base: 15 23 42;
  --color-surface: 30 41 59;
  --color-active-surface: 23 37 84;
  --color-primary: 226 232 240;
  --color-secondary: 148 163 184;
  --color-muted: 100 116 139;
  --color-accent: 59 130 246;
  --color-done: 52 211 153;
  --color-idle: 71 85 105;
  color-scheme: dark;
}

.light {
  --color-base: 255 255 255;
  --color-surface: 241 245 249;
  --color-active-surface: 219 234 254;
  --color-primary: 15 23 42;
  --color-secondary: 71 85 105;
  --color-muted: 148 163 184;
  --color-accent: 59 130 246;
  --color-done: 16 185 129;
  --color-idle: 203 213 225;
  color-scheme: light;
}

body {
  margin: 0;
  background-color: rgb(var(--color-base));
  color: rgb(var(--color-primary));
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
```

- [ ] **Step 2: 改写 `frontend/tailwind.config.js`**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        base: 'rgb(var(--color-base) / <alpha-value>)',
        surface: 'rgb(var(--color-surface) / <alpha-value>)',
        'active-surface': 'rgb(var(--color-active-surface) / <alpha-value>)',
        primary: 'rgb(var(--color-primary) / <alpha-value>)',
        secondary: 'rgb(var(--color-secondary) / <alpha-value>)',
        muted: 'rgb(var(--color-muted) / <alpha-value>)',
        accent: 'rgb(var(--color-accent) / <alpha-value>)',
        done: 'rgb(var(--color-done) / <alpha-value>)',
        idle: 'rgb(var(--color-idle) / <alpha-value>)',
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

- [ ] **Step 3: 构建验证**

Run: `cd frontend && npm run build`
Expected: 构建成功，无类型错误，无 Tailwind 解析错误

- [ ] **Step 4: 提交**

```bash
git add frontend/src/index.css frontend/tailwind.config.js
git commit -m "refactor: 配色改为 CSS 变量，支持 dark/light 主题切换"
```

---

### Task 2: useTheme hook

**Files:**
- Create: `frontend/src/state/theme.ts`
- Test: `frontend/tests/theme.test.tsx`

**Interfaces:**
- Produces: `useTheme(): { theme: 'dark' | 'light'; toggleTheme: () => void }`
- 行为：初始化读 `localStorage.getItem('theme')`，无值默认 `'dark'`；`useEffect` 里根据 theme 给 `document.documentElement` 加/去 `.light` 类（dark 不加类，light 加 `.light`）；`toggleTheme` 翻转 theme 并写 localStorage

- [ ] **Step 1: 写失败测试 `frontend/tests/theme.test.tsx`**

```tsx
import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useTheme } from '../src/state/theme'

describe('useTheme', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.classList.remove('light')
  })

  it('无 localStorage 时默认 dark，不加 .light 类', () => {
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('dark')
    expect(document.documentElement.classList.contains('light')).toBe(false)
  })

  it('localStorage 存 light 时初始化为 light，加 .light 类', () => {
    localStorage.setItem('theme', 'light')
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('light')
    expect(document.documentElement.classList.contains('light')).toBe(true)
  })

  it('toggleTheme 翻转主题并持久化', () => {
    const { result } = renderHook(() => useTheme())
    act(() => result.current.toggleTheme())
    expect(result.current.theme).toBe('light')
    expect(localStorage.getItem('theme')).toBe('light')
    expect(document.documentElement.classList.contains('light')).toBe(true)

    act(() => result.current.toggleTheme())
    expect(result.current.theme).toBe('dark')
    expect(localStorage.getItem('theme')).toBe('dark')
    expect(document.documentElement.classList.contains('light')).toBe(false)
  })
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run tests/theme.test.tsx`
Expected: FAIL（`useTheme` 未定义 / 模块不存在）

- [ ] **Step 3: 实现 `frontend/src/state/theme.ts`**

```ts
import { useState, useEffect, useCallback } from 'react'

export type Theme = 'dark' | 'light'

export function useTheme(): { theme: Theme; toggleTheme: () => void } {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('theme')
    return saved === 'light' ? 'light' : 'dark'
  })

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'light') root.classList.add('light')
    else root.classList.remove('light')
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }, [])

  return { theme, toggleTheme }
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && npx vitest run tests/theme.test.tsx`
Expected: PASS（3 个测试全过）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/state/theme.ts frontend/tests/theme.test.tsx
git commit -m "feat: 新增 useTheme hook，管理 dark/light 主题与持久化"
```

---

### Task 3: Sidebar 通用悬浮卡片容器

**Files:**
- Create: `frontend/src/components/Sidebar.tsx`

**Interfaces:**
- Consumes: 无（纯展示 + 自管理拖拽）
- Produces: 默认导出 `Sidebar` 组件，props 见下方签名；App 在 Task 5 接入

```ts
interface SidebarProps {
  side: 'left' | 'right'
  open: boolean
  onClose: () => void
  title: string
  width: number
  onWidthChange: (w: number) => void
  minWidth?: number   // 默认 240
  maxWidth?: number   // 默认 560
  children: React.ReactNode
}
```

行为：
- 绝对定位 `absolute top-0 bottom-0`（左 `left-0` / 右 `right-0`），四周圆角 `rounded-lg`，阴影 `shadow-xl`，背景 `bg-surface`
- `open=false`：`opacity-0 pointer-events-none` + 向外 `translate-x-full`（左栏 `-translate-x-full`，右栏 `translate-x-full`）+ `transition`
- `open=true`：归位 `translate-x-0` + `opacity-100`
- 顶部标题栏：标题（左）+ 折叠按钮（右，chevron 指向外侧）。左栏 chevron 用 `M15 18l-6-6 6-6`（指向左），右栏用 `M9 18l6-6-6-6`（指向右）
- 拖拽手柄：靠 ChatPanel 那一侧边缘（左栏手柄在卡片右边缘 `right: -2px`，右栏手柄在卡片左边缘 `left: -2px`），宽 `w-1`，`cursor-col-resize`，`hover:bg-accent/40`
- 拖拽时给 body 加 `cursor-col-resize` + `user-select: none`，mouseup 移除；新宽度 clamp 到 `[minWidth, maxWidth]` 后回调 `onWidthChange`

- [ ] **Step 1: 实现 `frontend/src/components/Sidebar.tsx`**

```tsx
import { useRef, type ReactNode } from 'react'

interface SidebarProps {
  side: 'left' | 'right'
  open: boolean
  onClose: () => void
  title: string
  width: number
  onWidthChange: (w: number) => void
  minWidth?: number
  maxWidth?: number
  children: ReactNode
}

function clamp(v: number, min: number, max: number) {
  return Math.min(Math.max(v, min), max)
}

export default function Sidebar({
  side, open, onClose, title, width, onWidthChange,
  minWidth = 240, maxWidth = 560, children,
}: SidebarProps) {
  const startRef = useRef<{ x: number; w: number } | null>(null)

  function startResize(e: React.MouseEvent) {
    e.preventDefault()
    startRef.current = { x: e.clientX, w: width }
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }
  function onMove(e: MouseEvent) {
    if (!startRef.current) return
    const delta = e.clientX - startRef.current.x
    const next = side === 'left'
      ? startRef.current.w + delta
      : startRef.current.w - delta
    onWidthChange(clamp(next, minWidth, maxWidth))
  }
  function onUp() {
    startRef.current = null
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  const isLeft = side === 'left'
  const hiddenTransform = isLeft ? '-translate-x-full' : 'translate-x-full'

  return (
    <div
      className={`absolute top-0 bottom-0 ${isLeft ? 'left-0' : 'right-0'} flex flex-col bg-surface rounded-lg shadow-xl transition-transform duration-300 ${
        open ? 'translate-x-0 opacity-100' : `${hiddenTransform} opacity-0 pointer-events-none`
      }`}
      style={{ width }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-idle">
        <h2 className="text-sm font-semibold text-primary">{title}</h2>
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded hover:bg-active-surface text-secondary"
          aria-label={`收起${title}`}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            {isLeft ? <path d="M15 18l-6-6 6-6" /> : <path d="M9 18l6-6-6-6" />}
          </svg>
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {children}
      </div>
      <div
        onMouseDown={startResize}
        className={`absolute top-0 bottom-0 w-1 cursor-col-resize hover:bg-accent/40 transition-colors ${
          isLeft ? 'right-0 translate-x-1/2' : 'left-0 -translate-x-1/2'
        }`}
      />
    </div>
  )
}
```

- [ ] **Step 2: 类型检查 + 构建**

Run: `cd frontend && npm run build`
Expected: 构建成功（Sidebar 尚未使用，但需确认类型无误）

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/Sidebar.tsx
git commit -m "feat: 新增 Sidebar 通用悬浮卡片容器（可折叠 + 拖拽宽度）"
```

---

### Task 4: TopBar 加主题按钮 + 移除进度环

**Files:**
- Modify: `frontend/src/components/TopBar.tsx`

**Interfaces:**
- Consumes: `theme: Theme`、`onToggleTheme: () => void`（来自 Task 2 的 useTheme）
- Produces: TopBar 不再渲染进度环（迁到 ProgressPanel，Task 6）；新增主题切换按钮

**当前代码（`TopBar.tsx:1-42`）：** 从 `useFormState` 取 state，循环 SECTIONS 算 filled/total，渲染 logo + 进度环 + 重新开始。props 只有 `onReset`。

- [ ] **Step 1: 改写 `frontend/src/components/TopBar.tsx`**

去掉 SECTIONS/filledCount/进度环逻辑；props 增加 `theme` 和 `onToggleTheme`。

```tsx
import type { Theme } from '../state/theme'

interface Props {
  theme: Theme
  onToggleTheme: () => void
  onReset: () => void
}

export default function TopBar({ theme, onToggleTheme, onReset }: Props) {
  const isDark = theme === 'dark'
  return (
    <div className="h-14 border-b border-idle flex items-center justify-between px-5 bg-surface">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center text-white text-sm font-bold">直</div>
        <span className="text-primary text-sm font-semibold">直播间视觉向量化智能客服</span>
      </div>
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={onToggleTheme}
          className="p-1.5 rounded hover:bg-active-surface text-secondary"
          aria-label={isDark ? '切换到浅色主题' : '切换到深色主题'}
        >
          {isDark ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="5" />
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
            </svg>
          )}
        </button>
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

注意：原 `bg-base` 改为 `bg-surface`（顶栏作为实体面板更合理，且与新设计一致）；移除 `useFormState`、`SECTIONS`、`filledCount` 导入。

- [ ] **Step 2: 构建（App 尚未传新 props，会有类型错误，下一 Task 修复）**

Run: `cd frontend && npx tsc -b --noEmit 2>&1 | head -20`
Expected: 可能报 App.tsx 中 `<TopBar>` props 不匹配（正常，Task 5 修复）。仅确认 TopBar.tsx 自身类型正确。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/TopBar.tsx
git commit -m "feat: TopBar 加主题切换按钮，移除进度环"
```

---

### Task 5: App 重组布局 + 接入主题与侧栏

**Files:**
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `useTheme`（Task 2）、`Sidebar`（Task 3）、新 `TopBar` props（Task 4）
- Produces: 整体布局——TopBar + ChatPanel 充满 + 两个 Sidebar overlay；侧栏开关、宽度状态与持久化

- [ ] **Step 1: 改写 `frontend/src/App.tsx`**

```tsx
import { useState } from 'react'
import TopBar from './components/TopBar'
import ChatPanel from './components/ChatPanel/ChatPanel'
import ProgressPanel from './components/ProgressPanel/ProgressPanel'
import DeliveryPanel from './components/DeliveryPanel/DeliveryPanel'
import Sidebar from './components/Sidebar'
import { FormProvider } from './state/FormContext'
import { useTheme } from './state/theme'

const PROGRESS_WIDTH_KEY = 'sidebar.progress.width'
const DELIVERY_WIDTH_KEY = 'sidebar.delivery.width'

function loadWidth(key: string, fallback: number) {
  const v = Number(localStorage.getItem(key))
  return Number.isFinite(v) && v > 0 ? v : fallback
}

export default function App() {
  const [resetKey, setResetKey] = useState(0)
  const [progressOpen, setProgressOpen] = useState(false)
  const [deliveryOpen, setDeliveryOpen] = useState(false)
  const [progressWidth, setProgressWidth] = useState(() => loadWidth(PROGRESS_WIDTH_KEY, 320))
  const [deliveryWidth, setDeliveryWidth] = useState(() => loadWidth(DELIVERY_WIDTH_KEY, 360))
  const { theme, toggleTheme } = useTheme()

  function handleProgressWidth(w: number) {
    setProgressWidth(w)
    localStorage.setItem(PROGRESS_WIDTH_KEY, String(w))
  }
  function handleDeliveryWidth(w: number) {
    setDeliveryWidth(w)
    localStorage.setItem(DELIVERY_WIDTH_KEY, String(w))
  }

  function handleReset() {
    setResetKey((k) => k + 1)
    setProgressOpen(false)
    setDeliveryOpen(false)
  }

  return (
    <FormProvider key={resetKey}>
      <div className="h-full flex flex-col bg-base text-primary">
        <TopBar theme={theme} onToggleTheme={toggleTheme} onReset={handleReset} />
        <div className="relative flex-1 overflow-hidden">
          <div className="absolute inset-0">
            <ChatPanel
              progressOpen={progressOpen}
              deliveryOpen={deliveryOpen}
              onToggleProgress={() => setProgressOpen((o) => !o)}
              onToggleDelivery={() => setDeliveryOpen((o) => !o)}
              onComplete={() => setDeliveryOpen(true)}
            />
          </div>
          <Sidebar
            side="left"
            open={progressOpen}
            onClose={() => setProgressOpen(false)}
            title="采集进度"
            width={progressWidth}
            onWidthChange={handleProgressWidth}
          >
            <ProgressPanel />
          </Sidebar>
          <Sidebar
            side="right"
            open={deliveryOpen}
            onClose={() => setDeliveryOpen(false)}
            title="交付物"
            width={deliveryWidth}
            onWidthChange={handleDeliveryWidth}
          >
            <DeliveryPanel />
          </Sidebar>
        </div>
      </div>
    </FormProvider>
  )
}
```

- [ ] **Step 2: 构建验证（ChatPanel 还未接新 props，可能报错，Task 6 修复）**

暂不单独构建，与 Task 6 合并验证。

- [ ] **Step 3: 暂不提交，等 Task 6 完成后一起提交（App 与 ChatPanel 改动需同时通过类型检查）**

---

### Task 6: ChatPanel 加浮在角落的折叠按钮 + ProgressPanel 加进度环

**Files:**
- Modify: `frontend/src/components/ChatPanel/ChatPanel.tsx`
- Modify: `frontend/src/components/ProgressPanel/ProgressPanel.tsx`

**Interfaces:**
- ChatPanel Consumes: `progressOpen`、`deliveryOpen`、`onToggleProgress`、`onToggleDelivery`（来自 App）
- ChatPanel Produces: 新 props 签名；保留 `onComplete?`
- ProgressPanel: 顶部新增进度环（逻辑从 TopBar 迁来，颜色用 CSS 变量）

- [ ] **Step 1: 改写 `frontend/src/components/ChatPanel/ChatPanel.tsx` 顶部**

仅改 props 接口 + 最外层包裹 + 加两个浮动按钮，消息/输入逻辑不动。

原（`ChatPanel.tsx:13`）：
```tsx
export default function ChatPanel({ onComplete }: { onComplete?: () => void }) {
```
改为：
```tsx
interface ChatPanelProps {
  onComplete?: () => void
  progressOpen: boolean
  deliveryOpen: boolean
  onToggleProgress: () => void
  onToggleDelivery: () => void
}

export default function ChatPanel({
  onComplete, progressOpen, deliveryOpen, onToggleProgress, onToggleDelivery,
}: ChatPanelProps) {
```

原（`ChatPanel.tsx:57-58`）最外层：
```tsx
  return (
    <div className="h-full flex flex-col">
```
改为（加 `relative` + 两个浮动按钮）：
```tsx
  return (
    <div className="h-full flex flex-col relative">
      {!progressOpen && (
        <button
          type="button"
          onClick={onToggleProgress}
          className="absolute top-3 left-3 z-10 p-2 rounded-card bg-surface/80 backdrop-blur shadow hover:bg-surface text-secondary"
          aria-label="展开采集进度"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
      )}
      {!deliveryOpen && (
        <button
          type="button"
          onClick={onToggleDelivery}
          className="absolute top-3 right-3 z-10 p-2 rounded-card bg-surface/80 backdrop-blur shadow hover:bg-surface text-secondary"
          aria-label="展开交付物"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 18l6-6-6-6" />
          </svg>
        </button>
      )}
```

- [ ] **Step 2: 改写 `frontend/src/components/ProgressPanel/ProgressPanel.tsx` 加进度环**

原文件顶部只 import `useFormState`/`SECTIONS`/`makeSummary`。新增 `filledCount` 导入，在列表上方加进度环。

改写为：
```tsx
import { useFormState } from '../../state/FormContext'
import { SECTIONS } from '../../data/sections'
import { filledCount, makeSummary } from '../../utils/summary'

const STATUS_DOT: Record<string, string> = {
  pending: 'bg-idle',
  active: 'bg-accent',
  complete: 'bg-done',
}

export default function ProgressPanel() {
  const { state } = useFormState()

  let filled = 0, total = 0
  for (const def of SECTIONS) {
    const r = filledCount(state.sections[def.id], def)
    filled += r.filled
    total += r.total
  }
  const pct = total === 0 ? 0 : Math.round((filled / total) * 100)

  return (
    <div className="h-full overflow-y-auto">
      <div className="px-3 py-3 border-b border-idle flex items-center gap-2">
        <svg width="28" height="28" viewBox="0 0 36 36" className="-rotate-90">
          <circle cx="18" cy="18" r="14" fill="none" stroke="rgb(var(--color-idle))" strokeWidth="3" />
          <circle
            cx="18" cy="18" r="14" fill="none" stroke="rgb(var(--color-done))" strokeWidth="3"
            strokeDasharray={`${(pct / 100) * 88} 88`} strokeLinecap="round"
          />
        </svg>
        <span className="text-secondary text-xs">{filled}/{total} 已采集</span>
      </div>
      <div className="py-2">
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
    </div>
  )
}
```

- [ ] **Step 3: 构建验证**

Run: `cd frontend && npm run build`
Expected: 构建成功，无类型错误

- [ ] **Step 4: 全量测试**

Run: `cd frontend && npm test`
Expected: 所有测试通过（含 theme.test.tsx + 原有 summary/reducer/chatController 测试）

- [ ] **Step 5: 提交（App + ChatPanel + ProgressPanel 一起）**

```bash
git add frontend/src/App.tsx frontend/src/components/ChatPanel/ChatPanel.tsx frontend/src/components/ProgressPanel/ProgressPanel.tsx
git commit -m "feat: 重组三栏为悬浮侧栏布局，ChatPanel 充满，进度环移至进度栏"
```

---

### Task 7: 手动验证 + 收尾

**Files:**
- 无文件改动（验证 + 文档收尾）

- [ ] **Step 1: 启动 dev server**

Run: `cd frontend && npm run dev`
打开浏览器访问 Vite 显示的本地地址。

- [ ] **Step 2: 手动验证清单**

逐项验证（每项不通过则回到对应 Task 修复）：

1. **主题切换**：点 TopBar 日/月按钮，所有区域（顶栏、ChatPanel、侧栏、消息气泡）颜色切换；刷新页面后主题保持
2. **左侧栏展开/收起**：ChatPanel 左上角 chevron 按钮 → 点击 → 进度栏从左滑入，圆角阴影；卡片顶部 chevron → 点击 → 收起，回到角落按钮
3. **右侧栏展开/收起**：ChatPanel 右上角 chevron 按钮 → 点击 → 交付栏从右滑入；卡片顶部按钮收起
4. **拖拽宽度**：拖左侧栏右边缘 → 宽度变化，不超过 240–560；拖右侧栏左边缘同理；刷新后宽度保持
5. **进度环**：在左侧栏顶部显示，颜色随主题切换（dark 绿/done、灰/idle；light 同）
6. **聊天完成触发**：完成所有采集步骤 → 右侧交付栏自动展开
7. **重置**：点"重新开始" → 侧栏关闭、表单清空
8. **两侧栏同时展开**：互不干扰，都悬浮在 ChatPanel 之上

- [ ] **Step 3: 最终构建确认**

Run: `cd frontend && npm run build && npm test`
Expected: 构建成功 + 所有测试通过

- [ ] **Step 4: 完成分支（不 push、不 merge，等用户确认）**

```bash
git log --oneline main..HEAD
```
向用户汇报分支状态，等待 review。

---

## Self-Review

**Spec coverage:**
- §2.1 布局（ChatPanel 充满 + overlay）→ Task 5 ✓
- §2.2 侧栏样式（圆角/阴影/折叠态/宽度）→ Task 3 ✓
- §2.3 折叠按钮位置（角落 + 卡片顶部）→ Task 3 + Task 6 ✓
- §2.4 关闭方式（卡片按钮 toggle）→ Task 3 ✓
- §2.5 交付栏时机（随时 + 完成自动展开）→ Task 5（`onComplete` + 手动按钮）✓
- §2.6 主题切换 → Task 2 + Task 4 ✓
- §3 配色方案 → Task 1 ✓
- §4.2 状态管理（4 个状态 + 持久化）→ Task 5 ✓
- §5.3 拖拽逻辑（Sidebar 不碰 localStorage，App 持久化）→ Task 3 + Task 5 ✓
- §5.6 进度环迁移 → Task 6 ✓
- §6 测试策略（useTheme 单测 + 手动）→ Task 2 + Task 7 ✓

**Placeholder scan:** 无 TBD/TODO，所有代码块完整。✓

**Type consistency:** `Theme` 类型在 Task 2 定义，Task 4 import 一致；`SidebarProps` 在 Task 3 定义，Task 5 使用一致；`ChatPanelProps` 在 Task 6 定义，Task 5 使用一致。✓
