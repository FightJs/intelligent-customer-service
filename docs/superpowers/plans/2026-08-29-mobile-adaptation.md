# 手机端适配实现计划：按住说话 + 响应式布局

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 触屏设备语音输入改为按住说话/松开停止，并补齐手机端（≤640px）工作台布局适配。

**Architecture:** 新增 `useCoarsePointer` hook（`matchMedia('(pointer: coarse)')`）作为触屏判定唯一入口；ChatPanel 在触屏下用 pointer 事件驱动现有 `useSpeechRecognition` 的 start/stop（hook 零改动）；CenterCard 在触屏下禁用拖拽/缩放并铺满容器；CSS 侧新增 ≤640px 断点与安全区适配。

**Tech Stack:** React 19 + TypeScript + Vite + Tailwind 工具类 + 手写 `index.css`；测试 Vitest + @testing-library/react（jsdom）。

**Spec:** `docs/superpowers/specs/2026-08-29-mobile-adaptation-design.md`

**工作目录：** `G:/worktree/intelligent-customer-service`（分支 `feat/mobile-adaptation`，已创建）

**关键背景（执行者必读）：**

- jsdom **没有** `window.matchMedia`，所以 hook 必须兜底 `typeof window.matchMedia !== 'function'` 返回 `false`——这样现有全部测试在桌面行为下不受影响。
- 测试命令在 `frontend/` 目录下执行：`npm test`（vitest run）、`npm run lint`（oxlint）、`npm run build`。
- 现有语音测试在 `frontend/tests/ChatPanel.test.tsx` 的 `describe('ChatPanel 语音输入')`，采用「点击开始/点击停止」语义，desktop 行为必须保持不变。
- `ChatPanel.tsx` 中相关现状：
  - `toggleSpeechInput`（约 405-421 行）：click 切换开始/停止。
  - 麦克风按钮 JSX（约 784-834 行）：`onClick={toggleSpeechInput}`，class `voice-input-button`，aria-label 在「开始语音输入」/「停止语音输入」间切换。
  - 底部状态文案（约 877-884 行）：`正在收音，再次点击结束`。
- `CenterCard.tsx` 现状：`useDraggable` / `useResizable` 提供 `onDragStart` / `onResizeStart`，拖拽柄 `[data-card-handle]`，缩放柄 `[data-resize-handle]`。

---

### Task 1: `useCoarsePointer` hook

**Files:**
- Create: `frontend/src/hooks/useCoarsePointer.ts`
- Test: `frontend/tests/useCoarsePointer.test.ts`

- [ ] **Step 1: 写失败测试**

创建 `frontend/tests/useCoarsePointer.test.ts`：

```ts
import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useCoarsePointer } from '../src/hooks/useCoarsePointer'

type ChangeListener = () => void

interface MockMediaQueryList {
  matches: boolean
  addEventListener: (type: string, listener: ChangeListener) => void
  removeEventListener: (type: string, listener: ChangeListener) => void
}

function mockMatchMedia(initialMatches: boolean) {
  const listeners = new Set<ChangeListener>()
  const media: MockMediaQueryList = {
    matches: initialMatches,
    addEventListener: (_type, listener) => { listeners.add(listener) },
    removeEventListener: (_type, listener) => { listeners.delete(listener) },
  }
  window.matchMedia = vi.fn(
    () => media,
  ) as unknown as typeof window.matchMedia

  return {
    setMatches(next: boolean) {
      media.matches = next
      for (const listener of [...listeners]) {
        listener()
      }
    },
  }
}

describe('useCoarsePointer', () => {
  afterEach(() => {
    delete (window as Partial<Window>).matchMedia
  })

  it('无 matchMedia 的环境（jsdom 默认）返回 false', () => {
    delete (window as Partial<Window>).matchMedia

    const { result } = renderHook(() => useCoarsePointer())

    expect(result.current).toBe(false)
  })

  it('触屏设备返回 true，指针类型变化时同步更新', () => {
    const media = mockMatchMedia(true)

    const { result } = renderHook(() => useCoarsePointer())
    expect(result.current).toBe(true)

    act(() => media.setMatches(false))
    expect(result.current).toBe(false)
  })

  it('卸载后移除 change 监听', () => {
    const media = mockMatchMedia(false)
    const removeSpy = vi.spyOn(
      window.matchMedia('(pointer: coarse)'),
      'removeEventListener',
    )

    const { unmount } = renderHook(() => useCoarsePointer())
    unmount()

    expect(removeSpy).toHaveBeenCalled()
    expect(media.matches).toBe(false)
  })
})
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /g/worktree/intelligent-customer-service/frontend && npx vitest run tests/useCoarsePointer.test.ts
```

