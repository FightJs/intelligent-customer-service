# 直播间智能客服系统（ICS）

面向直播间搭建场景的 AI 客服与交付系统：多轮对话采集客户需求，结合垂类知识库生成定制方案与多媒体交付物，并提供可运营的知识库与后台管理能力。

仓库：https://github.com/FightJs/intelligent-customer-service

---

## 系统概览

系统按三大模块划分：

| 模块 | 定位 | 核心产出 |
|------|------|----------|
| **模块一 · 客服 Agent** | 与用户多轮对话，采集直播间搭建需求 | 结构化 `form_state` 调研表 |
| **模块二 · 方案 Agent** | 结合垂类知识库做定制化分析与交付生成 | 三视图预览图、环绕视频、设备与规划 PDF、最终交付包 |
| **模块三 · 后端与知识库** | CRUD、鉴权、知识入库与检索底座 | 向量库 + 结构化知识关系（graph） |

```text
用户对话
   │
   ▼
┌─────────────────────────────┐
│ 模块一  客服 Agent           │
│ 路由识别 / 纠偏 / 提前预选    │──► form_state（调研表真相源）
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐     ┌──────────────────────────────┐
│ 模块二  方案 Agent           │◄───►│ 模块三  后端 CRUD + 知识库     │
│ plan → 三视图 → 环绕视频 → 包 │     │ Qdrant 向量 + 知识关系网络      │
└──────────────┬──────────────┘     │ 管理端上传 / 种子脚本 / 混合检索 │
               │                    └──────────────────────────────┘
               ▼
     方案 PDF · 三视图 · 预览视频 · 设备清单 · ZIP 交付包
```

端到端数据流：

```text
form_state
    │
    ▼
知识库 hybrid_search（设备 / 方案 / 垂类）
    │
    ▼
F2 plan_document ──► plan.json + 设备与规划 PDF
    │
    ├──────────────► F3 preview_images（正面 / 左侧 / 背面 三视图）
    │                     │
    └──────────────► F4 preview_video（环绕预览视频）
                          │
                          ▼
                     F5 final_package（交叉校验 + 说明 + ZIP）
```

---

## 模块一 · 客服 Agent（需求采集）

多轮对话驱动调研表采集，目标是稳定产出可进入方案管线的 `form_state`。

### 能力

1. **路由识别**  
   - 基于调研表状态机（`agent/flow.py`）识别当前应问字段、条件分支（`visible_if`）与章节可见性。  
   - 支持 `full` / `quick` 两种采集模式；快速模式只强制核心字段，其余可跳过。

2. **路由纠正**  
   - **微意图规则层**（`agent/micro_intent.py`）：不调 LLM，用确定性规则处理「跳过 / 不知道 / 是与否 / 价格区间 / 参考链接」等常见表达，并写回当前题。  
   - **跑题纠偏**：用户问推荐、报价、转人工等非采集内容时，先纠正回采集轨道（「信息收齐后会一起出方案」），避免对话漂移。  
   - **过早完结纠正**：Agent 误报「信息已齐」时，对照 schema 必填项与跳过记录二次校验，防止假完成。

3. **提前预选**  
   - 仅当模型回复实际询问某道选择题时，后端从 schema 生成对应快捷选项（`suggestions`）。  
   - 前端以 Chip 形式预选/一键作答，减少重复打字，同时保证选项与表单真相源一致。

4. **Agent 工具循环**  
   - Anthropic 兼容 tool-use 循环（`agent/loop.py`）：模型可调用工具读写表单字段、处理图片上传、推进调研。  
   - 支持流式输出（`/api/chat/stream`）与会话恢复。

### 相关代码

| 路径 | 职责 |
|------|------|
| `backend/agent/` | 对话循环、工具、微意图、文案与鉴权 |
| `backend/survey/` | 调研表 schema 单一真相源 + codegen |
| `frontend/src/components/ChatPanel/` | 对话 UI、建议 Chip、进度总览 |

---

## 模块二 · 方案 Agent（定制分析与交付）

以 `form_state` 为输入，检索垂类知识库，生成定制化交付物。管线阶段 F2–F5，由 `pipeline/orchestrator.py` 编排（状态机、超时、重试、取消、成本汇总）。

### 2.1 方案文档（F2 `plan_document`）

流程：`Normalize → Decompose → Retrieve → Compose → Validate → Render → Persist`

- 将调研表归一为需求 brief（垂类、面积、预算档、直播类型、产品与目标等）。
- LLM 拆解检索意图，按意图做知识库混合检索（设备参数 / 搭建方案 / 垂类知识）。
- 组合成 `plan.json`（方案唯一真相源）：空间布局、设备清单、场景卡、预算分配。
- 渲染 **设备与规划 PDF**（Jinja2 + WeasyPrint；环境缺 pango/cairo 时降级 Word）。

