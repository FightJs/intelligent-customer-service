# AGENTS.md — Intelligent Customer Service 项目协作规约

本文件是本仓库 AI agent 与人类协作者的统一开发规约。所有提交、分支、PR 必须遵守。
目标：**可溯源** —— 任何一行代码变更都能追溯到对应的 issue / PR / commit。

## 1. 仓库结构（Monorepo）

整个工作区是**单一 git 仓库**（monorepo），托管于 GitHub `HXS482/intelligent-customer-service`。
前端、后端、文档、规约统一在一个仓库内，共享一套分支与提交规范。

```
A:\Intelligent Customer Service\           ← git 根（.git 在此）
├── frontend/          # 前端（React + Vite + Tailwind，三栏布局 UI）
├── backend/           # 后端（待开发）
├── docs/
│   └── superpowers/
│       ├── specs/     # 设计文档（brainstorming 产物）
│       └── plans/     # 实现计划（writing-plans 产物）
├── AGENTS.md          # 本文件（协作规约）
├── opencode.json      # opencode 项目配置（权限 + 指令）
├── setup-github.ps1   # GitHub 环境初始化脚本
└── .gitignore         # monorepo 根排除规则
```

- **唯一 GitHub 仓库**：`intelligent-customer-service`，默认分支 `main`
- `docs/superpowers/` 是设计与计划的"源头"，每个功能先有 spec → plan → 才有代码
- `frontend/`、`backend/` 可有各自 `.gitignore` 补充子包特定排除项
- 严禁在子目录内再 `git init`（避免嵌套仓库反模式）

## 2. 分支模型（GitHub Flow）

只有两类长期分支：

| 分支 | 用途 | 保护 |
|---|---|---|
| `main` | 可发布的稳定代码 | **禁止直接 push**，只能由 PR 合入 |
| `feature/*` `fix/*` `docs/*` `chore/*` `refactor/*` | 短命工作分支 | 从最新 `main` 切出，合并后删除 |

### 分支命名
`<type>/<简短描述>-<issue号>`
- `feature/host-info-form-#12`
- `fix/dashboard-expand-bug-#18`
- `docs/readme-update`

### 工作流
1. 从最新 `main` 切分支：`git checkout main && git pull && git checkout -b feature/xxx-#N`
2. 频繁小步提交（每步可独立验证）
3. 推送并开 PR：`gh pr create`
4. PR 通过 review / CI 后 **squash merge** 到 main
5. 合并后删除分支

## 3. 提交规范（Conventional Commits）

每个 commit message 必须符合：

```
<type>(<scope>): <subject>

[可选 body]
[可选 footer: 引用 issue]
```

### type（必填，小写）
| type | 用途 |
|---|---|
| `feat` | 新功能 |
| `fix` | bug 修复 |
| `docs` | 文档变更（README、AGENTS.md、spec、plan） |
| `style` | 代码风格（格式、空格、分号），不改逻辑 |
| `refactor` | 重构，既不加功能也不修 bug |
| `perf` | 性能优化 |
| `test` | 增加/修改测试 |
| `build` | 构建系统、依赖（package.json、vite.config） |
| `ci` | CI 配置 |
| `chore` | 杂项（脚手架、.gitignore） |
| `revert` | 回滚某次提交 |

### scope（可选）
受影响的模块，如 `chatpanel`、`dashboard`、`reducer`、`schema`。

### 示例
```
feat(dashboard): 卡片网格支持就地展开编辑
fix(chatpanel): 多选项需点确认再推进 (#18)
docs: 补充 README 启动说明
chore: 项目脚手架与 Tailwind 主题
```

### 规则
- subject 用** imperative mood**（"add X" 不是 "added X"），中文用动词开头（"新增""修复"）
- 不超过 72 字符
- **禁止** `update`、`wip`、`misc` 这类无信息量 message
- 一个 commit 只做一件事

## 4. Issue 与 PR 关联（可溯源核心）

- 每个 PR 必须在描述里写 `Closes #N` 或 `Refs #N`（N 为 issue 号）
- commit footer 可加 `Refs #N`（非必需，PR 关联已足够）
- 合并 PR 时 GitHub 自动关闭对应 issue
- 禁止"无 issue 的功能提交"——新功能先开 issue 描述需求

