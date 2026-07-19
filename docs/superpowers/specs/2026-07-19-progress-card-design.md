# ProgressCard 悬浮任务卡片设计

- 日期:2026-07-19
- 分支:`feat/ui-refinement`
- 范围:前端 UI 重构
- 关联:`frontend/src/components/ProgressPanel/`、`frontend/src/App.tsx`、`frontend/src/components/TopBar.tsx`

## 一、目标

把当前左侧 Sidebar 内的平铺式 `ProgressPanel` 替换为 **左上角悬浮的独立任务卡片**(`ProgressCard`),视觉与交互对齐 Codex TODO 卡片、Linear 任务列表。

核心诉求:**不占据用户心智**——卡片小、悬浮、安静;完成项自动收束,焦点永远在"当前在问什么"。

## 二、背景与现状

### 当前实现的问题

`ProgressPanel.tsx`(48 行)装在左 `Sidebar` 容器内,作为三栏布局的左栏:

- 平铺渲染 10 章节,已完成/进行中/待办混在一起,扫视无层次
- `status` 字段依赖后端 `replace_state` 时回填,显示是否可靠存疑
- 摘要 `truncate` 过狠,长字段信息丢失
- 没用 `filledCount`,章节级进度不可见
- 不可点击、不可展开,看不到字段明细
- 当前章节高亮偏弱(`ring-accent/30`)
- `skipped` 与 `pending` 视觉几乎无区分

### 项目布局约束(已确认)

- 左 Sidebar 容器:默认宽 320px,可拖拽调宽 240~560px,占满屏高,可关闭
- TopBar 高度约 56px
- ChatPanel 中央占剩余宽度
- 双主题:dark/light(CSS 变量 + Tailwind 语义 token:base/surface/active-surface/primary/secondary/muted/idle/accent/done)

### 数据来源

- 章节定义:`frontend/src/data/sections.ts`(codegen 产物,10 章节)
- 字段类型:`text`/`choice-single`/`choice-multi`/`dimension`/`image`/`table`
- 表单状态:`StudioFormState`(`useReducer` 管理),由后端 `/api/chat` 返回 `form_state` 后整体 `replace_state`
- 章节状态:`SectionState.status` ∈ `'pending' | 'active' | 'complete' | 'skipped'`
- 当前章节:`state.currentSectionId`
- 进度计算:`utils/summary.ts` 的 `filledCount(section, def)` 返回 `{filled, total}`

## 三、整体方案

### 3.1 布局变更(项目级)

**删除**左 Sidebar 承载 ProgressPanel 的整条链路,**新建**独立悬浮 `ProgressCard` 组件。

| 项 | 旧 | 新 |
|---|---|---|
| ProgressPanel 容器 | 左 Sidebar 的 children,撑满 | 独立 `position: fixed`,悬浮 |
| 定位 | flex 子元素,顶栏下到底栏 | `fixed`,默认 `top-16 left-4`,可拖拽 |
| ChatPanel 布局 | `paddingLeft: progressWidth + 12` | `padding: 0`(占满中央) |
| 左 Sidebar 实例 | App.tsx:85-94 整段 | 删除 |
| `progressOpen`/`progressWidth`/`PROGRESS_WIDTH_KEY` | App.tsx:40-43 | 删除 |
| TopBar 左侧开关 | 切换 `progressOpen` | 切换卡片显隐(`progressCardVisible`) |
| 文件 | `ProgressPanel.tsx` | 删除;新建 `ProgressCard.tsx` |

**保留**右 Sidebar(`DeliveryPanel`)不动。

### 3.2 卡片定位与尺寸

- 定位:`fixed`,默认 `top: 80px`(TopBar 下方 24px)、`left: 16px`
- 宽度:**固定 280px**(不响应式)
- 高度:`auto`,最大 `70vh`,超出内部 `overflow-y-auto`
- 层级:`z-30`(在 ChatPanel 之上、Modal 之下)
- 背景:`bg-surface/95 backdrop-blur-md`(半透 + 毛玻璃)
- 圆角:`rounded-xl`(12px)
- 阴影:`shadow-2xl ring-1 ring-white/10`

### 3.3 卡片结构

```
┌─ 采集进度 3/10 ────────────────── ⋯ □ ┐
│  (header:拖拽手柄区)                    │
├────────────────────────────────────────┤
│  ∧ ✓ 已完成 2 项                  ← 折叠 │
│                                        │
│  ◐ 直播间现状                    5/8    │
│    ▸ 当前在问: 开播时长                  │
│                                        │
│  ○ 场地条件                             │
│  ○ 预算                                 │
│  ○ 商品与品牌视觉                        │
│  ○ 主播信息                             │
│  ○ 现有设备                             │
│  ○ 需求与目标                            │
│  ○ 客服备注                             │
│                                        │
├────────────────────────────────────────┤
│  ✓ 2  ·  ◐ 1  ·  7 待           ← 汇总 │
└────────────────────────────────────────┘
```