### 2.2 三视图预览图（F3 `preview_images`）

- 基于 `plan.json` / `scene_card` 生成三机位静帧：  
  **正面 0° / 左侧 120° / 背面 240°**（灯光、动线、布线与景深）。
- 媒体供应商可切换（DashScope / OpenRouter 等），支持 draft / standard / high 质量档。
- 产物落盘至 `ARTIFACT_ROOT/{pipeline_run_id}/images/`，并记录 skill 成本。

### 2.3 环绕预览视频（F4 `preview_video`）

- 以 F3 主视觉帧做图生视频（i2v），输出约 5–15 秒环绕/场景预览 mp4。
- 主模型与 fallback 可配置（如 `wan2.7-i2v` → `kling-v3-video`），支持 flash 降级档。

### 2.4 最终交付包（F5 `final_package`）

- 对 plan / 图 / 视频做交叉校验，生成说明 README 与 manifest。
- 汇总设备清单 Excel、方案 PDF、三视图、预览视频，打包 ZIP 下载。
- 幂等：可重跑；复用已有媒体文件，不重复生图/生视频。

### 交付物一览

| 交付物 | 阶段 | 说明 |
|--------|------|------|
| 设备与规划 PDF（/ Word） | F2 | 布局、设备清单、预算与垂类建议 |
| 三视图预览图 | F3 | 正面 / 左侧 / 背面三机位 |
| 环绕预览视频 | F4 | 主视觉图生视频 |
| 设备清单 Excel + 说明 + ZIP | F5 | 最终交付包 |

### 相关代码

| 路径 | 职责 |
|------|------|
| `backend/pipeline/` | 编排器、plan、打包、校验、模板 |
| `backend/pipeline/skills/` | `preview_images` / `preview_video` |
| `backend/media/` | 生图 / 生视频供应商适配层 |
| `backend/delivery/` | PDF / Word / Excel / Markdown 渲染 |
| `docs/backend-docs/pipeline/` | F1–F5 与 Plan Agent 规格 |

---

## 模块三 · 后端 CRUD 与知识库（向量 + Graph）

### 3.1 业务 CRUD 与鉴权

- **FastAPI** 提供会话、对话、订单、交付物、管线、管理端接口。
- **鉴权**：注册 / 登录 / 游客登录 + JWT；管理员种子账号由环境变量初始化。
- **持久化**：SQLite（`store/db.py`），会话、消息、交付物、管线运行、知识文档元数据；上传文件单独落盘。
- **额度**：按用户与 IP 限制对话与图片调用频率（环境变量可配）。

### 3.2 知识库数据输入

运营侧可维护垂类知识，入口包括：

1. **管理端上传 PDF**（`/api/admin/knowledge/upload`）→ 切块 → embedding → 入库；失败可重试。  
2. **种子 / 导入脚本**（`backend/scripts/seed_knowledge.py`、`ingest_knowledge.py`）→ JSON / 结构化数据批量写入。  
3. **业务主键 upsert**：同业务键覆盖更新；embedding 失败整批回滚，不写半截数据。

三类 Collection：

| Collection | 内容 | 过滤/关联字段示例 |
|------------|------|-------------------|
| `equipment_specs` | 设备参数（灯光/相机/镜头/声卡…） | `category` · `brand` · `price_band` · `room_size` · `industry` |
| `setup_schemes` | 搭建方案 | `industry` · `room_size` · `budget_level` |
| `vertical_knowledge` | 垂类知识（行业话术、场景规范等） | `industry` · `scene` 等 |

### 3.3 向量（Vector）

- **存储**：Qdrant（单容器 `deploy/qdrant.yml`，或本地嵌入式 `QDRANT_URI=./data/qdrant`，开发可用 `memory://`）。
- **表示**：每条知识同时具备  
  - dense 向量（如 DashScope `text-embedding-v3` 1024 维，或本地 mock/CI）  
  - sparse 向量（token 稀疏表示，服务 BM25 风格检索）
- **检索**：`hybrid_search` = dense + sparse 融合（weighted / RRF）+ rerank（local BGE / dashscope / identity）。
- **降级**：Embedding / 向量库不可用时可标记 `degraded`，方案生成走模板兜底，不阻断主流程。

### 3.4 Graph（知识关系网络）

系统在向量检索之外维护**结构化知识关系**，用于按业务条件导航与过滤，而不是无约束全文命中：