预期：FAIL，报错 `Cannot find module '../src/hooks/useCoarsePointer'`。

- [ ] **Step 3: 实现 hook**

创建 `frontend/src/hooks/useCoarsePointer.ts`：

```ts
import { useSyncExternalStore } from 'react'

const COARSE_POINTER_QUERY = '(pointer: coarse)'

function canMatchMedia(): boolean {
  return (
    typeof window !== 'undefined'
    && typeof window.matchMedia === 'function'
  )
}

function subscribe(onChange: () => void): () => void {
  if (!canMatchMedia()) {
    return () => {}
  }

  const media = window.matchMedia(COARSE_POINTER_QUERY)
  media.addEventListener('change', onChange)
  return () => {
    media.removeEventListener('change', onChange)
  }
}

function getSnapshot(): boolean {
  if (!canMatchMedia()) {
    return false
  }
  return window.matchMedia(COARSE_POINTER_QUERY).matches
}

/**
 * 是否为触屏（粗指针）设备。桌面端返回 false。
 * jsdom 等无 matchMedia 的环境安全兜底为 false。
 */
export function useCoarsePointer(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, () => false)
}
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd /g/worktree/intelligent-customer-service/frontend && npx vitest run tests/useCoarsePointer.test.ts
```

预期：3 个用例全部 PASS。

- [ ] **Step 5: 提交**

```bash
cd /g/worktree/intelligent-customer-service && git add frontend/src/hooks/useCoarsePointer.ts frontend/tests/useCoarsePointer.test.ts && git commit -m "feat: 新增 useCoarsePointer 触屏判定 hook"
```

---

### Task 2: ChatPanel 按住说话（触屏）

**Files:**
- Modify: `frontend/src/components/ChatPanel/ChatPanel.tsx`
- Modify: `frontend/tests/ChatPanel.test.tsx`

- [ ] **Step 1: 写失败测试**

