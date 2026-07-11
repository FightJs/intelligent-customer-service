# 固定常驻三栏布局 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将"默认收起、点击悬浮弹出"的侧栏交互，改为 flex 行布局的"默认三栏常驻、可收起为 64px 窄条、可拖拽调宽"。

**Architecture:** 删除 `App.tsx` 中绝对定位浮层 + padding 让位逻辑，改为 `flex` 行布局三栏平铺；`Sidebar.tsx` 从绝对定位浮层改为 flex 子项，宽度由 `open` 状态决定（展开=拖拽值，收起=64px），新增 `onToggle` prop 供窄条展开图标调用；`TopBar.tsx` 仅高度 40→48px。默认状态翻转为三栏全开，默认宽度 220/280。

**Tech Stack:** React 19 + Vite 8 + Tailwind 3.4 + Vitest 4 + @testing-library/react

## Global Constraints

- 工作分支：`feat/fixed-three-column-layout`（已从 main 切出，spec 已提交）
- 配色 token 不变（`bg-surface`/`text-primary`/`border-idle`/`bg-accent`/`ring-white/10` 等沿用）
- 持久化 key 不变：`sidebar.progress.width`、`sidebar.delivery.width`（保留旧值，不强制覆盖）
- 收起态窄条宽度固定 64px；展开态默认 左 220 / 右 280，可拖拽范围 左 180–360 / 右 220–420
- 拖拽仅在 `open=true` 时生效
- Conventional Commits：`refactor:`/`feat:`/`docs:`，中文描述
- 测试命令：`cd frontend && npm test`（vitest run）；构建验证：`cd frontend && npm run build`
- 现有 5 个测试文件（chatController/reducer/summary/theme/setup）不得被破坏

参考 spec：`docs/superpowers/specs/2026-07-08-fixed-three-column-layout-design.md`

---

## File Structure

| 文件 | 责任 |
|---|---|
| `frontend/src/components/Sidebar.tsx` | 改为 flex 子项；宽度由 open 决定；收起态 64px 仅展开图标；新增 `onToggle` prop；拖拽仅 open 时挂载 |
| `frontend/src/App.tsx` | flex 行布局替代浮层；默认 open=true；默认宽 220/280；reset 去掉折叠副作用；传 `onToggle` 给 Sidebar |
| `frontend/src/components/TopBar.tsx` | 高度 `h-10` → `h-12`（40→48px） |
| `frontend/tests/Sidebar.test.tsx` | 新增：Sidebar 在 open/closed 态下的渲染与 onToggle 行为 |

---

### Task 1: Sidebar 改造为 flex 子项 + onToggle prop

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx`
- Test: `frontend/tests/Sidebar.test.tsx`

**Interfaces:**
- Produces: `Sidebar` 组件 props 新增 `onToggle: () => void`
  - `open=true`：渲染 header（标题 + headerExtra）、children、拖拽手柄；`style.width` = `width` prop
  - `open=false`：渲染垂直居中的展开图标按钮，children 不渲染，无拖拽手柄；`style.width` = 64
  - 容器类名：`flex flex-col bg-surface rounded-[12px] shadow-xl ring-1 ring-white/10 transition-[width] duration-300 overflow-hidden shrink-0`
- Consumes: 无新依赖（沿用 `side`/`title`/`width`/`onWidthChange`/`minWidth`/`maxWidth`/`children`/`headerExtra`）

- [ ] **Step 1: 写失败测试 `frontend/tests/Sidebar.test.tsx`**

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Sidebar from '../src/components/Sidebar'

describe('Sidebar', () => {
  it('open=true 时渲染标题、headerExtra、children，宽度等于 width prop', () => {
    const { container } = render(
      <Sidebar side="left" open={true} title="采集进度" width={220}
               onWidthChange={() => {}} onToggle={() => {}} headerExtra={<span>X</span>}>
        <div>子内容</div>
      </Sidebar>
    )
    expect(screen.getByText('采集进度')).toBeInTheDocument()
    expect(screen.getByText('X')).toBeInTheDocument()
    expect(screen.getByText('子内容')).toBeInTheDocument()
    const root = container.firstElementChild as HTMLElement
    expect(root.style.width).toBe('220px')
  })

  it('open=false 时宽度 64px，不渲染 children，渲染展开图标按钮', () => {
    const onToggle = vi.fn()
    const { container } = render(
      <Sidebar side="left" open={false} title="采集进度" width={220}
               onWidthChange={() => {}} onToggle={onToggle}>
        <div>子内容</div>
      </Sidebar>
    )
    expect(screen.queryByText('子内容')).not.toBeInTheDocument()
    const root = container.firstElementChild as HTMLElement
    expect(root.style.width).toBe('64px')
    const btn = screen.getByRole('button', { name: '展开采集进度' })
    fireEvent.click(btn)
    expect(onToggle).toHaveBeenCalledOnce()
  })

  it('open=false 时右栏展开按钮 aria-label 仍含标题', () => {
    render(
      <Sidebar side="right" open={false} title="交付物" width={280}
               onWidthChange={() => {}} onToggle={() => {}} />
    )
    expect(screen.getByRole('button', { name: '展开交付物' })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npm test -- Sidebar`
