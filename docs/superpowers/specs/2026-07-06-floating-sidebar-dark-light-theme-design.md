# 悬浮侧栏 + dark/light 主题改造

- **日期**：2026-07-06
- **状态**：已确认（待实现）
- **范围**：将现有固定三栏布局改为"ChatPanel 充满 + 左右悬浮可折叠卡片"，新增 dark/light 主题切换
- **参考**：`docs/superpowers/specs/2026-07-06-three-column-layout-design.md`（原三栏设计）

## 1. 背景与动机

现有布局为 flex 三栏：ProgressPanel（30%）/ ChatPanel（70%），ChatPanel 完成后挤压左栏、滑入 DeliveryPanel（40%）。问题：
- 侧栏固定占文档流，挤压 ChatPanel 视觉空间
- 配色为单一深色 slate，无主题切换
- 折叠按钮缺失，侧栏无法收起

新方案：ChatPanel 始终充满中间，左右侧栏改为悬浮卡片（overlay），可独立折叠/展开、可拖拽改变宽度；同时引入 dark/light 双主题。

## 2. 核心交互

### 2.1 布局

```
┌───────────TopBar───────────┐
│ logo        [🌙] [重新开始] │   ← TopBar：logo + 主题切换 + 重置（不再有进度环）
├────────────────────────────┤
│  ┌─┐                  ┌─┐  │
│  │P│   ChatPanel      │D│  │   ← 侧栏 overlay 悬浮（有阴影），不占文档流
│  │r│   充满中间         │e│  │
│  │o│                  │l│  │
│  │g│ [›]        [‹]   │  │  │   ← 侧栏隐藏时，折叠按钮浮在 ChatPanel 左/右上角
│  │ │                  │ │  │
│  └─┘                  └─┘  │
└────────────────────────────┘
```

### 2.2 侧栏（ProgressPanel / DeliveryPanel）

- **样式**：绝对定位悬浮（`absolute top-0 bottom-0`，从 TopBar 底边开始覆盖），四周圆角，`shadow-xl`
- **折叠态**：完全隐藏（`opacity-0 pointer-events-none` + 向外 `translate-x`），无边缘竖条
- **宽度**：默认左侧 320px、右侧 360px；用户可拖拽边缘手柄改变宽度，范围 240–560px；松手后持久化到 localStorage
- **顶部**：标题 + 折叠按钮（chevron 指向外侧）
  - 左侧栏标题"采集进度" + 进度环（从 TopBar 移过来）
  - 右侧栏标题"交付物"

### 2.3 折叠/展开按钮位置

- **侧栏隐藏时**：按钮用 `absolute` 浮在 ChatPanel 左上 / 右上角（z-10），半透明 `bg-surface/80` + `backdrop-blur`
- **侧栏展开时**：ChatPanel 角落对应按钮消失，按钮"移到"侧栏卡片顶部（实为侧栏自己的关闭按钮）
- 左按钮图标 `›`（chevron 指左，表示展开左栏），右按钮图标 `‹`

### 2.4 关闭侧栏

仅通过侧栏卡片顶部的折叠按钮 toggle（不再点 ChatPanel 角落按钮，因为展开后角落按钮已消失）。

### 2.5 交付栏展开时机

- **随时可手动展开**（右侧 ChatPanel 角落按钮始终可用）
- **聊天完成后自动展开一次**（保留原 `onComplete` 行为，用户可手动收起）

### 2.6 主题切换

- TopBar 加日/月 SVG 图标按钮，点击 toggle dark/light
- 主题状态存 localStorage，下次访问记住
- dark 为默认（`:root` 定义 dark 值），`.light` 类覆盖

## 3. 配色方案（Slate 中性灰）

CSS 变量 + Tailwind 语义 token。组件代码零改动（所有 `bg-surface`/`text-primary`/`border-idle` 等类名照常工作）。

| token | dark | light |
|---|---|---|
| base | `#0f172a` | `#ffffff` |
| surface | `#1e293b` | `#f1f5f9` |
| active-surface | `#172554` | `#dbeafe` |
| primary | `#e2e8f0` | `#0f172a` |
| secondary | `#94a3b8` | `#475569` |
| muted | `#64748b` | `#94a3b8` |
| accent | `#3b82f6` | `#3b82f6` |
| done | `#34d399` | `#10b981` |
| idle | `#475569` | `#cbd5e1` |

