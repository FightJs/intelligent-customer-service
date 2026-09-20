---
feature: plan-delivery-pages
status: delivered
updated: 2026-09-10
branch: main
commits: uncommitted-working-tree
---

# 智能交付页面（我的方案 + 知识库）

## Report

**What was built** — 用户端独立路由 `/plans`「我的方案」：左侧历史方案列表（含状态与更新时间），右侧详情含管线四 skill 进度、三机位 360 预览图廊（灯箱）、预览视频区、方案 PDF 清单与完整交付包下载；Guest 可查看列表，不展示按 skill 重试等生成入口。管理端 AdminHeader 新增第三 Tab「知识库」：统计卡、拖拽/点击上传 PDF（按设备参数/搭建方案/垂类知识分类）、状态与分类筛选、文档表、详情抽屉（Esc 关闭、重新向量化、删除）；「向量化中」使用 Warning 徽标。仓库根目录 `index.html` + `styles.css` + `app.js` 为可独立打开的设计原型，令牌对齐 `DESIGN.md`。顺带补齐 Tailwind `outline`/`recess` 色值映射与 Badge 的 warning/danger 变体。

**Verification** — `npm run lint` PASS（0 errors，6 个既有 warning）；`npm run build` PASS（tsc + vite）；`npm test`（Node 22）170/170 PASS。独立 review 后已修复 Guest 入口语义、embedding Warning 徽标、失败 skill 重试入口。

**Journey log** — 后端管线契约见 `docs/backend-docs/spec-studio-delivery-pipeline.md`；900px 断点不可用 Tailwind `lg`（1024）；`border-outline`/`bg-recess` 此前未映射进 theme；TopBar 引入 Link 后测试需包 MemoryRouter；根目录原型 `innerHTML` 仅作设计稿，勿直接当生产代码。

## [S1] Problem

后端智能交付管线（F1–F5，见 `docs/backend-docs/spec-studio-delivery-pipeline.md`）约定订单后异步产出 360 预览图、预览视频、方案 PDF。前端目前只有工作台右槽的静态结构化清单，用户无法查看多机位预览与视频；后台也没有运营上传 PDF 入向量库的界面。

## [S2] Design

### 视觉约束

严格沿用 `DESIGN.md` 青瓷运营台令牌与现有组件范式（AdminHeader tabs、DataTable、抽屉、StatCard、TopBar）。不引入新色彩语义、不改工作台布局。

### 用户端：`/plans`「我的方案」

- **路由**：`Protected` 下新路由；TopBar / 工作台入口跳转；Guest 可见列表但不展示生成入口。
- **布局**：左右双栏。左 240–280px 方案列表；右为主详情。`<900px` 改单栏（列表 → 详情返回）。
- **列表项**：标题、垂类/面积摘要、状态徽标（生成中 / 可下载 / 失败）、更新时间。
- **详情区模块**（自上而下）：
  1. **状态条**：pipeline 状态 + 各 skill 进度点（方案 PDF / 预览图 / 预览视频 / 汇总包）+ 费用（若有）
  2. **360° 预览图廊**：≥3 张多机位图，标注 0° / 120° / 240°；点击开灯箱放大；partial 时缺失位标 Warning
  3. **预览视频**：`<video controls>`，时长/分辨率元信息；failed 显示错误与重试提示
  4. **方案清单 PDF**：章节摘要（设备清单 / 三档套餐 / 搭建规划）+ 下载按钮；在线预览可后续接 iframe
  5. **完整交付包**：下载 zip / manifest 摘要（文件数、hash 摘要可后置）