Expected: FAIL（旧版 Sidebar 是 absolute 浮层，open=false 时用 translate 隐藏但 children 仍渲染，且无 onToggle 展开按钮）

- [ ] **Step 3: 重写 `frontend/src/components/Sidebar.tsx`**

```tsx
import { useRef, type ReactNode } from 'react'

interface SidebarProps {
  side: 'left' | 'right'
  open: boolean
  title: string
  width: number
  onWidthChange: (w: number) => void
  onToggle: () => void
  minWidth?: number
  maxWidth?: number
  children: ReactNode
  headerExtra?: ReactNode
}

function clamp(v: number, min: number, max: number) {
  return Math.min(Math.max(v, min), max)
}

export default function Sidebar({
  side, open, title, width, onWidthChange, onToggle,
  minWidth = 240, maxWidth = 560, children, headerExtra,
}: SidebarProps) {
  const isLeft = side === 'left'
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
    const next = isLeft ? startRef.current.w + delta : startRef.current.w - delta
    onWidthChange(clamp(next, minWidth, maxWidth))
  }
  function onUp() {
    startRef.current = null
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  return (
    <div
      className="relative flex flex-col bg-surface rounded-[12px] shadow-xl ring-1 ring-white/10 transition-[width] duration-300 overflow-hidden shrink-0"
      style={{ width: open ? width : 64 }}
    >
      {open ? (
        <>
          <div className="flex items-center justify-center px-4 py-3 border-b border-idle gap-2">
            <h2 className="text-sm font-semibold text-primary">{title}</h2>
            {headerExtra}
          </div>
          <div className="flex-1 hide-scrollbar">
            {children}
          </div>
          <div
            onMouseDown={startResize}
            className={`absolute top-0 bottom-0 w-1 cursor-col-resize hover:bg-accent/40 transition-colors ${
              isLeft ? 'right-0 translate-x-1/2' : 'left-0 -translate-x-1/2'
            }`}
          />
        </>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <button
            type="button"
            onClick={onToggle}
            className="p-2 rounded hover:bg-active-surface text-secondary"
            aria-label={`展开${title}`}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {isLeft ? (
                <path d="M9 6l6 6-6 6" />
              ) : (
                <path d="M15 6l-6 6 6 6" />
              )}
            </svg>
          </button>
        </div>
      )}
    </div>
  )
}
```

> 注：拖拽手柄用 `absolute` 是相对 Sidebar 根容器（根容器是 flex item，定位仍正常）。手柄仅在 open 块内渲染，收起态不出现。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && npm test -- Sidebar`
Expected: PASS（3 个测试全过）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/Sidebar.tsx frontend/tests/Sidebar.test.tsx
git commit -m "refactor: Sidebar 改为 flex 子项，新增 onToggle prop 与收起态窄条"
```

---

### Task 2: App.tsx 改为 flex 行布局 + 默认三栏全开

