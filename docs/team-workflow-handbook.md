# 团队成员开发操作手册

> 新成员必读。本文档描述从 clone 到合并的完整流程。
> 环境搭建见根目录 [README](../README.md),本文档只讲协作流程。

---

## 一、首次准备(每人只做一次)

### 1. 接受邀请
邮箱/GitHub 收到协作者邀请后点 **Accept**。没收到告诉队长重新发。

### 2. 克隆仓库
```bash
git clone https://github.com/FightJs/intelligent-customer-service.git
cd intelligent-customer-service
```

### 3. 配置本地环境
按根目录 `README.md` 的「新协作者上手」装好前后端依赖。后端记得 `cp backend/.env.example backend/.env` 并填 `LLM_API_KEY`(找队长要)。

---

## 二、每次开发的标准流程

```
① 拉最新代码
② 切功能分支
③ 开发 + commit
④ 推送 + 开 PR
⑤ 等 CI 全绿 + 请人 review
⑥ squash 合并
⑦ 切回 main 拉最新
```

### ① 拉最新代码
```bash
git checkout main
git pull
```

### ② 切功能分支
**分支名格式**:`类型/简短描述`
```bash
git checkout -b feat/xxx      # 新功能
git checkout -b fix/xxx       # 修 bug
git checkout -b refactor/xxx  # 重构
git checkout -b docs/xxx      # 文档
git checkout -b chore/xxx     # 杂项(配置/依赖等)
```

### ③ 开发 + commit
**Commit 格式**:`type: description`(中英文不混用,一个 commit 做一件事)
```bash
git add <文件>
git commit -m "feat: 支持多主播信息采集"
```
- `type`: `feat` / `fix` / `refactor` / `docs` / `chore`
- 本地先验证(后端 `uv run pytest`,前端 `npm test && npm run build`)

### ④ 推送 + 开 PR
```bash
git push -u origin feat/xxx
```
推送后到 GitHub 网页,**发 Pull Request**:
- base 选 `main`
- **PR 标题 = 最终 commit 信息**(如 `feat: 支持多主播信息采集`)
- **PR 描述按模板填**:What / Why / Changes / Testing

### ⑤ 等 CI 全绿 + 请人 review
- 提交 PR 后自动触发 CI(前端 lint/build/test + 后端 test,**约 1 分钟**)
- **CI 红了先自己修**,不要等别人看
- 绿了之后 @ 一个队友 review

### ⑥ squash 合并
- 仓库只允许 **squash 合并**(你的多个 commit 会被压成一个干净的 commit 进 main)
- 合并后**分支自动删除**(不用手动清)

### ⑦ 切回 main 拉最新
```bash
git checkout main
git pull --prune    # --prune 顺便清理本地已删的远端分支引用
```

---

## 三、团队纪律(本仓库无强制保护,靠自觉)

| 规则 | 说明 |
|---|---|
| ✅ **绝不直接 push main** | 所有改动走 PR,哪怕一行 |
| ✅ **CI 必须全绿才能合并** | 红 PR 不合并,先修 |
| ✅ **合并前至少 1 人 review** | 自己的 PR 也走流程 |
| ✅ **只用 squash 合并** | 仓库已限制,别尝试其他方式 |
| ✅ **不要 force push** | 会覆盖他人工作 |

> 本仓库是私有库 + GitHub 免费版,**不支持分支保护**,以上规则系统不会强制拦截,完全靠大家守规矩。

---

## 四、常见情况处理

### Q: 我的分支落后 main 了,怎么同步?
```bash
git checkout feat/xxx
git fetch origin
git rebase origin/main     # 把 main 最新拉到你的分支底下
# 如有冲突,解决后 git add → git rebase --continue
git push --force-with-lease  # rebase 后需要强推(仅限自己的分支)
```

### Q: CI 挂了怎么看错误?
PR 页面点 `Details` → 看哪个 job 红(Frontend / Backend)→ 看日志。

### Q: review 提了意见怎么改?
```bash
# 在同一分支继续改
git add <文件>
git commit -m "fix: 按 review 意见调整 xxx"
git push          # 不用开新 PR,原 PR 自动更新
```

### Q: 我改了后端表单 schema,前端没更新?
后端 `backend/survey/schema_def.py` 是单一真相源。改完**必须**重新生成:
```bash
cd backend
uv run python -m survey.export   # 重新生成 frontend/schema.json
git add frontend/schema.json backend/survey/schema_def.py
```
**忘了这步,前端就用旧 schema,前后端不一致。** 这个改动要和 schema 改动放同一个 PR。

### Q: 要拉别人的 PR 到本地看?
```bash
git fetch origin pull/PR编号/head:pr-编号
git checkout pr-编号
```

### Q: 后端测试本地能过、CI 挂了?
检查是否依赖了本地 `backend/data/ics.db`。测试 `conftest.py` 会自动 `init_db()`,不要依赖外部 db 文件。

---

## 五、给新成员的提醒

1. **第一次先走通流程**:clone → 改个 README 错字 → 开 PR → 合并。把流程跑顺比写代码重要。
2. **CI 绿不等于代码对**:CI 只查 lint/build/test,业务逻辑对不对要靠 review。
3. **有问题及时问**:卡住超过 30 分钟就在群里 @,别闷头搞。