- **空态**：未提交订单 → 引导回工作台完成调研；生成中 → 进度骨架 + 可离开提示；失败 → Danger 文案 + 按 skill 重试入口（有权限时）
- **数据契约（mock 对齐后端）**：
  ```ts
  type PlanStatus = 'pending' | 'running' | 'ready' | 'partial' | 'failed'
  type PlanListItem = { id: string; title: string; industry: string; roomSize: string; status: PlanStatus; updatedAt: string }
  type PlanDetail = {
    id: string
    title: string
    status: PlanStatus
    skills: { plan: SkillState; images: SkillState; video: SkillState; package: SkillState }
    images: { angle: 'front' | 'left' | 'rear'; url: string; label: string }[]
    video?: { url: string; durationSec: number; resolution: string }
    pdf?: { title: string; sections: string[]; downloadUrl: string }
    package?: { downloadUrl: string; fileCount: number }
  }
  type SkillState = 'pending' | 'running' | 'succeeded' | 'partial' | 'failed'
  ```

### 管理端：第三 Tab「知识库」

- **入口**：`AdminHeader` 增加 `knowledge` tab，与交付物/用户并列；图标 `Database`。
- **布局**（对齐 DeliveriesTab）：
  1. StatCard 行：文档总数 / 就绪 / 向量化中 / 失败
  2. 上传区：拖拽 + 点击选择 PDF；分类选择（设备参数 / 搭建方案 / 垂类知识）；上传后进入「待向量化/向量化中」
  3. 筛选栏：SearchInput + 状态 + 分类
  4. DataTable：文件名、分类、状态徽标、chunks、更新时间、操作（详情 / 删除 Danger）
  5. 详情抽屉：元数据、预览摘要、重新向量化、删除
- **状态语义**：就绪=Done；向量化中=Warning；失败=Danger；待处理=Muted。
- **数据契约（mock）**：
  ```ts
  type KnowledgeStatus = 'pending' | 'embedding' | 'ready' | 'failed'
  type KnowledgeCategory = 'equipment' | 'scheme' | 'vertical'
  type KnowledgeDoc = {
    id: string
    filename: string
    category: KnowledgeCategory
    status: KnowledgeStatus
    chunks: number
    updatedAt: string
    note?: string
  }
  ```

### 交互与状态

- Hover / Focus-visible 沿用现有 outline Accent；按钮 6px 圆角。
- 上传：拖入高亮 Active surface + Accent 边框；失败 Toast/Danger。
- 图廊灯箱：Esc 关闭，左右键切图；`prefers-reduced-motion` 下无位移动画。
- 所有异步区域设计 loading / empty / error。

### 原型

仓库根目录 `index.html` + `styles.css` + `app.js` 为可独立打开的设计原型，复刻上述两页视觉与交互，使用同一套 CSS 变量，便于评审后同步 React。

## [S3] Out of Scope

- 不实现 F1–F5 后端管线、Milvus、DashScope 调用（见既有 backend spec）
- 不改工作台对话与订单确认流程
- 不做真实 PDF iframe 渲染 / 视频转码
- 不做知识库文档在线编辑器、审核工作流（后期）
- 不做真 equirectangular 360 全景查看器

## Tasks

- [x] T1: 撰写并冻结本页面 feature 文档 — acceptance: 本文档契约与页面清单完整 (covers: S2)
- [x] T2: 产出根目录 HTML 设计原型（我的方案 + 知识库）— acceptance: 浏览器打开 index.html 可切换两页，令牌与 DESIGN.md 一致，含 loading/empty/error 态 (covers: S2)
- [x] T3: 实现 React `/plans` 页面与路由/入口 — acceptance: 登录用户可从工作台进入我的方案，详情含图廊/视频/PDF/包下载区，Guest 降级正确 (covers: S2; depends: T1)
- [x] T4: 实现 React 后台「知识库」第三 Tab — acceptance: AdminHeader 出现知识库，上传/筛选/表格/详情抽屉可交互，状态语义符合 S2 (covers: S2; depends: T1)
- [x] T5: 前端 lint/build/test 通过 — acceptance: `npm run lint`、`npm run build`、`npm test` 全绿 (covers: S2; depends: T3, T4)
