# 直播间智能客服系统

AI 对话式客服系统，通过多轮对话采集直播间搭建需求，自动生成交付物文档（Markdown / Excel / Word）。

- **前端** — React + TypeScript 对话式 UI，展示采集进度与交付物
- **后端** — FastAPI + LLM Agent，驱动对话脚本，持久化会话，生成交付物

---

## 新协作者上手

### 1. 克隆并进入项目

```bash
git clone https://github.com/HXS482/intelligent-customer-service.git
cd intelligent-customer-service
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev        # 启动开发服务器 http://localhost:5173
```

| 命令 | 作用 |
|---|---|
| `npm run dev` | 开发服务器 |
| `npm run build` | 类型检查 + 构建 |
| `npm run lint` | oxlint 静态检查 |
| `npm test` | vitest 单元测试 |

> 技术栈：React 19 · TypeScript · Vite · Tailwind CSS · Vitest

### 3. 后端

需要 Python ≥ 3.12，推荐用 [uv](https://docs.astral.sh/uv/)（CI 也用它）。

```bash
cd backend
cp .env.example .env       # 填入你的 LLM_API_KEY
uv sync --extra dev        # 安装依赖
uv run uvicorn api.app:app --reload   # 启动 http://localhost:8000
```

| 命令 | 作用 |
|---|---|
| `uv sync --extra dev` | 安装依赖（含测试） |
| `uv run pytest` | 跑测试 |
| `uv run python -m survey.export` | 改了表单 schema 后，重新生成 `frontend/schema.json` |

> `.env` 不入库（已 gitignore）。`LLM_API_KEY` 必填，后端通过 Anthropic SDK 调 DeepSeek 的 `/anthropic` 端点。

### 4. API 端点速查

| Method | Path | 说明 |
|---|---|---|
| `POST` | `/api/session` | 新建会话，返回 greeting + 初始 form_state |
| `GET` | `/api/session/{id}` | 恢复会话状态（跨会话续接） |
| `POST` | `/api/chat` | 一轮对话，返回 reply + form_state 更新 |
| `POST` | `/api/generate/{doc_type}` | 生成交付物（markdown / excel / word），流式下载 |

### 5. 目录结构

```
.
├── frontend/          # React UI
│   └── src/
│       ├── components/  # ChatPanel / MessageBubble / QuickChips ...
│       ├── data/        # scriptedFlow（本地脚本，可替换为真实后端）
│       └── state/       # 表单状态管理
├── backend/           # FastAPI + LLM Agent
│   ├── agent/          # LLM 调用 + tool-use 循环 + 表单状态机
│   ├── api/            # FastAPI 路由（app.py）
│   ├── survey/         # 表单 schema（单一真相源）+ codegen
│   ├── store/          # SQLite 持久化（sessions / messages）
│   ├── delivery/       # 交付物生成（md / xlsx / docx）
│   └── tests/
└── .github/           # CI workflow + PR/Issue 模板
```

---

## 团队协作流程

> 📖 **新成员必读**:完整操作手册见 [`docs/team-workflow-handbook.md`](./docs/team-workflow-handbook.md)(从 clone 到合并的全流程)。AI 开发约定见 [`AGENTS.md`](./AGENTS.md),这里是要点。

### 日常开发

```
git checkout main && git pull
git checkout -b feat/xxx        # 或 fix/xxx / refactor/xxx / chore/xxx
# 开发 → 本地验证 → commit（Conventional Commits）
git push -u origin feat/xxx
# GitHub 发 PR → 填模板 → 等 CI 全绿 → 请人 review → squash 合并
git checkout main && git pull --prune
```

### 纪律（本仓库无分支保护，靠自觉）

私有库免费版不支持分支保护，以下约定靠团队自觉执行：

- ✅ **所有改动走 PR**，不直接 push main
- ✅ **CI 必须全绿才能合并**（前端 lint/build/test + 后端 test）
- ✅ **合并前至少 1 人 review**，自己的 PR 也走流程
- ✅ **合并用 squash**（仓库已配置为仅允许 squash，分支合并后自动删除）

### Commit 规范

格式：`type: description`

- `type`：`feat` / `fix` / `refactor` / `docs` / `chore`
- 一个 commit 做一件事，不堆

---

## 常见问题

**CI 上后端测试为什么本地能过、CI 挂？**
检查是否依赖了本地 `backend/data/ics.db`。测试 `conftest.py` 会自动 `init_db()`，不要依赖外部 db 文件。

**改了表单字段后前端没更新？**
后端 `survey/schema_def.py` 是单一真相源。改完跑 `uv run python -m survey.export` 重新生成 `frontend/schema.json`。

**`.env` 找不到？**
`.env` 不入库，从 `.env.example` 复制。`LLM_API_KEY` 必填。
