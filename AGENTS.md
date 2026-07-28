# Nerve

## Thinking

```
GOAL: <one sentence>
APPROACH: <one sentence — pick ONE path>
EDGE: <one risk to watch>
```

Trivial requests: skip the think block. Match user's language.

## Code

- 模块化组件化，高内聚低耦合，单一职责
- 简洁高效可读性高，不过度设计
- 不写兜底代码、冗余代码、猜测性代码
- 不明白的地方询问，不为"保证能跑"堆不必要的代码
- 不确定接口响应结构时，读源码或问，不要猜
- Write when it matters across sessions. Reply first, write after.

## Workflow

### Todo List

多步骤任务必须用 TodoList 跟踪进度：
- 任务拆解为可验证的步骤
- 每步完成后标记状态（pending/in_progress/completed）
- 遇到阻塞及时暴露，不要静默跳过
- 完成后回顾 todo list 确认无遗漏

### Superpowers

复杂任务善用 superpowers 技巧：
- **Workflow**：多阶段任务（理解→设计→实现→审查）用 workflow 串联，每阶段独立验证
- **Parallel agents**：独立子任务并行执行，不串行等待
- **Adversarial verify**：关键决策用多个独立视角验证，避免单一判断失误
- **Loop-until-dry**：不确定范围的发现任务，持续探索直到连续无新发现
- **Multi-modal sweep**：从不同角度（按容器/内容/实体/时间）搜索，避免单角度遗漏
- **Completeness critic**：最终检查"还有什么遗漏"，确保覆盖完整

选择依据：
- 简单任务 → 直接执行，不搞复杂
- 多步骤但无依赖 → TodoList
- 有依赖的多阶段 → Workflow
- 需要并行 → Parallel agents
- 需要验证 → Adversarial verify

## Git

### 开发流程
1. 从 main 切分支: `fix/xxx` / `feat/xxx` / `refactor/xxx` / `chore/xxx`
2. 改完 → 本地 build/test 验证 → commit（Conventional Commits）
3. push → 创建 PR → 自己 review diff → 等 CI 全绿
4. 至少 1 人 review approve → squash 合并 → 分支自动删除
5. 切回 main → `git pull --prune`

### Commit
- 格式: `type: description`（fix/feat/refactor/docs/chore）
- 中英文随用户，不混用
- 一个 commit 做一件事，不堆

### PR
- title = commit message
- body 写 What / Why / Changes / Testing（PR 模板已自动填）
- 自己先 review 再请人看
- **CI 必须全绿才能合并**（前端 lint/build/test + 后端 test）

### 团队纪律（无分支保护，靠自觉）
> 私有库免费版不支持分支保护，以下约定靠团队自觉执行：
- **绝不直接 push main**，所有改动走 PR
- **CI 红了不合并**，先修
- **合并用 squash**（仓库已配置为仅允许 squash）
- **合并前至少 1 人 review**，即使是 owner 自己的 PR 也走流程
- **分支及时删**（已配置合并后自动删除）

### 不做的事
- 不自动 push（除非用户说）
- 不自动 merge（除非用户说）
- 不 force push

## Security

No data exfiltration. No destructive commands without asking. Ask before anything that leaves the machine.

## Voice

Never "作为一个AI" / "As an AI". Never hedge (可能/大概/也许). Cite memory sources.