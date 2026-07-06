# 三栏布局重构 · 采集进度 + 聊天 + 交付物/订单

- **日期**：2026-07-06
- **状态**：已确认（待实现）
- **范围**：将现有 2 栏布局重构为 3 栏；新增订单表单组件
- **参考**：`docs/superpowers/specs/2026-07-06-livestream-cs-ui-design.md`（原 2 栏设计）

## 1. 背景与动机

现有布局为 2 栏：左 ChatPanel（55%）+ 右 Dashboard 卡片网格（45%），完成后跳转 ReportPreview 页。问题：
- 卡片网格在采集期与聊天功能重叠（两边都在"采集"）
- 完成态跳页，丢失对话上下文
- 无订单/下单环节

新布局拆为三栏分工：**进度 | 对话 | 交付**，每栏职责单一，采集完成后不跳页而是右栏滑入。

## 2. 视觉决策（已确认）

| 维度 | 决策 |
|---|---|
| 整体布局 | 三栏：左进度 / 中聊天 / 右交付物+订单 |
| 采集期右栏 | 隐藏，实际为 左 ~30% + 中 ~70% 两栏 |
| 完成时右栏 | 从右侧滑入，中栏收窄到 ~40%，变为 左 20% + 中 40% + 右 40% 三栏 |
| 左栏交互 | 只读，不可点编辑（编辑走聊天，本阶段为 future） |
| 右栏订单 | UI 模拟订单，不调后端 |

## 3. 整体布局

```
┌─────────────────────────────────────────────────────────────┐
│ TopBar：Logo · 完成度 X/47 · 重新开始                          │
├──────────┬──────────────────────────┬───────────────────────┤
│ 左 ~20%  │ 中 ~40%                   │ 右 ~40%               │
│ Progress │ ChatPanel                 │ DeliveryPanel         │
│ Panel    │                           │                       │
│          │ AI/User 气泡              │ 〔采集完成后滑入〕     │
│ 11 节    │ 内嵌选项/尺寸/图片卡片     │                       │
│ 垂直列表 │ 输入框                    │ · 方案概要            │
│ 状态色条 │                           │ · 4 个交付物卡片       │
│ 摘要 1 行 │                          │ · 订单表单 + 提交按钮  │
│ (只读)   │                           │                       │
└──────────┴──────────────────────────┴───────────────────────┘
```

### 采集期（未完成）
右栏不渲染。布局为 左 ~30% + 中 ~70% 两栏。

### 完成期
右栏从右侧滑入（CSS transition），中栏收窄到 ~40%。
- 触发条件：所有必填字段完成（与原 Dashboard 的 `allDone` 计算一致）
- 由 App 持有 `showDelivery: boolean` state 控制
- 滑入动画：`transform: translateX(100%) → translateX(0)`，transition `300ms ease-out`

### 核心数据流
不变。聊天驱动 → dispatch update_field → StudioFormState → ProgressPanel 与 DeliveryPanel 订阅渲染。

## 4. 左栏 ProgressPanel（只读）

替代旧的 Dashboard 卡片网格。

### 布局
垂直紧凑列表，每节 1 行：
```
[状态色点] 节标题 · 摘要
```
- 示例：`● 三、直播间现状 · 已播 · 2000-1万观看`