- **节点**：设备、搭建方案、垂类知识片段（对应三个 Collection）。
- **关系边**：以 payload 字段表达——`industry`（垂类）、`room_size`（空间）、`budget_level`（预算档）、`category`（设备类别）等。
- **映射层**（`knowledge/mapping.py`）：调研表字段 → 知识库枚举，例如  
  `venue.area` → `room_size`，`budget.total` + `budget.equipment` → `budget_level`。  
  方案 Agent 检索时沿这些关系过滤，形成「需求条件 → 适配设备 / 方案 / 垂类知识」的图式导航。
- **业务主键**：设备 `brand+name+source`、方案 `scheme_name+source`、垂类 `source+chunk_index`，保证节点可覆盖更新、可审计。

> 说明：完整多跳知识图谱引擎（独立 Graph DB）因冷启动成本暂缓；当前以 Qdrant payload 关系 + 映射层实现可检索、可过滤的知识关系网络。

### 相关代码

| 路径 | 职责 |
|------|------|
| `backend/api/app.py` | 全量 HTTP 接口 |
| `backend/store/` | SQLite CRUD、上传 |
| `backend/agent/auth.py` | JWT / 用户 |
| `backend/knowledge/` | schema / ingest / embedding / search / mapping / rerank |
| `backend/scripts/seed_knowledge.py` | 知识种子数据 |
| `deploy/qdrant.yml` | Qdrant 单容器部署 |

---

## 技术栈

| 层 | 选型 |
|----|------|
| 前端 | React 19 · TypeScript · Vite · Tailwind CSS · Vitest · React Router |
| 后端 | Python ≥ 3.12 · FastAPI · SQLite · Anthropic 兼容 LLM SDK |
| 知识库 | Qdrant · dense/sparse hybrid · rerank |
| 媒体生成 | DashScope / OpenRouter 等可插拔适配（生图 / i2v） |
| 交付渲染 | Jinja2 · WeasyPrint · openpyxl · python-docx |
| 部署 | 本地 uv 开发；Qdrant docker compose；前端可接 Cloudflare（wrangler） |

---

## 目录结构

```text
.
├── frontend/                 # React 工作台 + 管理后台 + 营销页
│   └── src/
│       ├── screens/          # Auth / Workbench / Plans / Admin / Marketing
│       ├── components/       # ChatPanel / DeliveryPanel / admin ...
│       ├── api/              # 会话、对话、pipeline 客户端
│       └── data/             # schema 等 codegen 产物
├── backend/
│   ├── agent/                # 模块一：对话循环、微意图、路由与预选
│   ├── survey/               # 调研表 schema（单一真相源）
│   ├── pipeline/             # 模块二：F2–F5 编排与 skills
│   ├── media/                # 生图 / 生视频适配
│   ├── delivery/             # PDF / Word / Excel 渲染
│   ├── knowledge/            # 模块三：向量 + 知识关系 + 入库检索
│   ├── store/                # SQLite CRUD 与上传
│   ├── api/                  # FastAPI 路由
│   ├── scripts/              # seed / ingest / pipeline 试跑脚本
│   └── tests/                # pytest（mock LLM / mock embedding）
├── docs/
│   ├── backend-docs/pipeline/  # F1–F5、Plan Agent 规格
│   └── team-workflow-handbook.md
├── deploy/qdrant.yml         # 知识库单容器
└── .github/                  # CI + PR/Issue 模板
```

---

## 快速开始

### 克隆

```bash
git clone https://github.com/FightJs/intelligent-customer-service.git
cd intelligent-customer-service
```

### 前端

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

| 命令 | 作用 |
|------|------|
| `npm run dev` | 开发服务器 |
| `npm run build` | 类型检查 + 构建 |
| `npm run lint` | oxlint |
| `npm test` | vitest |
| `npm run gen:schema` | 从后端 schema 重新生成前端类型 |

### 后端