四个区块:
1. **Header**:标题 `采集进度 N/M` + 右侧 `⋯`(预留,占位)、`□`(显隐切换/全屏,本期占位不接功能)
2. **已完成分组**:`∧ ✓ 已完成 N 项`,默认折叠;展开后单行列出每个已完成章节(带 `✓` 图标)
3. **进行中 + 待办区**:当前章节置顶,带"当前在问: xxx"子行;其余 pending 章节按顺序单行列出
4. **底部汇总**:`✓ N · ◐ N · N 待`

### 3.4 状态图标系统

| 状态 | 图标 | 颜色 | 动效 |
|---|---|---|---|
| `pending` | `○` 空心圆环 | `text-idle` | 无 |
| `active` | `◐` 半圆 | `text-accent` | `animate-pulse`(1s) |
| `complete` | `✓` 对勾圆 | `text-done` | 无 |
| `skipped` | `—` 横杠 | `text-idle opacity-50` | 无 |

单个 `StatusIcon` 组件按 `status` prop 渲染对应 SVG(circle-ring / half-circle / check-circle / dash 4 种),统一 14×14、`stroke-width: 1.5`、`currentColor`。

### 3.5 交互

**点击行为**:
- 点当前/未来章节行 → 展开/收起该章节字段明细(单列 `label + value`)
- 点"已完成 N 项"行 → 展开/收起已完成分组
- header 区域**不接点击**(避免误触),只接拖拽
- header 右侧 `⋯`、`□` 按钮 `stopPropagation`,本期不接功能

**展开字段明细**:
- 单列布局,每行 `[label 灰色] [value 主色]`
- 已填字段:`text-secondary` 标签 + `text-primary` 值
- 未填必填字段:`text-muted` 标签 + `(未填)` 占位
- 不可见字段(`visibleIf` 不满足):**不显示**
- 字段值显示用现有 `utils/summary.ts` 的 `valueToText` 逻辑(需 export)

**视觉细节**:
- 当前章节行:`bg-active-surface/50` 微高亮(不用 ring,避免视觉重)
- 行高 36px,字号 `text-[13px]`
- 内边距:行 `px-3 py-2`,明细 `ml-6 px-3 py-1.5 text-[12px]`
- hover:行 `bg-base/50` 过渡 150ms

### 3.6 拖拽行为

**手柄**:整个 header 区。
- 默认 `cursor-default`
- hover header → `cursor-move` + 标题字色 `text-secondary → text-primary`

**移动**:
- `mousedown` 记录 `{ mouseX, mouseY, cardX, cardY }`
- `mousemove` 计算位移,更新 `transform: translate(x, y)`
- `mouseup` 结束、写 `localStorage`
- 拖拽中卡片 `opacity-90 scale-[0.98]`,过渡 100ms
- 拖拽中强制收起内部展开项(防抖动)

**边缘避让**(clamp):
- `x ∈ [8, viewportWidth − 280 − 8]`
- `y ∈ [TopBar高度 + 8, viewportHeight − 80 − 8]`
- 监听 `window resize` 重新 clamp

**持久化**:
- key:`progresscard.pos`
- 值:`{ x: number, y: number }`
- 初次无 key → 默认 `{ x: 16, y: 80 }`

**实现参考**:`frontend/src/components/Sidebar.tsx:25-47` 的拖拽调宽逻辑,改造成拖拽移动。

## 四、组件拆分

```
frontend/src/components/ProgressCard/
├── ProgressCard.tsx          # 主组件:容器 + 拖拽 + 显隐 + header(单行 UI 内联)
├── SectionList.tsx           # 已完成分组 + 进行中 + 待办列表
├── SectionRow.tsx            # 单章节行(图标 + 标题 + 进度 + 展开)
├── FieldDetail.tsx           # 展开后的字段明细列表
├── StatusIcon.tsx            # 状态图标(4 态,单组件)
└── useCardDrag.ts            # 拖拽 hook
```

每个文件单一职责,200 行以内。header 只有 1 行 UI,不单独拆文件,内联在 `ProgressCard.tsx`。

**数据流**:
```
App.tsx
  └─ <ProgressCard visible={progressCardVisible} />
       ├─ useCardDrag() → { x, y, dragging, onHeaderMouseDown }
       ├─ useFormState() → state
       ├─ Header 内联(标题 + 按钮占位)
       ├─ SectionList
       │    ├─ 已完成分组(折叠)
       │    ├─ 当前章节(置顶 + "当前在问")
       │    └─ pending 章节列表
       │       └─ SectionRow → FieldDetail(展开时)
       └─ 底部汇总
```