### PR 描述模板
```markdown
## 关联 issue
Closes #N

## 变更内容
- ...

## 验证方式
- [ ] 测试通过：`cd frontend && npm test`（后端同理进 backend/）
- [ ] 构建通过：`cd frontend && npm run build`
- [ ] 手动验证：...

## 自检
- [x] commit message 符合 Conventional Commits
- [x] 无 console.log / 调试代码残留
```

## 5. Agent 专属规则

AI agent（opencode）在本项目工作时**必须**：

1. **永远不直接 push 到 main** —— 任何变更先切 feature 分支再开 PR
2. **永远不 force push** 到他人协作的分支
3. **commit message 必须符合** 第 3 节规范
4. **开 PR 前必须自检**：改了前端就 `cd frontend && npm test && npm run build`；改了后端同理进对应子包
5. **只在用户明确要求时**才 commit / push / 开 PR / 合并
6. **gh 命令用于所有 GitHub 操作**（建仓库、开 PR、查 issue、加 label）
7. **大型功能必须先有 spec + plan**（走 superpowers brainstorming → writing-plans 流程）

## 6. 标准开发流程（SOP）

> 这是**接到任何需求后的端到端动作序列**，把第 2/3/4/5 节的规则串成一条流水线。
> 每一步都有明确命令与决策点，**严禁跳步**。

### 流程总览

```
①同步 main  →  ②建 issue  →  ③切分支  →  ④编码+小步提交
   →  ⑤本地自检  →  ⑥push  →  ⑦开 PR  →  ⑧合并  →  ⑨清理
```

---

### ① 同步最新 main（起点，每次开工必做）

```bash
cd "A:/Intelligent Customer Service"   # monorepo 根
git checkout main
git pull --ff-only origin main
```
- `--ff-only`：本地有分叉时会失败而非自动 merge，防止意外污染 main。
- 失败处理：本地 main 若有分叉，先 `git reset --hard origin/main`（**仅当本地无未推送的提交**）。

---

### ② 建对应 issue（功能/fix 必需，chore/docs 可免）

```bash
gh issue create --title "feat: 简短需求描述" --body "## 需求
..."
```
- 记下返回的 issue 号 `#N`，后续分支名和 PR 都要引用。
- **禁止无 issue 的功能提交**（第 4 节）。

---

### ③ 从最新 main 切 feature 分支

```bash
git checkout -b feature/<简短描述>-#N
```
- 命名遵循第 2 节：`feature/host-info-form-#12`。
- 一条分支只做一件事；多需求开多条分支。

---

### ④ 编码 + 小步提交

```bash
# 改一点，提一点（每步可独立验证）
git add <相关文件>          # 不要无脑 git add -A，避免误带调试文件
git commit -m "feat(scope): 动词开头的描述"
```
- commit message 必须符合第 3 节 Conventional Commits。
- 一个 commit 只做一件事；禁止 `wip`/`update` 这类无信息量 message。
- **禁止提交**：`console.log`、`debugger`、临时文件、`node_modules/`、`dist/`。

---

### ⑤ 本地自检（push 前必做）

```bash
# monorepo：进入对应子包再跑（前端改动 → frontend/，后端改动 → backend/）
cd frontend && npm test && npm run build && cd ..
```
- 只改了文档（AGENTS.md / docs/）可跳过此步。
- 任一失败 → 回 ④ 修复，**不得带病 push**（第 5 节第 4 条）。
- 自检通过后再 push。

---

### ⑥ 推送分支

```bash
git push -u origin feature/<简短描述>-#N
```
- 失败处理见第 9 节「网络代理与故障排查」。
- push 超时的常见原因是凭据/代理未就绪，**不是**网络本身不通。

---

### ⑦ 开 PR（合并的唯一入口）

```bash
gh pr create \
  --title "feat(scope): 简短描述" \
  --body "Closes #N

## 变更内容
- ...

## 验证方式
- [x] npm test 通过
- [x] npm run build 通过"
```
- PR 描述**必须**含 `Closes #N`（第 4 节）。
- 自检：无 `console.log` / 调试残留。

---

### ⑧ 合并（仅用户明确同意后）

