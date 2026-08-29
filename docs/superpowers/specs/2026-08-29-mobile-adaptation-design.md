# 手机端适配设计：按住说话 + 响应式布局

日期：2026-08-29
分支：`feat/mobile-adaptation`
范围：仅前端（`frontend/`），后端不动

## 背景与目标

当前工作台面向桌面设计：

- 语音输入是**点击切换**（点一下开始、再点一下停止），手机上不符合用户习惯
- 布局只有 ≤900px 一个断点（隐藏右栏），**没有手机端（≤640px）布局**
- 中央卡片可拖拽/缩放（`useDraggable` / `useResizable`），触屏上会干扰滚动和点击

目标：

1. 触屏设备语音输入改为**按住说话、松开停止**；桌面端保持现有点击切换
2. 手机端（≤640px）UI 可用：单列布局、卡片铺满、禁用拖拽缩放、安全区适配

非目标（YAGNI）：

- 上滑取消语音（松开即保留识别文本）
- 右栏交付槽的手机端入口（沿用现有 ≤900px 的 `display: none`）
- 营销页（marketing.css 已有自己的响应式断点，不在本次范围）

## 方案

### 1. 触屏判定：`useCoarsePointer` hook

新文件 `frontend/src/hooks/useCoarsePointer.ts`：

- `matchMedia('(pointer: coarse)')` 判定触屏设备
- 监听 `change` 事件，返回响应式 boolean
- SSR/测试环境下默认 `false`（无 `window.matchMedia` 时）

桌面端（fine pointer）行为完全不变。

### 2. 按住说话（`ChatPanel.tsx`）

复用现有 `useSpeechRecognition` hook（`startListening` / `stopListening` 已满足需求，hook 零改动）：

- 触屏端麦克风按钮：
  - `onPointerDown` → 清空 speechError、记录 speechBase、`startListening()`
  - `onPointerUp` / `onPointerCancel` → `stopListening()`，输入框聚焦
  - 用 ref 标记一次 hold 周期，抑制 hold 结束后残留的 `click` 事件误触 toggle
  - `onPointerLeave` 不停止（手指可能轻微滑出按钮，避免意外中断）
- 按钮文案/title/aria-label 触屏端改为「按住说话」/「松开停止」
- 按住期间视觉反馈复用现有 `is-listening` 样式与声波动画
- `touch-action: none` 防止按住时触发页面滚动/手势冲突
- 桌面端保持 `onClick={toggleSpeechInput}` 不变

边界处理：

- 按住不足一拍就松开（识别尚未 `onstart`）：`stopListening` 已有 abort 兜底，不报错
- 按住期间识别出错（权限/网络）：走现有 `onError` → `speechError` 提示
- 组件卸载时 hook 的 cleanup 已 abort，无泄漏

### 3. 手机端布局（`index.css` 新增 ≤640px 断点）

```css
@media (max-width: 640px) {
  /* .workbench-stage: 单列，中央卡片铺满，padding 缩小 */
  /* .workbench-pet-zone: 隐藏（手机屏留给对话） */
  /* .workbench-slots: 沿用 ≤900px 的 display: none */
  /* .center-card: 撑满容器，关闭拖拽/缩放的视觉手柄 */
  /* TopBar: 紧凑间距、缩小按钮 */
  /* 聊天输入区: padding-bottom 加 env(safe-area-inset-bottom) */
  /* textarea/输入框字号 ≥16px，防 iOS 聚焦自动缩放 */
}
```

### 4. CenterCard 禁用拖拽/缩放

- `CenterCard` 内部使用 `useDraggable` / `useResizable`
- 引入 `useCoarsePointer()`：触屏时跳过指针事件绑定，卡片回到静态铺满定位
- `centerBounds.ts` 的边界计算在禁用时不执行，无需改动

### 5. viewport

检查 `frontend/index.html` 的 `<meta name="viewport">`，确保为
`width=device-width, initial-scale=1, viewport-fit=cover`（`viewport-fit=cover` 是安全区生效的前提）。

## 数据流

无状态流变化。语音识别的 transcript 仍走现有 `onTranscript` → draft 拼接逻辑（`speechBaseRef` + 增量识别文本）。

## 测试

- `useSpeechRecognition` 零改动，已有测试不动
- 新增 `useCoarsePointer.test.ts`：mock `matchMedia`，验证初始值与 change 监听
- `ChatPanel.test.tsx` 补充：
  - coarse pointer 下 `pointerdown` 启动识别、`pointerup` 停止
  - hold 后残留的 `click` 不触发 toggle
  - 非 coarse 下维持 click 切换行为
- 现有测试全部保持通过

## 涉及文件

| 文件 | 改动 |
|---|---|
| `frontend/src/hooks/useCoarsePointer.ts` | 新增 |
| `frontend/src/components/ChatPanel/ChatPanel.tsx` | 按住说话交互 |
| `frontend/src/index.css` | ≤640px 断点、touch-action、安全区 |
| `frontend/src/components/CenterCard/CenterCard.tsx` | 触屏禁用拖拽/缩放 |
| `frontend/index.html` | viewport meta（如需） |
| `frontend/tests/useCoarsePointer.test.ts` | 新增 |
| `frontend/tests/ChatPanel.test.tsx` | 补充 hold 交互用例 |