**Files:**
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: Task 1 的 `Sidebar` 新签名（`onToggle` 必填）
- Produces: App 默认 `progressOpen=true`、`deliveryOpen=true`；默认宽 220/280；布局为 `flex gap-2 p-2`

- [ ] **Step 1: 改写 `frontend/src/App.tsx` 的状态默认值与布局**

将文件第 39–104 行替换为：

```tsx
  const [resetKey, setResetKey] = useState(0)
  const [progressOpen, setProgressOpen] = useState(true)
  const [deliveryOpen, setDeliveryOpen] = useState(true)
  const [progressWidth, setProgressWidth] = useState(() => loadWidth(PROGRESS_WIDTH_KEY, 220))
  const [deliveryWidth, setDeliveryWidth] = useState(() => loadWidth(DELIVERY_WIDTH_KEY, 280))
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
  }

  return (
    <FormProvider key={resetKey}>
      <div className="h-full flex flex-col bg-base text-primary">
        <TopBar
          theme={theme}
          onToggleTheme={toggleTheme}
          onReset={handleReset}
          progressOpen={progressOpen}
          deliveryOpen={deliveryOpen}
          onToggleProgress={() => setProgressOpen((o) => !o)}
          onToggleDelivery={() => setDeliveryOpen((o) => !o)}
        />
        <div className="flex-1 flex gap-2 p-2 overflow-hidden">
          <Sidebar
            side="left"
            open={progressOpen}
            title="采集进度"
            width={progressWidth}
            onWidthChange={handleProgressWidth}
            onToggle={() => setProgressOpen((o) => !o)}
            minWidth={180}
            maxWidth={360}
            headerExtra={<ProgressHeaderExtra />}
          >
            <ProgressPanel />
          </Sidebar>
          <div className="flex-1 min-w-0">
            <ChatPanel onComplete={() => setDeliveryOpen(true)} />
          </div>
          <Sidebar
            side="right"
            open={deliveryOpen}
            title="交付物"
            width={deliveryWidth}
            onWidthChange={handleDeliveryWidth}
            onToggle={() => setDeliveryOpen((o) => !o)}
            minWidth={220}
            maxWidth={420}
          >
            <DeliveryPanel />
          </Sidebar>
        </div>
      </div>
    </FormProvider>
  )
```

> 变化点：
> - `progressOpen/deliveryOpen` 默认 `true`
> - 默认宽 `220`/`280`
> - `handleReset` 去掉两行 `setProgressOpen(false)/setDeliveryOpen(false)`
> - 删除 `relative` + `absolute inset-0` + `padding-transition` 浮层结构
> - 改为 `flex gap-2 p-2`，三栏平铺，ChatPanel 包一层 `flex-1 min-w-0`
> - 两个 Sidebar 显式传 `minWidth/maxWidth` 和 `onToggle`

- [ ] **Step 2: 运行全部测试**

Run: `cd frontend && npm test`
Expected: PASS（新增 Sidebar 3 个 + 原有全部测试，0 失败）

- [ ] **Step 3: 构建验证**

Run: `cd frontend && npm run build`
Expected: 0 错误（tsc + vite build 通过）

- [ ] **Step 4: 提交**

```bash
git add frontend/src/App.tsx
git commit -m "refactor: App 改为 flex 行布局，默认三栏全开，默认宽 220/280"
```

---

### Task 3: TopBar 高度调整

**Files:**
- Modify: `frontend/src/components/TopBar.tsx:19`

**Interfaces:**
- Consumes: 无
- Produces: TopBar 高度 48px

- [ ] **Step 1: 修改 `frontend/src/components/TopBar.tsx` 第 19 行**

将：
```tsx
    <div className="h-10 flex items-center px-4 gap-3">
```
改为：
```tsx
    <div className="h-12 flex items-center px-4 gap-3">
```

- [ ] **Step 2: 构建验证**