- **squash merge**（第 2 节），把多个小 commit 压成 main 上的一个干净 commit：
  ```bash
  gh pr merge <PR号> --squash --delete-branch
  ```
- 合并后 GitHub 自动关闭关联 issue。

---

### ⑨ 清理（回到起点）

```bash
git checkout main
git pull --ff-only origin main     # 拉取刚合并的代码
# feature 分支已在第 ⑧ 步删除（本地+远程）
git branch -d feature/<简短描述>-#N   # 保险：删除本地分支（如未删）
```

---

### 决策点速查

| 场景 | 动作 |
|---|---|
| 用户要一个新功能 | ② → ③（必须先有 issue） |
| 改一行 typo / 改文档 | 跳过 ②，仍走 ③→⑧（PR 强制） |
| 紧急 hotfix | 同 feature 流程，分支用 `fix/` 前缀 |
| 用户让你"提交" | 走完 ④⑤⑥，**不自动开 PR/合并**（第 5 节第 5 条）|
| 用户让你"合并" | 走 ⑧，**不自动删分支**除非用户同意 |

### SOP 自检清单（每个 PR 合并前全勾）

- [ ] 从最新 main 切的分支
- [ ] commit message 全部 Conventional Commits 格式
- [ ] 改动子包的自检通过（前端 `cd frontend && npm test && npm run build`）
- [ ] PR 描述含 `Closes #N`
- [ ] 无调试代码残留
- [ ] squash merge 到 main，分支已删

---

## 7. 可溯源检查清单

任何变更合并前，以下条件全部满足才算"可溯源"：
- [ ] 对应 issue 存在
- [ ] PR 描述含 `Closes #N`
- [ ] commit message 是 Conventional Commits 格式
- [ ] 变更在 feature 分支，经 PR 合入 main
- [ ] 测试与构建通过

## 8. 常用命令速查

```bash
# 切分支
git checkout -b feature/xxx-#N

# 提交
git add -A
git commit -m "feat(scope): 描述"

# 开 PR
gh pr create --title "feat(scope): 描述" --body "Closes #N ..."

# 查 issue
gh issue list
gh issue create --title "..." --body "..."

# 查 PR 状态
gh pr status
gh pr view --web
```

## 9. 网络代理与故障排查

### 基础配置

本机通过 `127.0.0.1:7897` 访问 GitHub（git 已配置 `http.proxy` / `https.proxy`）。
若 clone/push/auth 失败，先确认代理客户端（Clash 等）正在运行且 GitHub 规则生效。

### 首次环境配置（每次新机器/新 clone 必做）

```bash
# 1. GitHub CLI 登录（OAuth，浏览器授权）
gh auth login --hostname github.com --git-protocol https --web

# 2. 把 gh 的 token 注册为 git 的 HTTPS 凭据助手（关键！）
gh auth setup-git

# 3. 调小上传缓冲，避免大 push 在代理上挂起
git config --global http.postBuffer 524288
```

### 故障排查决策树

| 症状 | 原因 | 解决 |
|---|---|---|
| `gh auth login --web` 打印 code 后卡住 | OAuth 换 token 走 HTTPS 被代理拦截 | 确认系统代理生效后重试；或改用 PAT：`gh auth login --with-token < token.txt` |
| `git push` 超时 / 不返回 | git 没有可用 HTTPS 凭据 | `gh auth setup-git` |
| `git push` 超时（凭据已配） | postBuffer 过大，代理阻塞 | `git config http.postBuffer 524288` |
| `Connection was reset` | 代理未启用 / GitHub 被墙 | 确认 Clash 等代理在跑，规则放行 GitHub |
| `Permission denied (publickey)` over SSH | 没配 SSH key | 用 HTTPS + gh 凭据（推荐），或生成 SSH key 加到 GitHub |
| push 报 `non-fast-forward` | 远程有你没有的提交 | `git pull --rebase origin <分支>` 后再 push |

### 连通性自测命令

```bash
# 代理通不通
curl -x http://127.0.0.1:7897 -sI --max-time 8 https://api.github.com

# git 凭据通不通（成功会列出远程分支）
git ls-remote origin

# gh 认证状态
gh auth status
```