在 `frontend/tests/ChatPanel.test.tsx` 顶部 import 中加入 `afterEach`：

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
```

在文件末尾追加新的 describe（注意 `MockSpeechRecognition` 类在本文件中是各测试内局部定义的，这里完整重复一份，不要跨测试引用）：

```tsx
describe('ChatPanel 按住说话（触屏）', () => {
  function mockCoarsePointer() {
    window.matchMedia = vi.fn((query: string) => ({
      matches: query === '(pointer: coarse)',
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })) as unknown as typeof window.matchMedia
  }

  afterEach(() => {
    delete (window as Partial<Window>).matchMedia
  })

  it('按住开始识别、松开停止，残留 click 不重复触发', async () => {
    mockCoarsePointer()

    const recognitions: MockSpeechRecognition[] = []
    class MockSpeechRecognition {
      lang = ''
      continuous = false
      interimResults = false
      maxAlternatives = 1
      onresult: ((event: unknown) => void) | null = null
      onerror: ((event: { error: string }) => void) | null = null
      onend: (() => void) | null = null
      onstart: (() => void) | null = null
      start = vi.fn()
      stop = vi.fn()
      abort = vi.fn()
      constructor() { recognitions.push(this) }
    }
    const speechWindow = window as typeof window & {
      webkitSpeechRecognition?: new () => MockSpeechRecognition
    }
    speechWindow.webkitSpeechRecognition = MockSpeechRecognition

    renderPanel()
    await screen.findByPlaceholderText('输入您的回答…')

    const button = screen.getByRole('button', { name: '按住说话' })

    fireEvent.pointerDown(button)
    expect(recognitions).toHaveLength(1)
    expect(recognitions[0].start).toHaveBeenCalledTimes(1)

    act(() => recognitions[0].onstart?.())
    expect(screen.getByTestId('voice-listening-indicator')).toBeInTheDocument()

    fireEvent.pointerUp(button)
    expect(recognitions[0].stop).toHaveBeenCalledTimes(1)

    // 触屏按住后浏览器会补发 click，绝不能当成 toggle 重新开始
    fireEvent.click(button)
    expect(recognitions).toHaveLength(1)

    delete speechWindow.webkitSpeechRecognition
  })

  it('pointercancel 同样停止识别', async () => {
    mockCoarsePointer()

    const recognitions: MockSpeechRecognition[] = []
    class MockSpeechRecognition {
      lang = ''
      continuous = false
      interimResults = false
      maxAlternatives = 1
      onresult: ((event: unknown) => void) | null = null
      onerror: ((event: { error: string }) => void) | null = null
      onend: (() => void) | null = null
      onstart: (() => void) | null = null
      start = vi.fn()
      stop = vi.fn()
      abort = vi.fn()
      constructor() { recognitions.push(this) }
    }
    const speechWindow = window as typeof window & {
      webkitSpeechRecognition?: new () => MockSpeechRecognition
    }
    speechWindow.webkitSpeechRecognition = MockSpeechRecognition

    renderPanel()
    await screen.findByPlaceholderText('输入您的回答…')

    const button = screen.getByRole('button', { name: '按住说话' })
    fireEvent.pointerDown(button)
    act(() => recognitions[0].onstart?.())
    fireEvent.pointerCancel(button)
    expect(recognitions[0].stop).toHaveBeenCalledTimes(1)

    delete speechWindow.webkitSpeechRecognition
  })
})
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /g/worktree/intelligent-customer-service/frontend && npx vitest run tests/ChatPanel.test.tsx
```

预期：新 describe 的 2 个用例 FAIL（找不到名为「按住说话」的按钮）。

- [ ] **Step 3: 实现按住说话**

修改 `frontend/src/components/ChatPanel/ChatPanel.tsx`：

**3a.** 顶部 import 区加入：

```ts
import { useCoarsePointer } from '../../hooks/useCoarsePointer'
```

（路径以该文件现有相对 import 为准——ChatPanel 位于 `src/components/ChatPanel/`，hook 位于 `src/hooks/`。）

**3b.** 将现有 `toggleSpeechInput`（约 405-421 行）重构为拆分 + 兼容 hold 的一组回调，整体替换为：

```tsx
  const coarsePointer = useCoarsePointer()
  const voiceHoldRef = useRef(false)

  const beginSpeechInput = useCallback(() => {
    setSpeechError('')
    speechBaseRef.current = draft.trimEnd()
    startListening()
  }, [draft, startListening])

  const endSpeechInput = useCallback(() => {
    stopListening()
    draftRef.current?.focus()
  }, [stopListening])

  const toggleSpeechInput = useCallback(() => {
    if (listening) {
      endSpeechInput()
      return
    }
    beginSpeechInput()
  }, [listening, beginSpeechInput, endSpeechInput])

  // 触屏端按住说话：按下开始、松开/取消停止；click 全部忽略，
  // 避免按住结束后浏览器补发的 click 误触 toggle。
  const handleVoicePointerDown = useCallback(() => {
    if (!coarsePointer || listening) return
    voiceHoldRef.current = true
    beginSpeechInput()
  }, [coarsePointer, listening, beginSpeechInput])

  const handleVoicePointerEnd = useCallback(() => {
    if (!voiceHoldRef.current) return
    voiceHoldRef.current = false
    endSpeechInput()
  }, [endSpeechInput])

  const handleVoiceClick = useCallback(() => {
    if (coarsePointer) return
    toggleSpeechInput()
  }, [coarsePointer, toggleSpeechInput])