需要 Python ≥ 3.12，推荐 [uv](https://docs.astral.sh/uv/)。

```bash
cd backend
cp .env.example .env    # 填写 LLM_API_KEY 等
uv sync --extra dev
uv run uvicorn api.app:app --reload   # http://localhost:8000
```

知识库本地开发（无 Docker）：

```bash
export QDRANT_URI=memory:// EMBEDDING_PROVIDER=mock RERANK_PROVIDER=identity
uv run python scripts/seed_knowledge.py
```

带 Qdrant 的完整知识库：

```bash
docker compose -f ../deploy/qdrant.yml up -d
export QDRANT_URI=http://localhost:6333 \
       EMBEDDING_PROVIDER=dashscope DASHSCOPE_API_KEY=...
uv run --extra qdrant python scripts/seed_knowledge.py
uv run --extra qdrant python scripts/ingest_knowledge.py path/to/docs.json
```

| 命令 | 作用 |
|------|------|
| `uv run pytest` | 后端测试 |
| `uv run python -m survey.export` | 改调研表 schema 后同步 `frontend/schema.json` |

> `.env` 不入库。关键变量见 `backend/.env.example`：`LLM_*`、`JWT_*`、`ADMIN_*`、`QDRANT_*`、`EMBEDDING_*`、`MEDIA_*`、`ARTIFACT_ROOT`。

---

## API 速查

### 认证与会话

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/api/auth/register` | 注册 |
| `POST` | `/api/auth/login` | 登录 |
| `POST` | `/api/auth/guest` | 游客登录 |
| `GET` | `/api/auth/me` | 当前用户 |
| `POST` | `/api/session` | 新建会话（greeting + 初始 form_state） |
| `GET` | `/api/session/{id}` | 恢复会话 |
| `POST` | `/api/session/{id}/skip` | 跳过当前题 |
| `POST` | `/api/chat` | 一轮对话（reply + form_state + suggestions） |
| `POST` | `/api/chat/stream` | 流式对话 |
| `POST` | `/api/generate/{doc_type}` | 传统交付物生成（md / excel / word 等） |

### 管线交付（模块二）

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/api/pipeline` | 启动 F2–F5 管线 |
| `GET` | `/api/pipeline` | 管线列表 |
| `GET` | `/api/pipeline/{id}` | 管线详情（plan / images / video / package 状态） |
| `POST` | `/api/pipeline/{id}/retry` | 重试 |
| `POST` | `/api/pipeline/{id}/cancel` | 取消 |
| `GET` | `/api/pipeline/{id}/package` | 下载 ZIP 交付包 |
| `GET` | `/api/pipeline/{id}/artifacts/{kind}` | 下载单类产物（images/video/pdf…） |

### 管理与知识库（模块三）

| Method | Path | 说明 |
|--------|------|------|
| `GET/POST/PATCH/DELETE` | `/api/admin/users...` | 用户 CRUD |
| `GET/PATCH/DELETE` | `/api/admin/deliveries...` | 交付物管理 |
| `GET` | `/api/admin/knowledge/docs` | 知识文档列表 |
| `POST` | `/api/admin/knowledge/upload` | 上传 PDF 入库 |
| `POST` | `/api/admin/knowledge/docs/{id}/retry` | 入库重试 |

> 接口字段以 `backend/api/app.py` 与前端 `src/api/` 为准。

---

## 团队协作

完整手册：[`docs/team-workflow-handbook.md`](./docs/team-workflow-handbook.md)  
AI 开发约定：[`AGENTS.md`](./AGENTS.md)

```text
main 拉最新 → 切 feat|fix|refactor|chore 分支 → 本地验证
→ Conventional Commit → push → PR
→ CI 全绿 + ≥1 人 review → squash 合并 → 回 main pull
```

要点：

- 所有改动走 PR，不直接 push `main`
- CI 红了不合并（前端 lint/build/test + 后端 pytest）
- Commit：`type: description`（`feat` / `fix` / `refactor` / `docs` / `chore`）
- 一个 commit 做一件事

---

## 常见问题

**CI 上后端测试挂了，本地却是绿的？**  
不要依赖本地 `backend/data/ics.db`。`tests/conftest.py` 会自动 `init_db()`。

**改了调研表字段，前端没更新？**  
真相源是 `backend/survey/schema_def.py`。执行 `uv run python -m survey.export`，必要时前端再跑 `npm run gen:schema`。

**知识库检索无结果 / 方案退化？**  
确认 `QDRANT_URI`、embedding 与 seed 脚本是否就绪。检索全空时 F2 可能标记 `knowledge_degraded` 并走模板方案。

**`.env` 从哪来？**  
从 `backend/.env.example`（及 `frontend/.env.example`）复制。密钥文件不入库。

**管道产物在本地哪里？**  
默认 `backend/data/artifacts/{pipeline_run_id}/`，可用 `ARTIFACT_ROOT` 改路径。

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [`docs/backend-docs/spec-studio-delivery-pipeline.md`](./docs/backend-docs/spec-studio-delivery-pipeline.md) | 交付管线总览 |
| [`docs/backend-docs/pipeline/README.md`](./docs/backend-docs/pipeline/README.md) | F1–F5 / Plan Agent 规格索引 |
| [`docs/backend-docs/pipeline/spec-f1-vector-knowledge-base.md`](./docs/backend-docs/pipeline/spec-f1-vector-knowledge-base.md) | 向量知识库 |
| [`docs/backend-docs/pipeline/spec-plan-agent.md`](./docs/backend-docs/pipeline/spec-plan-agent.md) | Plan Agent 与交付门禁 |
| [`DESIGN.md`](./DESIGN.md) | 前端「青瓷运营台」设计规范 |
| [`docs/team-workflow-handbook.md`](./docs/team-workflow-handbook.md) | 团队开发操作手册 |