Run: `cd frontend && npm run build`
Expected: 0 错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/TopBar.tsx
git commit -m "style: TopBar 高度 40px → 48px"
```

---

### Task 4: 验收清单手动核验 + 完成分支

**Files:**
- 无新文件

- [ ] **Step 1: 全量测试 + 构建**

Run: `cd frontend && npm test && npm run build`
Expected: 全部测试 PASS，构建 0 错误

- [ ] **Step 2: 对照 spec 验收清单逐条核验**

参考 `docs/superpowers/specs/2026-07-08-fixed-three-column-layout-design.md` 第 9 节：

- [ ] 默认进入：三栏全开，左 220 / 中 flex / 右 280
- [ ] 中间聊天区 `flex:1`，侧栏收起时自然扩展吃掉空间，无遮挡
- [ ] 点 TopBar 开关或侧栏窄条展开图标：侧栏宽度过渡 220↔64（或 280↔64），300ms 动画
- [ ] 收起态 64px 窄条：仅垂直居中展开图标，内容隐藏
- [ ] 展开态可拖拽调宽，范围 左 180–360 / 右 220–420，松手后写 localStorage
- [ ] 收起态不可拖拽
- [ ] 栏间 8px gap，每栏独立圆角 12px + 阴影 + ring
- [ ] TopBar 高度 48px，开关按钮图标方向与开合状态对应
- [ ] 重新开始：仅重置表单，侧栏开合与宽度保持当前状态

> 人工核验项（无现成测试覆盖，需 dev server 目测）：
> 启动 `cd frontend && npm run dev`，浏览器打开后逐条目测上述清单。
> 拖拽调宽、动画手感、收起态窄条视觉这几项必须目测确认。

- [ ] **Step 3: 查看分支 commits**

Run: `git log main..HEAD --oneline`
Expected: 看到 3 个 commit（Sidebar / App / TopBar）

- [ ] **Step 4: 汇报给用户，等待 review**

向用户报告：分支 `feat/fixed-three-column-layout` 已完成，4 个 commit（含 spec），可 review diff 后决定是否合并。
```

按规则，本计划**不自动 push、不自动 merge**（AGENTS.md 约定），完成后由用户确认。

---

## Self-Review

**1. Spec coverage（对照 spec 第 8 节技术改动清单 + 第 9 节验收）：**

| Spec 要求 | 对应 Task |
|---|---|
| Sidebar 绝对定位 → flex 子项 | Task 1 Step 3 |
| width 由 open 决定，收起 64px | Task 1 Step 3（`width: open ? width : 64`） |
| 收起态仅展开图标 | Task 1 Step 3（else 分支） |
| 新增 onToggle prop | Task 1 Step 1/3 |
| 拖拽仅 open 时挂载 | Task 1 Step 3（手柄在 `open ?` 分支内） |
| App flex 布局替代浮层 | Task 2 Step 1 |
| 默认 open=true | Task 2 Step 1 |
| 默认宽 220/280 | Task 2 Step 1 |
| reset 去掉折叠副作用 | Task 2 Step 1（handleReset 简化） |
| 拖拽范围 左 180–360 / 右 220–420 | Task 2 Step 1（minWidth/maxWidth 显式传） |
| TopBar h-10 → h-12 | Task 3 Step 1 |
| 验收清单 | Task 4 Step 2 |

**2. Placeholder scan：** 无 TBD/TODO，每步都有完整代码或确切命令。✅

**3. Type consistency：** 
- `Sidebar` props 在 Task 1 定义 `onToggle: () => void`（必填），Task 2 调用处两处都传了 `onToggle`。✅
- `minWidth/maxWidth` 在 Task 2 显式传 `180/360` 和 `220/420`，覆盖 spec 第 4 节"左 180–360 / 右 220–420"。✅
- 收起态宽度 `64` 在 Task 1 实现、Task 4 验收一致。✅
- 默认宽 `220/280` 在 Task 2、Task 4 一致。✅

**4. 一个发现并已修复的问题：** Task 1 Step 3 拖拽手柄用 `absolute`，但 flex 子项默认 `position: static`，手柄会相对最近定位祖先错位。已在根容器类名加上 `relative`（Task 1 Step 3 代码块已是修正后版本）。