## 五、样式与主题

### 5.1 Tailwind 类名规范

只用项目已有的语义 token(见 `frontend/src/index.css`),**不引入新颜色**:

- 卡片容器:`bg-surface/95 backdrop-blur-md rounded-xl shadow-2xl ring-1 ring-white/10`
- Header:`px-3 py-2.5 border-b border-idle/30`
- 章节行:`px-3 py-2 rounded-md hover:bg-base/50 transition-colors`
- 当前章节行:`bg-active-surface/50`
- 标签:`text-secondary text-[12px]`
- 值:`text-primary text-[12px]`
- 未填:`text-muted text-[12px]`
- 状态图标:`text-idle`/`text-accent`/`text-done`
- 汇总行:`text-[11px] text-muted`

### 5.2 双主题适配

dark/light 由现有 `state/theme.ts` + CSS 变量处理,ProgressCard 只用语义 token,无需写主题判断。

## 六、App.tsx 改动

```tsx
// 删除
const [progressOpen, setProgressOpen] = useState(false)
const [progressWidth, setProgressWidth] = useState(...)
function handleProgressWidth(w) { ... }
const PROGRESS_WIDTH_KEY = 'sidebar.progress.width'
// paddingLeft: progressOpen ? progressWidth + 12 : 0  →  paddingLeft: 0
// <Sidebar side="left" ...><ProgressPanel /></Sidebar>  →  删除

// 新增
const [progressCardVisible, setProgressCardVisible] = useState(true)
// TopBar onToggleProgress={() => setProgressCardVisible(v => !v)}
// <ProgressCard visible={progressCardVisible} />
```

## 七、TopBar.tsx 改动

左侧开关按钮图标换为眼睛(`Eye`/`EyeOff`),`progressOpen` prop 改为 `progressVisible`,语义从"展开侧栏"改为"显示进度卡片"。

## 八、删除项清单

- `frontend/src/components/ProgressPanel/ProgressPanel.tsx`
- `frontend/src/components/ProgressPanel/` 整个目录(若空)
- `App.tsx` 中 `progressOpen`/`progressWidth`/`PROGRESS_WIDTH_KEY`/`handleProgressWidth`
- `App.tsx` 中 `<Sidebar side="left">` 实例

**不删** `Sidebar.tsx` 本身——右侧 `DeliveryPanel` 仍在用。

## 九、不做的事(YAGNI)

- ❌ 卡片不响应宽度变化(固定 280px)
- ❌ `⋯` 按钮不接下拉菜单(占位)
- ❌ `□` 按钮不接全屏/弹窗(占位)
- ❌ 章节不支持手动改状态(`set_active_section` action 不接)
- ❌ 不做字段值的多列网格(单列)
- ❌ 不做"跳转到对话对应位置"(章节只展开明细,不联动 ChatPanel)
- ❌ 不动 `Sidebar.tsx` 的拖拽调宽逻辑(右侧还在用)
- ❌ 不动 `reducer.ts` 的 `status` 重算(数据来源问题留后续 PR)

## 十、验收标准

1. 启动前端,左上角出现悬浮卡片,280px 宽
2. dark/light 切换,卡片颜色都正确,无对比度问题
3. 当前章节(`active`)置顶,带"当前在问: xxx"子行,`◐` 图标脉冲
4. 已完成章节折叠为"✓ 已完成 N 项"一行,点击展开
5. 点未完成章节 → 展开字段明细,已填/未填区分清晰
6. 拖拽 header 移动卡片,松手后位置存 `localStorage`,刷新仍在
7. 拖到屏幕边缘被 clamp,不会拖丢
8. TopBar 左侧按钮可隐藏/显示卡片
9. 中央 ChatPanel 占满全宽,无 `paddingLeft` 残留
10. `npm run test` 通过,无类型错误(`npm run lint`)

## 十一、风险

- **`status` 字段可靠性**:agent 模式下 `replace_state` 是否回填了正确的 status 未确认。本期**不改后端**,先信任后端返回;若实测发现 status 不准,在 ProgressCard 内部用 `filledCount` 自行推算(`filled>=total && total>0` → complete,`filled>0` → active,否则 pending),作为前端兜底。
- **拖拽性能**:`mousemove` 高频触发,需用 `requestAnimationFrame` 节流或直接 setState(React 18 自动批处理,够用)。
- **z-index 冲突**:卡片 `z-30`,需确认无其他元素抢焦点;Modal/Toast 若有应在 `z-40+`。