```

（若 `useRef` 尚未在该文件 import，则加入。`setSpeechError`、`speechBaseRef`、`draftRef` 均为现有变量，保持原名。）

**3c.** 麦克风按钮 JSX（约 784-834 行）：将 `onClick={toggleSpeechInput}` 替换为：

```tsx
              onClick={handleVoiceClick}
              onPointerDown={handleVoicePointerDown}
              onPointerUp={handleVoicePointerEnd}
              onPointerCancel={handleVoicePointerEnd}
```

aria-label 与 title 改为（`speechSupported` 为现有变量）：

```tsx
              aria-label={
                coarsePointer
                  ? (listening ? '松开停止' : '按住说话')
                  : (listening ? '停止语音输入' : '开始语音输入')
              }
              aria-pressed={listening}
              title={
                !speechSupported
                  ? '当前浏览器不支持语音输入'
                  : coarsePointer
                    ? (listening ? '松开停止' : '按住说话')
                    : (listening ? '停止语音输入' : '开始语音输入')
              }
```

**3d.** 输入框 placeholder（约 699-705 行）的 listening 分支改为：

```tsx
                  listening
                    ? coarsePointer
                      ? '正在聆听，松开结束…'
                      : '正在聆听，请再次点击麦克风结束…'
```

**3e.** 底部状态文案（约 877-884 行）改为：

```tsx
              {coarsePointer ? '正在收音，松开结束' : '正在收音，再次点击结束'}
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd /g/worktree/intelligent-customer-service/frontend && npx vitest run tests/ChatPanel.test.tsx tests/useSpeechRecognition.test.tsx
```

预期：全部 PASS（含原有「点击开始/停止」桌面用例——jsdom 无 matchMedia，走 desktop 分支）。

- [ ] **Step 5: 提交**

```bash
cd /g/worktree/intelligent-customer-service && git add frontend/src/components/ChatPanel/ChatPanel.tsx frontend/tests/ChatPanel.test.tsx && git commit -m "feat: 触屏端语音输入改为按住说话"
```

---

### Task 3: CenterCard 触屏静态化

**Files:**
- Modify: `frontend/src/components/CenterCard/CenterCard.tsx`
- Modify: `frontend/tests/CenterCard.test.tsx`

- [ ] **Step 1: 写失败测试**

在 `frontend/tests/CenterCard.test.tsx` 顶部 import 加入 `afterEach` 与 `vi`：

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
```

在 describe 内追加用例：

```tsx
  describe('触屏设备', () => {
    function mockCoarsePointer() {
      window.matchMedia = vi.fn((query: string) => ({
        matches: query === '(pointer: coarse)',
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })) as unknown as typeof window.matchMedia
    }

    afterEach(() => {
      delete (window as Partial<Window>).matchMedia
    })

    it('禁用拖拽缩放并铺满容器', () => {
      mockCoarsePointer()

      const { container } = render(<CenterCard />)
      const card = container.querySelector('[data-center-card]') as HTMLElement

      expect(container.querySelector('[data-resize-handle]')).toBeNull()
      expect(card.style.width).toBe('100%')
      expect(card.style.height).toBe('100%')
      expect(card.style.transform).toBe('')
    })
  })
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /g/worktree/intelligent-customer-service/frontend && npx vitest run tests/CenterCard.test.tsx
```

预期：新用例 FAIL（resize handle 仍存在、width 为 930px）。

- [ ] **Step 3: 实现触屏静态化**

修改 `frontend/src/components/CenterCard/CenterCard.tsx`：

**3a.** import 加入：

```ts
import { useCoarsePointer } from '../../hooks/useCoarsePointer'
```

**3b.** 组件内（`useZStack` 之后）加入：

```tsx
  const coarsePointer = useCoarsePointer()
```

**3c.** 外层 div 的 style 改为条件式：

```tsx
      style={coarsePointer
        ? { inset: 0, width: '100%', height: '100%', zIndex: z }
        : {
            inset: 0,
            width: size.w,
            height: size.h,
            transform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
            zIndex: z,
            opacity: dragging || resizing ? 0.9 : 1,
          }}
```

**3d.** 拖拽柄（`data-card-handle` div）：`onMouseDown={onDragStart}` 改为：

