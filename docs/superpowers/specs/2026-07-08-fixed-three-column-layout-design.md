# 三栏布局迭代 · 悬浮侧栏 → 固定常驻三栏

- **日期**：2026-07-08
- **状态**：已确认（待实现）
- **范围**：将"默认收起、点击悬浮弹出"的侧栏交互，改为"默认三栏常驻、可收起为窄条、可拖拽调宽"
- **前置**：
  - `2026-07-06-three-column-layout-design.md`（原三栏设计，已实现）
  - commit `914ae98`（悬浮侧栏 + dark/light 主题改造，即本 spec 的改造对象）

## 1. 背景与动机

当前实现（commit 914ae98）中，左右侧栏默认收起、点击 TopBar 按钮后以**绝对定位浮层**形式从两侧滑入，中间 ChatPanel 通过 `padding-transition` 让出空间。问题：

- **默认收起**：首次进入看不到采集进度和交付物全貌，三栏分工的优势被弱化
- **浮层避让**：中间区用 `paddingLeft/paddingRight` 动态让位，逻辑复杂、视觉有"盖住"感
- **不像工作台**：参考 Codex / ChatGPT，用户期望三栏常驻、可收起进入"专注模式"

目标：改为 flex 行布局的常驻三栏，中间区 `flex:1` 自然吃掉剩余空间，侧栏可收起为 64px 窄条。

## 2. 视觉决策（已确认）

| 维度 | 决策 |
|---|---|
| 整体布局 | flex 行布局，三栏平铺，**无绝对定位浮层** |
| 默认栏宽 | 左 220px / 中 flex:1 / 右 280px |
| 默认开合 | 左右栏**默认全开**（原为默认收起） |
| 收起态 | 栏宽过渡到 64px 窄条，内容隐藏，仅留展开图标 |
| 栏间间隙 | 保留 8px gap（沿用原 `left-2/right-2` 节奏） |
| 圆角 | 每栏独立 `rounded-[12px]`（间隙分隔，无对接缝问题） |
| 可拖拽调宽 | 保留，仅 open 时生效；范围 左 180–360 / 右 220–420 |
| 可收起按钮 | 保留 TopBar 现有开关按钮，逻辑零改动 |
| localStorage 旧值 | 保留（已用过老版本的用户沿用其调过的宽度，不强制覆盖） |
| 重置（重新开始） | 不动侧栏开合状态（原代码会折叠，现移除该副作用） |

## 3. 整体布局

```
┌─ App (h-full flex flex-col bg-base) ──────────────────────────┐
│  TopBar (h-12, 固定高)                                          │
├─ div.layout (flex-1 flex gap-2 p-2 overflow-hidden) ──────────┤
│                                                                │
│  [Sidebar.L]   [ChatPanel]              [Sidebar.R]            │
│   width:        flex: 1                 width:                │
│   open?220      min-w-0                 open?280              │
│   :64                                  :64                    │
│   transition                            transition             │
│   -[width] 300ms                        -[width] 300ms        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 关键变化（vs 现状）

1. `App.tsx` 删除 `relative` + `absolute` 浮层 + `paddingLeft/paddingRight` 过渡逻辑
2. 改为 `flex` 行布局，三栏平铺
3. `Sidebar.tsx`：从"绝对定位浮层"改为"flex 子项"
4. 栏宽由 `open` 状态决定（展开=用户拖拽值，收起=64）
5. 默认状态：`progressOpen=true`、`deliveryOpen=true`

## 4. Sidebar 组件改造

### 当前结构（绝对定位浮层）

```tsx
<div className="absolute top-1 bottom-2 left-2 right-2 ... transition-transform">
  ...
</div>
```

### 新结构（flex 子项）

```tsx
<div
  className="flex flex-col bg-surface rounded-[12px] shadow-xl ring-1 ring-white/10
             transition-[width] duration-300 overflow-hidden shrink-0"
  style={{ width: open ? width : 64 }}
>
  {/* header：展开=标题+extra，收起=仅展开图标 */}
  <div className="flex items-center px-4 py-3 border-b border-idle">
    {open ? (
      <><h2 className="text-sm font-semibold text-primary">{title}</h2>{headerExtra}</>
    ) : (
      <button onClick={onToggle} aria-label={`展开${title}`}>
        <ExpandIcon side={side} />
      </button>
    )}
  </div>

  {/* body：展开=children，收起=空（overflow-hidden 裁剪） */}
  <div className="flex-1 hide-scrollbar">
    {open && children}
  </div>

  {/* 拖拽手柄：仅 open 时挂载 */}
  {open && <ResizeHandle side={side} onResize={...} />}