## 4. 架构

### 4.1 文件结构

```
frontend/src/
├── App.tsx                      ← 改：承载主题 + 侧栏开关/宽度状态，重组布局
├── index.css                    ← 改：加 :root 和 .light 的 CSS 变量定义
├── components/
│   ├── TopBar.tsx               ← 改：加主题切换按钮，移除进度环，移除宽度挤压逻辑
│   ├── ChatPanel/
│   │   └── ChatPanel.tsx        ← 改：加两个浮在角落的折叠按钮
│   ├── ProgressPanel/
│   │   └── ProgressPanel.tsx    ← 改：顶部加进度环（从 TopBar 迁来）
│   ├── DeliveryPanel/
│   │   └── DeliveryPanel.tsx    ← 不改
│   └── Sidebar.tsx              ← 新建：通用悬浮卡片容器 + 拖拽 resize
├── state/
│   └── theme.ts                 ← 新建：useTheme hook
└── tailwind.config.js           ← 改：颜色改为 CSS 变量引用
```

### 4.2 状态管理

两个独立 UI 状态 + 两个宽度状态，都放在 `App.tsx`（与表单数据无关，不进 FormContext）：

```ts
const [progressOpen, setProgressOpen] = useState(false)
const [deliveryOpen, setDeliveryOpen] = useState(false)
const [progressWidth, setProgressWidth] = useState(
  () => Number(localStorage.getItem('sidebar.progress.width')) || 320
)
const [deliveryWidth, setDeliveryWidth] = useState(
  () => Number(localStorage.getItem('sidebar.delivery.width')) || 360
)
const { theme, toggleTheme } = useTheme()
```

### 4.3 渲染层级

```tsx
<div className="h-full flex flex-col bg-base text-primary">
  <TopBar theme={theme} onToggleTheme={toggleTheme} onReset={...} />
  <div className="relative flex-1 overflow-hidden">
    <div className="absolute inset-0">
      <ChatPanel
        progressOpen={progressOpen}
        deliveryOpen={deliveryOpen}
        onToggleProgress={() => setProgressOpen(o => !o)}
        onToggleDelivery={() => setDeliveryOpen(o => !o)}
        onComplete={() => setDeliveryOpen(true)}
      />
    </div>
    <Sidebar side="left" open={progressOpen} onClose={...} title="采集进度"
             width={progressWidth} onWidthChange={setProgressWidth}>
      <ProgressPanel />
    </Sidebar>
    <Sidebar side="right" open={deliveryOpen} onClose={...} title="交付物"
             width={deliveryWidth} onWidthChange={setDeliveryWidth}>
      <DeliveryPanel />
    </Sidebar>
  </div>
</div>
```

ChatPanel 充满 `relative` 容器（`absolute inset-0`），两个 Sidebar 绝对定位悬浮其上。

## 5. 组件接口

### 5.1 `useTheme`（`state/theme.ts`）

```ts
type Theme = 'dark' | 'light'
export function useTheme(): { theme: Theme; toggleTheme: () => void }
```

- 初始化：读 `localStorage.getItem('theme')`，无值默认 `'dark'`
- 副作用：`useEffect` 写 `document.documentElement.classList`（dark 默认不加类，light 加 `.light`），持久化 localStorage

### 5.2 `Sidebar`（`components/Sidebar.tsx`）