```tsx
        onMouseDown={coarsePointer ? undefined : onDragStart}
```

className 中 `cursor-move` 改为条件：`${coarsePointer ? 'cursor-default' : 'cursor-move'}`（模板字符串拼接，保持其余类名不变）。

**3e.** 缩放柄改为仅非触屏渲染：

```tsx
        {!coarsePointer && (
          <div
            data-resize-handle
            onMouseDown={onResizeStart}
            className="center-card-resize-handle"
          />
        )}
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd /g/worktree/intelligent-customer-service/frontend && npx vitest run tests/CenterCard.test.tsx
```

预期：全部 PASS（原有用例走 jsdom 默认无 matchMedia → desktop 分支）。

- [ ] **Step 5: 提交**

```bash
cd /g/worktree/intelligent-customer-service && git add frontend/src/components/CenterCard/CenterCard.tsx frontend/tests/CenterCard.test.tsx && git commit -m "feat: 触屏设备禁用中央卡片拖拽缩放"
```

---

### Task 4: 手机端 CSS 与 viewport

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/components/TopBar.tsx`

纯 CSS/属性改动，无单测；验证靠 build + 人工目测。

- [ ] **Step 1: viewport 加 viewport-fit=cover**

`frontend/index.html` 第 6 行改为：

```html
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
```

- [ ] **Step 2: 语音按钮防触屏手势冲突**

`frontend/src/index.css` 现有 `.voice-input-button` 规则（约 564 行）内追加三个属性：

```css
.voice-input-button {
  touch-action: none;
  -webkit-user-select: none;
  user-select: none;
  /* …原有属性保持不变… */
}
```

- [ ] **Step 3: 新增 ≤640px 断点**

在 `frontend/src/index.css` 现有 `@media (max-width: 900px)` 块（约 1015-1018 行）之后追加：

```css
@media (max-width: 640px) {
  .workbench-stage {
    grid-template-columns: minmax(0, 1fr);
    gap: 8px;
    padding: 8px 8px calc(8px + env(safe-area-inset-bottom));
  }

  .workbench-pet-zone,
  .workbench-slots {
    display: none;
  }

  /* 防止 iOS 聚焦输入框时自动放大页面 */
  .chat-input {
    font-size: 16px;
  }
}
```

- [ ] **Step 4: TopBar 紧凑化（Tailwind 响应式类）**

`frontend/src/components/TopBar.tsx` 第 41 行 header 的类名由：

```tsx
      <header className="top-bar h-12 flex items-center px-5 gap-3.5 bg-transparent">
```

改为：

```tsx
      <header className="top-bar h-11 flex items-center px-3 gap-2 bg-transparent sm:h-12 sm:px-5 sm:gap-3.5">
```

- [ ] **Step 5: 构建验证**

```bash
cd /g/worktree/intelligent-customer-service/frontend && npm run build
```

预期：tsc + vite build 成功，无类型错误。

- [ ] **Step 6: 提交**

```bash
cd /g/worktree/intelligent-customer-service && git add frontend/index.html frontend/src/index.css frontend/src/components/TopBar.tsx && git commit -m "feat: 手机端布局断点与安全区适配"
```

---

### Task 5: 全量回归

**Files:** 无改动，仅验证。

- [ ] **Step 1: 全量测试**

```bash
cd /g/worktree/intelligent-customer-service/frontend && npm test
```

预期：所有测试文件 PASS。

- [ ] **Step 2: lint**

```bash
cd /g/worktree/intelligent-customer-service/frontend && npm run lint
```

预期：无 error。

- [ ] **Step 3: 生产构建**

```bash
cd /g/worktree/intelligent-customer-service/frontend && npm run build
```

预期：构建成功。

- [ ] **Step 4: 人工冒烟（可选但推荐）**

```bash
cd /g/worktree/intelligent-customer-service/frontend && npm run dev
```

Chrome DevTools 设备模拟选 iPhone，确认：
1. 工作台单列、中央卡片铺满、不可拖拽
2. 麦克风按钮提示「按住说话」，按住出声波、松开停止
3. 桌面窗口（≥900px）行为与之前完全一致