</div>
```

### 拖拽逻辑

- `open=true`：保留现有 mousedown/mousemove/mouseup 拖拽逻辑
- `open=false`：不挂载手柄，不响应拖拽
- 边界：`clamp(next, minWidth, maxWidth)`，默认 左 180–360 / 右 220–420

### 新增 prop

`Sidebar` 需要 `onToggle: () => void`，供收起态的展开图标调用。由 `App` 传入 `() => setProgressOpen(o => !o)` / `() => setDeliveryOpen(o => !o)`（与 TopBar 开关共用同一回调源）。

### 两个切换入口的行为一致

- TopBar 开关按钮：`open=true` 时点击收起，`open=false` 时点击展开
- 收起态窄条的展开图标：点击展开（此时 `open=false`，唯一动作就是展开）
- 两者都调用同一 `onToggle`，状态语义一致，不出现"两个入口行为冲突"

### 展开图标朝向

- 左栏收起态：`›`（指向右，提示展开后内容在右）
- 右栏收起态：`‹`（指向左，提示展开后内容在左）
- 用 `side` prop 决定，复用现有 TopBar 开关的箭头 SVG（已是 open/close 两套）

## 5. TopBar 改动

- 高度 `h-10` → `h-12`（40px → 48px）
- 两个"展开/收起"按钮的图标方向逻辑**保持不变**（复用现有 open/close 两套箭头）
- 其余元素（头像、logo、品牌名、主题切换、重置）不动

## 6. App.tsx 改动

```diff
  const [resetKey, setResetKey] = useState(0)
- const [progressOpen, setProgressOpen] = useState(false)
- const [deliveryOpen, setDeliveryOpen] = useState(false)
- const [progressWidth, setProgressWidth] = useState(() => loadWidth(PROGRESS_WIDTH_KEY, 320))
- const [deliveryWidth, setDeliveryWidth] = useState(() => loadWidth(DELIVERY_WIDTH_KEY, 360))
+ const [progressOpen, setProgressOpen] = useState(true)
+ const [deliveryOpen, setDeliveryOpen] = useState(true)
+ const [progressWidth, setProgressWidth] = useState(() => loadWidth(PROGRESS_WIDTH_KEY, 220))
+ const [deliveryWidth, setDeliveryWidth] = useState(() => loadWidth(DELIVERY_WIDTH_KEY, 280))

  function handleReset() {
    setResetKey((k) => k + 1)
-   setProgressOpen(false)
-   setDeliveryOpen(false)
  }

  return (
    <FormProvider key={resetKey}>
      <div className="h-full flex flex-col bg-base text-primary">
        <TopBar ... />
-       <div className="relative flex-1 overflow-hidden">
-         <div className="absolute inset-0 transition-[padding] duration-300"
-              style={{ paddingLeft: progressOpen ? progressWidth + 12 : 0,
-                       paddingRight: deliveryOpen ? deliveryWidth + 12 : 0 }}>
-           <ChatPanel onComplete={() => setDeliveryOpen(true)} />
-         </div>
-         <Sidebar side="left" open={progressOpen} ... />
-         <Sidebar side="right" open={deliveryOpen} ... />
+       <div className="flex-1 flex gap-2 p-2 overflow-hidden">
+         <Sidebar side="left" open={progressOpen}
+                  onToggle={() => setProgressOpen(o => !o)} ... >
+           <ProgressPanel />
+         </Sidebar>
+         <div className="flex-1 min-w-0">
+           <ChatPanel onComplete={() => setDeliveryOpen(true)} />
+         </div>
+         <Sidebar side="right" open={deliveryOpen}
+                  onToggle={() => setDeliveryOpen(o => !o)} ... >
+           <DeliveryPanel />
+         </Sidebar>
        </div>
      </div>
    </FormProvider>
  )
```

### 数据流（不变）

- `progressOpen/deliveryOpen` 由 `App` 持有，传给 `Sidebar.open`
- `progressWidth/deliveryWidth` 仍由 `App` 状态管理，拖拽时更新 + 写 localStorage
- `TopBar` 开关按钮 → 调 `setProgressOpen/setDeliveryOpen`，逻辑零改动
- `ChatPanel.onComplete` → `setDeliveryOpen(true)`，语义从"弹出"变为"确保打开"（默认已开，无副作用），保留

## 7. 不变的部分

- `ProgressPanel` / `DeliveryPanel` / `OrderForm` / `ChatPanel` 全部子组件
- `FormContext` / `reducer` / `initialState` / `sections` / `scriptedFlow` / `chatController`
- `schema` types / `summary` utils / `ProgressRing`
- TopBar 除高度外的所有元素
- Tailwind tokens / 主题切换逻辑
- 现有 16 个测试

## 8. 技术改动清单

```
修改：
  src/App.tsx                  # flex 布局替代浮层；默认 open=true；默认宽 220/280；reset 去掉折叠副作用
  src/components/Sidebar.tsx   # 绝对定位 → flex 子项；width 由 open 决定；收起态 64px 仅展开图标；新增 onToggle prop
  src/components/TopBar.tsx    # h-10 → h-12

不变：
  其余所有文件
```

## 9. 验收标准

- [ ] 默认进入：三栏全开，左 220 / 中 flex / 右 280
- [ ] 中间聊天区 `flex:1`，侧栏收起时自然扩展吃掉空间，无遮挡
- [ ] 点 TopBar 开关或侧栏窄条展开图标：侧栏宽度过渡 220↔64（或 280↔64），300ms 动画
- [ ] 收起态 64px 窄条：仅垂直居中展开图标，内容隐藏
- [ ] 展开态可拖拽调宽，范围 左 180–360 / 右 220–420，松手后写 localStorage
- [ ] 收起态不可拖拽
- [ ] 栏间 8px gap，每栏独立圆角 12px + 阴影 + ring
- [ ] TopBar 高度 48px，开关按钮图标方向与开合状态对应
- [ ] 重新开始：仅重置表单，侧栏开合与宽度保持当前状态
- [ ] `npm run build` 0 错误
- [ ] `npm test` 全通过