### 状态色点
| 状态 | 颜色 | 视觉 |
|---|---|---|
| pending（未采集） | `bg-idle` (#475569) | 灰实心点 |
| active（进行中） | `bg-accent` (#2563eb) | 蓝实心点 + pulse 动画 |
| complete（完成） | `bg-done` (#34d399) | 绿实心点 + ✓ |

### 当前节高亮
当前 AI 正在问的节（`state.currentSectionId`）：行背景 `bg-active-surface` (#172554) + 左侧 3px `border-accent` 色条。

### 交互
**只读**。整列不可点击、不可编辑。
- 编辑能力本阶段不实现（原"点卡片就地展开"已移除）
- 后续演进：用户在聊天里说"改下预算"，AI 识别意图并 dispatch update_field（标记为 future）

### 数据来源
- `SECTIONS`（节元数据）
- `state.sections[id]`（每节状态与字段）
- `makeSummary(section, def)`（复用现有 utils）
- `filledCount(section, def)`（用于顶部进度，不在左栏单行显示）

## 5. 中栏 ChatPanel（基本不变）

完整复用现有：
- `ChatPanel.tsx`（容器 + 输入框 + scroll-to-bottom）
- `chatController.ts`（scriptedFlow 推进）
- `scriptedFlow.ts`（20 步问答脚本）
- 4 种气泡卡片：ChoiceCard / DimensionInput / ImageUpload / MessageBubble
- Task 6 fix 的 `updateValue` / `commitAndAdvance` 拆分逻辑

### 唯一调整
宽度从 55% 收窄到采集期 ~70% / 完成期 ~40%（由父布局 flex 控制，ChatPanel 自身代码不动）。

### 完成触发
原 ChatPanel 在最后一个 scripted step 回答后 dispatch `complete` + set `finished`。新增：同时调用 `onComplete?.()` prop 通知 App 显示右栏（App 将该 prop 接到 `setShowDelivery(true)`）。沿用现有 prop 模式（原 `onAllDone` 重命名为 `onComplete`，语义更准）。

## 6. 右栏 DeliveryPanel（新组件，完成时滑入）

采集完成 → 右栏滑入。分 3 段垂直滚动：

### A. 方案概要（顶部）
卡片形式，1 行展示关键字段：
- 客户名 / 品类 / 面积 / 预算 / 交付时间

数据来源：从 `state.sections` 提取对应字段值，用 `makeSummary` 或直接读字段。

### B. 4 个交付物卡片（中间）
复用原 ReportPreview 的占位思路，但改为卡片列表（不是整页）：
- 场景设计说明
- 设备参数清单
- 多视角效果图
- 向量化评分报告

每张：标题 + 灰色 placeholder 框（`bg-surface` + "[ Agent 生成中 · 占位 ]" 文案）。

### C. 订单表单（底部，新组件 OrderForm）
UI 模拟订单，字段：
| 字段 | 类型 | 默认值 |
|---|---|---|
| 客户名 | text | 预填 `customer.brand` |
| 联系电话 | text | 预填 `customer.phone` |
| 服务套餐 | select | 标准（选项：基础 5000 / 标准 15000 / 全包 30000） |
| 预估总价 | text（只读） | 按套餐自动填充 |
| 备注 | textarea | 空 |

**「发送订单」按钮**：
- 点击后按钮变绿 `bg-done` + 显示 ✓
- 顶部弹 toast / 行内提示："订单 #ORD-XXXX 已发送"（ORD- 后 4 位随机）
- 不调后端，仅 UI 状态变化
- 提交后表单变只读（不可再改），按钮文案变"已发送"

## 7. 删除的旧组件

| 组件 | 原因 |
|---|---|
| `src/components/Dashboard/` （Dashboard.tsx, SectionCard.tsx, CardExpanded.tsx） | 被 ProgressPanel 替代；就地编辑功能移除 |
| `src/components/FieldEditor.tsx` | 仅 CardExpanded 使用，随之删除 |
| `src/components/ReportPreview.tsx` | 完成态不跳页；内容拆入 DeliveryPanel 的 A/B 段 |

### 保留并复用
- `src/components/ChatPanel/` 全部（ChatPanel, MessageBubble, ChoiceCard, DimensionInput, ImageUpload, chatController）
- `src/data/sections.ts`, `src/data/scriptedFlow.ts`
- `src/state/` 全部（FormContext, reducer, initialState）
- `src/types/schema.ts`, `src/utils/summary.ts`
- `src/components/TopBar.tsx`（进度仍 X/47，不变）

## 8. 技术改动清单

```
新建：
  src/components/ProgressPanel/ProgressPanel.tsx   # 左栏
  src/components/DeliveryPanel/DeliveryPanel.tsx   # 右栏容器（A+B+C）
  src/components/DeliveryPanel/OrderForm.tsx       # 订单表单子组件

删除：
  src/components/Dashboard/                        # 旧卡片网格
  src/components/FieldEditor.tsx
  src/components/ReportPreview.tsx

修改：
  src/App.tsx                                  # 3 栏 flex 布局 + showDelivery state + 滑入动画
  src/components/ChatPanel/ChatPanel.tsx       # onAllDone prop 重命名为 onComplete（语义更准，触发显示右栏）
```

### 不变
- reducer / initialState / FormContext
- sections / scriptedFlow / chatController
- schema types / summary utils
- TopBar
- Tailwind tokens / 视觉风格

## 9. 验收标准

- [ ] 采集期：左 30% + 中 70%，无右栏
- [ ] 采集完成瞬间：右栏从右滑入（~300ms），变为 20/40/40 三栏
- [ ] 左栏 11 行列表，当前节高亮，状态色点正确
- [ ] 中栏聊天全流程不变（20 步问答、4 种卡片、确认按钮）
- [ ] 右栏方案概要显示 5 个关键字段
- [ ] 右栏 4 个交付物卡片占位
- [ ] 右栏订单表单：客户名/电话预填，套餐下拉，总价自动，发送按钮
- [ ] 点发送：按钮变绿 ✓ + "订单 #ORD-XXXX 已发送"，表单只读
- [ ] 重新开始：清空所有，回到 2 栏采集态
- [ ] `npm test` 全通过（现有 16 测试不变）
- [ ] `npm run build` 0 错误

## 10. 后续演进（不在本阶段）

1. 聊天编辑能力：用户说"改下预算"→ AI 识别意图 → dispatch update_field（需 LLM 或意图识别）
2. 真实订单提交：OrderForm 的 onSubmit 接后端 API
3. 交付物真实生成：右侧 4 个卡片接后端 Agent 返回的效果图/清单