```tsx
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

职责：
- 绝对定位悬浮（`absolute top-0 bottom-0` + `left-0`/`right-0`），四周圆角，`shadow-xl`
- `open=false`：`opacity-0 pointer-events-none` + 向外 `translate-x-full` + `transition`
- `open=true`：归位 + `opacity-100`
- 顶部一行：标题（左）+ 折叠按钮（右，chevron 指向外侧）
- 拖拽手柄：靠 ChatPanel 那一侧边缘 4px 宽条，`cursor-col-resize`，hover 变 accent 色

### 5.3 拖拽 resize 逻辑

Sidebar 只负责"计算新宽度并回调 `onWidthChange`"，**不碰 localStorage**。持久化由 App 在 `onWidthChange` 回调里做（Sidebar 保持纯粹、可测试）。

```ts
// Sidebar.tsx 内
function startResize(e: React.MouseEvent) {
  const startX = e.clientX
  const startWidth = width
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'

  function onMove(e: MouseEvent) {
    const delta = e.clientX - startX
    const next = side === 'left' ? startWidth + delta : startWidth - delta
    onWidthChange(clamp(next, minWidth, maxWidth))
  }
  function onUp() {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}
```

```ts
// App.tsx 内（持久化责任在 App）
const [progressWidth, setProgressWidth] = useState(
  () => Number(localStorage.getItem('sidebar.progress.width')) || 320
)
function handleProgressWidthChange(w: number) {
  setProgressWidth(w)
  localStorage.setItem('sidebar.progress.width', String(w))
}
// 传给 Sidebar 的 onWidthChange={handleProgressWidthChange}
```

### 5.4 `TopBar`（改）

- 移除：进度环（迁到 ProgressPanel 顶部）
- 新增：主题切换按钮（日/月 SVG），位于重置按钮左侧
- 保留：logo + 标题 + 重置按钮

```
[logo] 直播间视觉向量化智能客服        [🌙/☀️] [重新开始]
```

### 5.5 `ChatPanel`（改）

新增 props：

```ts
interface ChatPanelProps {
  onComplete?: () => void
  progressOpen: boolean
  deliveryOpen: boolean
  onToggleProgress: () => void
  onToggleDelivery: () => void
}
```

内部最外层加 `relative`，在消息区上方绝对定位两个折叠按钮：

```tsx
{!progressOpen && (
  <button className="absolute top-3 left-3 z-10 p-2 rounded-card bg-surface/80 backdrop-blur shadow hover:bg-surface"
          onClick={onToggleProgress}>
    <ChevronRight />  {/* 指向左栏 */}
  </button>
)}
{!deliveryOpen && (
  <button className="absolute top-3 right-3 z-10 ..." onClick={onToggleDelivery}>
    <ChevronLeft />
  </button>
)}
```

### 5.6 `ProgressPanel`（改）

顶部加进度环（从 TopBar 迁来）：环 + "N/N 已采集" 文案。进度环 SVG 颜色用 CSS 变量（`rgb(var(--color-idle))` / `rgb(var(--color-done))`）。

## 6. 测试策略

- **useTheme 单测**：切换后 localStorage 写入正确值，classList 正确切换
- **手动验证清单**（dev server）：
  1. 切换主题，所有区域颜色正确切换，刷新后保持
  2. 左/右折叠按钮：隐藏时浮在 ChatPanel 角落，点击展开侧栏
  3. 侧栏展开后折叠按钮移到卡片顶部，点击关闭
  4. 拖拽侧栏边缘改变宽度，松手后持久化，刷新后保持
  5. 聊天完成后右侧交付栏自动展开
  6. 重置后侧栏关闭、宽度重置或保留（保留）

## 7. 改动清单

| 文件 | 类型 | 改动 |
|---|---|---|
| `frontend/src/index.css` | 改 | 加 `:root` 和 `.light` CSS 变量 |
| `frontend/tailwind.config.js` | 改 | 颜色改为 CSS 变量引用（保留 `<alpha-value>`） |
| `frontend/src/state/theme.ts` | 新建 | `useTheme` hook |
| `frontend/src/components/Sidebar.tsx` | 新建 | 悬浮卡片容器 + 拖拽 resize |
| `frontend/src/App.tsx` | 改 | 重组三栏为 overlay，承载侧栏开关/宽度状态 |
| `frontend/src/components/TopBar.tsx` | 改 | 加主题切换按钮，移除进度环 |
| `frontend/src/components/ChatPanel/ChatPanel.tsx` | 改 | 加浮在角落的折叠按钮 |
| `frontend/src/components/ProgressPanel/ProgressPanel.tsx` | 改 | 顶部加进度环 |
| `DeliveryPanel` / `MessageBubble` / `ChoiceCard` / `DimensionInput` / `ImageUpload` / `OrderForm` | 不改 | 类名照常工作 |
