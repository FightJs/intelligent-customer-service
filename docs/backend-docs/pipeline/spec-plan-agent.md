# Spec — Plan Agent + Skill 工具集架构

> 版本：v0.3（调研与规范，**本阶段不写业务代码**）
>
> 状态：Decided（关键项已拍板，见 §12）
>
> 关联：
> - 现有对话 Agent：`backend/agent/loop.py`、`backend/agent/tools.py`
> - 现有固定管线：`backend/pipeline/orchestrator.py`、`spec-studio-delivery-pipeline.md`
> - F1–F5 分阶段 Spec：`docs/backend-docs/pipeline/`
> - MVP 测试：`spec-plan-agent-mvp-testing.md`

---

## 1. 背景与动机

### 1.1 现状

| 能力 | 位置 | 形态 |
|------|------|------|
| 对话采集（问需求、填表） | `backend/agent/` | **Agent**：tool-use 循环，多轮迭代 |
| 方案生成 + 媒体 + 交付包 | `backend/pipeline/` | **固定管线**：`orchestrator` 按 `SKILL_ORDER` 串行调用 |

方案侧 LLM 仅以「单次 JSON 调用」出现（`pipeline/llm_calls.call_llm_json`）：

1. **Decompose**：一次调用输出检索意图
2. **Compose**：一次调用输出方案草稿

校验失败、知识库降级、预算超限等场景**没有自主改写能力**——要么 `failed`，要么死模板降级。

### 1.2 目标

1. 将「方案生成」升级为 **Plan Agent**：tool-use 循环内自主决定下一步 Skill
2. 各项能力 **Skill 化**：原子、可独立重试、可观测、幂等
3. 在最终交付前增加 **Delivery Evaluator（评估专家）**：硬门禁 + 软评分，未达标不得交付
4. 保留编排层对超时、预算、取消、落库的控制权
5. 降级交付走 **Human-in-the-Loop（HITL）**：必须经用户确认；前端提供确认交互
6. 评估阈值按 **垂类（industry）** 配置；支持 `resume_from` 中游重试

### 1.3 明确不做

| 不做 | 原因 |
|------|------|
| 替换对话采集 Agent（`agent/`） | 本 Spec 只改方案生成链路 |
| 让 Plan Agent 直接生成图/视频字节 | 媒体 API 慢且贵，由 Skill 异步执行，Agent 只触发与读结果 |
| 在 Agent 循环内改写用户已确认 `form_state` | 需求真相源仍是调研表 |
| 引入新的外部框架（LangGraph / AutoGen 等） | 复用现有 Anthropic 兼容 tool-use 模式，降低依赖 |
| 评估专家主观审美打分替代人工抽检 | 评估覆盖结构/一致性/门禁，画质仍人工抽检 |

---

## 2. 总体架构

```text
┌────────────────────────────────────────────────────────────────┐
│                    编排层 Orchestrator（壳）                     │
│   超时 / 成本上限 / 取消 / pipeline_run 状态 / 产物路径            │
└───────────────────────────┬────────────────────────────────────┘
                            │ 调用
                            ▼
┌────────────────────────────────────────────────────────────────┐
│                      Plan Agent（tool-use 循环）                 │
│  系统提示 + 目标约束 → messages.create → tool_use / end_turn      │
│  最多 N 轮；预算耗尽或 end_turn 才结束                              │
└───────────────────────────┬────────────────────────────────────┘
                            │ tools（Anthropic tool schema）
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────────┐
│  规划类 Skill  │   │  生成类 Skill  │   │  评估/门禁 Skill   │
│  decompose    │   │  compose_plan │   │  validate_plan    │
│  retrieve     │   │  refine_plan  │   │  evaluate_delivery│
│  render_doc   │   │  preview_*    │   │  package_delivery │
└───────────────┘   └───────────────┘   └───────────────────┘
```

### 2.1 分层职责

| 层 | 职责 | 不负责 |
|----|------|--------|
| **Orchestrator（壳）** | 创建 `pipeline_run`、超时、成本上限、取消检查、写 `skill_runs`、组装前端进度 | 不决定下一步调哪个 Skill |
| **Plan Agent** | 规划调用顺序、解读 Skill 返回、决定重试/改写/降级/收工 | 不绕过硬门禁、不无限重试 |
| **Skill（工具）** | 执行原子能力，返回结构化结果 + 成功/降级/失败 | 不互相调用（由 Agent 串联） |
| **Delivery Evaluator** | 最终交付前评估，输出 pass/fail + 分项得分 + 可执行修改建议 | 不修改 plan 原文、不重新生成媒体 |

---

## 3. 模块边界

### 3.1 建议目录（落地时）

```text
backend/
  agent/                      # 对话采集 Agent（不变）
  pipeline/
    plan_agent/
      loop.py                 # Plan Agent tool-use 循环
      prompts.py              # 系统提示 / 阶段约束
      tools.py                # Skill → Anthropic tool schema 映射
      budget.py               # Agent 级 token/轮次预算
    skills/                   # Skill 实现（多现有函数迁入/包装）
      decompose_requirements.py
      retrieve_knowledge.py
      compose_plan.py
      validate_plan.py
      refine_plan.py
      render_document.py
      preview_images.py
      preview_video.py
      package_delivery.py
      evaluate_delivery.py    # 评估专家
    orchestrator.py           # 退化为「壳」：超时/成本/取消/落库
    models.py                 # 契约模型（扩展）
```

> 落地时可渐进：先包一层 tool schema 调现有 `plan_document` 内函数，再逐步拆文件。**禁止**一步重写全部业务。

### 3.2 与现有模块关系

| 现有 | 改造后 |
|------|--------|
| `run_plan_document` 串联 decompose→retrieve→compose→validate→render | 拆为独立 Skill，由 Plan Agent 串联 |
| `templates_plan.build_template_plan` | 保留，作为 `compose_plan` 的降级路径（Agent 可主动选择） |
| `validate.validate_plan` | 变为 `validate_plan` Skill 的核心实现 |
| `llm_calls.call_llm_json` | `compose_plan` / `refine_plan` / `decompose` 内部实现 |
| `orchestrator.SKILL_ORDER` 硬编码顺序 | 仅约束「媒体阶段必须在 plan 之后」；plan 内顺序交给 Agent |
| F5 交叉校验 `R1–R7` | 并入 `evaluate_delivery` 硬门禁，与打包前评估统一 |

---

## 4. Plan Agent 设计

### 4.1 循环模型

复用对话 Agent 的 tool-use 形态（`agent/loop.py`）：

```text
初始化 system + 目标 + 初始状态摘要
循环（≤ MAX_AGENT_ITERATIONS）:
  1. messages.create（带 TOOL_DEFS）
  2. 若 tool_use → execute_tool(skill) → 将结果作为 tool_result 回传 → 继续
  3. 若 end_turn → 提取最终状态结论 → 结束
  4. 若预算耗尽 / 编排层取消 → 中断并落盘中间产物
```

### 4.2 约束（系统提示硬规则）

| # | 规则 |
|---|------|
| A1 | 必须先 `decompose_requirements` 再 `retrieve_knowledge`（可跳过若显式选择 template 降级） |
| A2 | `compose_plan` 之前必须有 retrieve 结果或 template 降级标记 |
| A3 | `render_document` 之前必须 `validate_plan` 通过或仅剩 soft warnings |
| A4 | `evaluate_delivery` 失败且存在 `fixable=true` 的项时，必须至少尝试一次 `refine_plan` 或重跑对应生成 Skill |
| A5 | 禁止在未调用 `evaluate_delivery` 且 pass 的情况下调用 `package_delivery` |
| A6 | 媒体 Skill（preview_images / preview_video）失败时允许 partial 交付，但必须在 package 前再评估一次 |
| A7 | 不得修改 `form_state`；不得伪造 knowledge_id |

以上规则同时在 **tool description** 与 **编排层后置断言** 中双重约束（Agent 违规 → 编排层 fail-closed）。

### 4.3 初始预算（默认值，可配置）

| 项 | 默认 | 说明 |
|----|------|------|
| `MAX_AGENT_ITERATIONS` | 12 | 含 tool_use 轮次 |
| `PLAN_PHASE_MAX_LLM_CALLS` | 8 | decompose/compose/refine 合计 |
| `REFINE_MAX_ATTEMPTS` | 3 | evaluate 失败后的改写上限 |
| `GATE_PASS_STREAK` | 2 | **连续 2 次** evaluate pass 才允许交付（防抖） |
| `HITL_CONFIRM_TIMEOUT_SEC` | **900（15 分钟）** | 降级确认窗口；**超时视为拒绝**，前端须说明「已超时，未确认降级」 |
| `SCORE_THRESHOLD_SOURCE` | `kb_then_config` | 分垂类阈值解析顺序：垂类知识库 → 配置文件 → default |
| `LLM_REVIEW_DEFAULT` | `on` | `llm_review` 默认全量开启（生产/联调）；CI 可关 |
| 墙钟超时 | 见 §7 | 按阶段由壳层控制 |

### 4.4 Agent 输入/输出契约（草案）

```python
class PlanAgentInput(BaseModel):
    pipeline_run_id: str
    session_id: str
    form_state: dict
    delivery_id: int | None = None
    allow_incomplete: bool = False
    # 允许从中游恢复
    resume_from: Literal['plan', 'images', 'video', 'package'] | None = None

class PlanAgentResult(BaseModel):
    status: Literal['succeeded', 'degraded', 'failed']
    plan_json_path: str | None
    pdf_path: str | None
    package_path: str | None
    evaluation: DeliveryGateResult | None
    tool_trace: list[ToolCallRecord]   # 可观测：每次 skill 名 + 入参摘要 + 耗时 + cost
    cost_cny: float
    warnings: list[str]
    error: str | None
```

`tool_trace` 写入 `skill_runs`（或新增 `agent_steps` 表），保证可回放。

---

## 5. Skill 工具集

### 5.1 通用约定

| 约定 | 说明 |
|------|------|
| 契约 | 显式 Pydantic 输入/输出，禁止隐式全局状态 |
| 幂等 | 同 `pipeline_run_id + skill(+intent_hash)` 重复执行复用产物，不重复计费 |
| 返回结构 | `{status, data, warnings, next_hints, cost_cny}`；`status ∈ {succeeded, degraded, failed}` |
| `next_hints` | 给 Agent 的结构化提示（如「知识库命中 0，建议 template 或换 query」） |
| 失败信息 | 含可执行建议，供 `refine_plan` / 评估专家消费 |
| 观测 | 写 `skill_runs`；Agent 轮次写 trace |

### 5.2 Skill 清单

| Skill | 类型 | 一句话 | 主要输入 | 主要输出 |
|-------|------|--------|----------|----------|
| `decompose_requirements` | 规划 | 需求 → 检索意图 | `RequirementBrief` | `list[RetrievalIntent]` |
| `retrieve_knowledge` | 规划 | 按意图 hybrid 检索 | intents | `hits[]`, `degraded: bool` |
| `compose_plan` | 生成 | 组合 PlanDraft | brief + hits | `PlanDraft` |
| `refine_plan` | 生成 | 按评估/校验问题改写 | draft + issues | `PlanDraft`（patch 后） |
| `validate_plan` | 评估 | 结构硬校验 | draft + brief | warnings, hard_errors |
| `render_document` | 生成 | 渲染 PDF/Word | draft + brief | `pdf_path`, `word_path` |
| `preview_images` | 生成 | 三机位预览图 | `plan_json_path` | images + 角度映射 |
| `preview_video` | 生成 | 预览视频 | plan + 首帧图 | `mp4_path` |
| `evaluate_delivery` | **门禁** | 最终评估专家 | plan+pdf+images+video+brief | `DeliveryGateResult` |
| `package_delivery` | 生成 | 打包交付包 | 上游产物 | package 目录 + manifest |

### 5.3 tool schema 形态（示意）

对齐现有 `agent/tools.py` 的 Anthropic 格式：

```json
{
  "name": "evaluate_delivery",
  "description": "对当前交付产物做最终评估。必须在 package_delivery 之前调用。返回 pass/fail、分项得分、硬错误与可修复建议。",
  "input_schema": {
    "type": "object",
    "properties": {
      "include_media": {
        "type": "boolean",
        "description": "是否把预览图/视频纳入本次评估（媒体已生成时必须 true）"
      }
    },
    "required": ["include_media"]
  }
}
```

Agent **不能**直接传任意文件路径；路径由 Skill 从 `pipeline_run` 上下文解析，防路径注入与串号。

---

## 6. Delivery Evaluator（评估专家）

### 6.1 定位

在 **打包交付之前** 对「方案内容 + 文档 + 媒体存在性/一致性」做最终评估。  
**未达到阈值不得交付**（`package_delivery` 拒绝或编排层 fail-closed）。

### 6.2 评估输入

| 项 | 来源 |
|----|------|
| `RequirementBrief` | `normalize_form_state` |
| `plan.json` | `compose_plan` / `refine_plan` |
| PDF 结构摘要 | `render_document`（章节标题、设备表行数、套餐档位数等结构化抽取，非全文重解析） |
| 预览图元数据 | `preview_images`（张数、角度标签、文件存在） |
| 视频元数据 | `preview_video`（存在、时长、source_image） |
| 知识引用 | `plan.meta.knowledge_refs` |

### 6.3 评估维度与默认阈值

#### 硬门禁（Hard Gate）— 任一失败 = 不得交付

| ID | 规则 | 失败动作 |
|----|------|----------|
| H1 | 必填核心需求齐全，或 `allow_incomplete=True` 且交付说明已显著标注 | fail |
| H2 | `summary` / `layout` / `setup_steps(≥3)` 结构完整 | fail |
| H3 | 设备项均有 `knowledge_id` 或 `is_custom=true` | fail |
| H4 | 至少 2 档套餐；档位金额可解析 | fail |
| H5 | PDF 存在且非空；关键章节（摘要/设备/套餐/搭建）标题可识别 | fail |
| H6 | 纳入交付的文件均存在且 sha256 可计算 | fail |
| H7 | 说明文案不得声称不存在的媒体文件 | fail |
| H8 | 评估 Skill 自身必须成功完成（解析崩溃 = fail） | fail |

#### 软评分（Soft Score）— 加权后 ≥ 阈值才 pass

| 维度 | 权重 | 说明 |
|------|------|------|
| `requirement_coverage` | 0.25 | brief 关键字段在 plan.summary / layout / steps 中有对应覆盖 |
| `equipment_consistency` | 0.20 | 已有设备标注、must_buy 逻辑、数量合理 |
| `budget_alignment` | 0.15 | 套餐中位价与 `budget_total` 偏差（容差：默认 10%，flexible 25%） |
| `knowledge_grounding` | 0.15 | 命中知识库比例；template 降级则此项最高 0.4 |
| `document_completeness` | 0.10 | PDF 章节完整度、套餐表可读性（结构信号） |
| `media_traceability` | 0.10 | 图角度齐全度、视频可追溯到 plan/scene_card |
| `llm_review` | 0.05 | LLM 复核「是否自洽、是否夸大」；**默认全量 ON**；失败按 0.5 折算，不阻断 |

默认（全局兜底，可被垂类覆盖）：

```text
SCORE_THRESHOLD = 0.75
SCORE_THRESHOLD_DEGRADED = 0.60
llm_review 默认 ON（生产/联调/联调环境全量开启）；仅 CI mock 可关
```

#### 分垂类阈值 — 解析顺序（已拍板）

**优先查垂类知识库，其次配置文件，最后 default。**

```text
brief.industry
    │
    ▼
① 垂类知识库（vertical_knowledge 或专用 collection）
   查询：industry + scene=gate_threshold / 条目 type=score_threshold
   命中且 payload 含 pass/degraded 合法数值 → 采用
    │ miss / 非法
    ▼
② 配置文件 SCORE_THRESHOLDS_BY_INDUSTRY
    │ 无该 industry
    ▼
③ default（0.75 / 0.60）
```

配置文件兜底形态：

```python
SCORE_THRESHOLDS_BY_INDUSTRY = {
    "default":  {"pass": 0.75, "degraded": 0.60},
    "women":    {"pass": 0.75, "degraded": 0.60},
    "beauty":   {"pass": 0.78, "degraded": 0.62},
    "food":     {"pass": 0.72, "degraded": 0.58},
    "digital":  {"pass": 0.80, "degraded": 0.65},
}
```

知识库阈值条目契约（ingest 侧约定）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `industry` | str | 与调研表一致的英文枚举 |
| `scene` | str | 固定 `gate_threshold` |
| `thresholds.pass` | float | 0–1 |
| `thresholds.degraded` | float | 0–1，且必须 < pass |
| `text` | str | BM25 正文（可写「美妆交付门禁阈值」等） |

| 规则 | 说明 |
|------|------|
| 解析键 | `form_state` → `RequirementBrief.industry` |
| 校验 | `0 ≤ degraded < pass ≤ 1`，否则视为非法并继续回落 |
| 知识库不可用 | 不阻断 evaluate；记 warning，走 ②/③ |
| 运行时可见 | `DeliveryGateResult.threshold` / `threshold_degraded` / `threshold_source`（`kb` \| `config` \| `default`） |
| 变更影响 | 知识库/配置热更新只影响新 evaluate；不重跑历史单 |

### 6.4 输出契约（草案）

```python
class GateDimensionScore(BaseModel):
    name: str
    score: float                    # 0.0–1.0
    weight: float
    details: list[str]

class GateIssue(BaseModel):
    id: str                         # H1 / S-budget / ...
    severity: Literal['hard', 'soft']
    message: str
    fixable: bool                   # refine_plan 能否处理
    suggested_action: str | None    # e.g. "refine_plan: 调整进阶档价格区间"

class DeliveryGateResult(BaseModel):
    passed: bool
    hard_errors: list[GateIssue]
    soft_issues: list[GateIssue]
    dimensions: list[GateDimensionScore]
    weighted_score: float
    industry: str
    threshold: float
    threshold_degraded: float
    threshold_source: Literal['kb', 'config', 'default']
    consecutive_pass_count: int
    delivery_decision: Literal['pass', 'degraded_candidate', 'fail']
    evaluated_at: str
    include_media: bool
    cost_cny: float
```

`delivery_decision` 语义：

| 值 | 条件 | 后续 |
|----|------|------|
| `pass` | 无 hard，且 `weighted_score ≥ threshold` 且 `consecutive_pass_count ≥ 2` | 直接允许 package |
| `degraded_candidate` | 无 hard，且 `threshold_degraded ≤ score < threshold`（或缺媒体等允许缺口）且连续 pass 未满 2 或需用户确认 | 进入 HITL，见 §6.7 |
| `fail` | 有 hard，或 `score < threshold_degraded`，或 refine 用尽 | failed；不得 package |

### 6.5 与 Agent 的交互

```text
Agent: evaluate_delivery(include_media=...)
  → decision=pass
        → consecutive_pass_count +1
        → 若 count ≥ GATE_PASS_STREAK(2) → Agent 可调用 package_delivery
        → 若 count < 2 → 需再跑一轮「轻校验 evaluate」（可不 refine）直到连续 2 次 pass
  → decision=degraded_candidate
        → 暂停 Agent；进入 HITL 确认（§6.7）
  → decision=fail 且存在 fixable
        → Agent 调用 refine_plan / 重跑对应生成 Skill
        → 再次 evaluate（计入 REFINE_MAX_ATTEMPTS；连续 pass 计数在 refine 后清零）
  → decision=fail 且不可修或次数用尽
        → Agent 结束为 failed
```

**防抖规则**：任一次 `refine_plan` / 生成 Skill 重跑成功后，`consecutive_pass_count` 重置为 0，必须重新累计 2 次连续 pass。

### 6.6 评估专家自身规则

| 规则 | 说明 |
|------|------|
| 确定性优先 | H1–H8 与 soft 的结构分必须纯规则可测，不依赖 LLM |
| LLM 仅辅助 | `llm_review` 只影响 0.05 权重，超时/失败按 0.5 计；**默认全量 ON**（`LLM_REVIEW_DEFAULT=on`），仅 CI mock 可关 |
| 不改产物 | 评估只读；修复一律通过 `refine_plan` / 重生成 |
| 可观测 | 结果落库 `skill_runs` 或 `gate_results`，供运营抽查 |
| 防「自己评自己过」 | `evaluate_delivery` 的实现不得复用 `compose_plan` 的同一 prompt/同一调用 |

### 6.7 降级交付 — Human-in-the-Loop（已拍板）

**原则**：系统**永不静默降级交付**。`degraded_candidate` 必须停在待确认态，由**用户**（下单客户，而非模型）显式确认后才打包。

#### 流程

```text
evaluate → degraded_candidate
    │
    ▼
pipeline_run.status = awaiting_degraded_confirm
写入 degraded_proposal（缺口列表 + 分项分 + 未达阈值原因）
    │
    ▼
前端进度页展示「降级确认」卡片（见前端契约）
    │
    ├─ 用户确认 accept
    │     → mark_degraded_approved(user_id, timestamp)
    │     → consecutive 规则：HITL 路径不要求 2 次 pass，但必须无 hard 且 score ≥ threshold_degraded
    │     → package_delivery → status=degraded
    │
    ├─ 用户拒绝 reject
    │     → status=failed，error=用户拒绝降级交付
    │
    └─ 超时 HITL_CONFIRM_TIMEOUT_SEC（**15 分钟**）
          → 默认拒绝 → status=failed
          → 前端必须展示：「降级确认已超时（15 分钟），已按未确认处理，未进行降级交付」
```

#### 降级提案内容（给用户看的，必须可读）

| 字段 | 说明 |
|------|------|
| `gaps` | 缺什么：如「预览视频未生成」「方案来自通用模板（知识库命中不足）」 |
| `score` / `threshold` | 当前软分与该垂类 pass 阈值 |
| `top_issues` | 影响最大的 ≤5 条 soft issues（中文说明） |
| `what_user_gets` | 确认后仍会得到：plan PDF、已有预览图、设备清单等 |
| `what_user_misses` | 确认后仍缺失的能力 |

#### 与 Agent 边界

| 角色 | 可以 | 不可以 |
|------|------|--------|
| Plan Agent | 生成 `degraded_proposal` 所需事实；在 fail 路径 refine | 替用户点确认；伪造「用户已同意」 |
| 编排层 | 写 `awaiting_degraded_confirm`；暴露 confirm/reject API | 在未 confirm 时调用 `package_delivery` |
| 前端 | 展示提案、收集确认、轮询/推送状态 | 前端本地判定 pass 后静默打包装载 |

#### 状态机片段

```text
running → awaiting_degraded_confirm → (accept) → running → package → degraded
                             └────→ (reject|timeout) → failed
```

`awaiting_degraded_confirm` 期间：取消仍然有效；不得继续调用付费媒体 API（除非用户在提案里勾选「继续生成缺失媒体再确认」——**本期不做**，提案只读）。

---

## 7. 编排层（壳）改造

### 7.1 保留职责

1. 创建/更新 `pipeline_runs`
2. 阶段墙钟超时（在现有基础上扩展 Agent 阶段）
3. 成本上限熔断（`COST_CAP_CNY` 可配置）
4. 取消（轮询 `status=cancelled`）
5. 中游重试入口（`resume_from`，**进 MVP**）
6. 组装 `build_pipeline_detail` 给前端
7. HITL：`awaiting_degraded_confirm` 状态管理、confirm/reject API、超时默认拒绝
8. 强制连续 pass：`GATE_PASS_STREAK` 未满不得 package

### 7.2 建议超时（默认）

| 阶段 | 超时 | 说明 |
|------|------|------|
| plan_agent（F2 闭环） | 240s | 含 decompose/retrieve/compose/validate/refine/render/evaluate |
| preview_images | 360s | 维持现状 |
| preview_video | 360s | 维持现状 |
| evaluate_delivery（媒体后二次） | 60s | 规则为主 |
| package_delivery | 60s | 维持现状 |

### 7.3 编排顺序（改造后）

```text
创建 pipeline_run
  → Plan Agent（生成方案闭环，含 plan 级 evaluate，需连续 2 次 pass 或进入 HITL）
  → preview_images（异步 Skill；壳层超时；resume_from 可从中游进入）
  → preview_video
  → evaluate_delivery(include_media=True)   # 最终门禁，壳层强制
  → decision=pass 且 streak≥2 → package
  → decision=degraded_candidate → HITL 确认 → package 或 failed
  → decision=fail → failed
```

**注意**：
1. 媒体后的 `evaluate_delivery` 由 **壳层强制调用**，不依赖 Agent 是否记得——保证「不过门禁不打包」在架构上不可绕过。
2. `package_delivery` 入参必须带 `gate_pass_token`（由壳层在 pass / HITL accept 后签发）；无 token 拒绝执行。

---

## 8. 状态与降级矩阵

### 8.1 状态

| 状态 | 含义 |
|------|------|
| `succeeded` | Agent 完成；连续 2 次 evaluate pass；产物齐全；**无需**用户降级确认 |
| `awaiting_degraded_confirm` | 已生成降级提案，**等待用户 HITL 确认** |
| `degraded` | 用户已确认降级后打包完成（有缺口说明） |
| `failed` | 硬门禁失败 / 用户拒绝降级 / 确认超时 / 预算耗尽 / 超时 / 评估不可修复 |

**不存在「系统自动降级交付」状态。** `degraded` 只能从 `awaiting_degraded_confirm` + accept 进入。

### 8.2 场景矩阵

| 场景 | 行为 |
|------|------|
| 知识库 0 命中 | Agent 可重试换 query（≤2）→ template `compose` → knowledge_grounding 降权 → 若达 degraded 阈值则 HITL |
| validate hard_error | 必须 refine；refine 后仍 hard → failed（**不可** HITL 降级） |
| evaluate 软分不足但 ≥ degraded 阈值 | refine ≤3 → 仍不足 → `degraded_candidate` → HITL |
| 软分 < degraded 阈值 | 直接 failed，不进 HITL |
| 连续 pass 未满 2 且无 refine | 再跑 evaluate 直到 streak=2；期间不得 package |
| 图片 partial / 缺视频 | 计入 gaps；可能 degraded_candidate → HITL |
| Agent 违规（未 evaluate 就 package） | 壳层拒绝（无 gate_pass_token），记 error |
| 用户拒绝降级 / 超时未确认 | failed；error 写明原因 |
| 成本熔断 | 立即停 Agent，落盘已产 plan（若有），failed |

---

## 9. 可观测与数据落库

| 数据 | 位置 |
|------|------|
| pipeline 状态 | `pipeline_runs`（沿用） |
| Skill 执行 | `skill_runs`（沿用，Agent 每次 tool 调用对应一条） |
| Agent 轨迹 | 建议 `agent_steps`：iteration, tool_name, input_digest, latency, tokens, cost |
| 评估结果 | `gate_results`：pipeline_run_id, passed, decision, score, industry, threshold, streak, issues JSON |
| HITL | `pipeline_runs.status=awaiting_degraded_confirm` + `degraded_proposal` JSON；confirm/reject 审计字段 |

### 9.1 进度 API 契约（前端）

```json
{
  "phase": "plan | media | gate | hitl | package",
  "current_skill": "compose_plan",
  "last_gate": {
    "passed": false,
    "delivery_decision": "degraded_candidate",
    "weighted_score": 0.68,
    "industry": "beauty",
    "threshold": 0.78,
    "threshold_degraded": 0.62,
    "consecutive_pass_count": 0,
    "fixable": 2
  },
  "hitl": {
    "required": true,
    "proposal_id": "gate_123",
    "gaps": ["预览视频未生成", "方案来自通用模板"],
    "top_issues": [{"id": "S-knowledge", "message": "知识库命中不足"}],
    "what_user_gets": ["方案 PDF", "设备清单", "2 张预览图"],
    "what_user_misses": ["预览视频", "第三机位图"],
    "expires_at": "2026-09-05T12:00:00Z"
  },
  "skills_ui": {"plan": "succeeded", "images": "partial", "video": "failed", "package": "pending"}
}
```

### 9.2 HITL API

| 方法 | 路径（草案） | 说明 |
|------|--------------|------|
| POST | `/api/pipeline/{id}/degraded/confirm` | 用户确认降级；body 可含确认文案版本 |
| POST | `/api/pipeline/{id}/degraded/reject` | 用户拒绝 |
| GET | `/api/pipeline/{id}` | 返回上述进度契约，含 `hitl` 块 |

鉴权：仅会话属主可 confirm/reject；管理员可旁路查看但不可代确认（审计区分 `actor`）。

### 9.3 前端展示要求

| 视图 | 要求 |
|------|------|
| 工作台进度页 | `awaiting_degraded_confirm` 时突出「待确认」；**15 分钟倒计时**展示 `expires_at` |
| 降级卡片 | 必须同时展示 **缺口** 与 **仍可获得内容**；主按钮「确认接受降级交付」，次按钮「放弃」 |
| 确认后 | 进入打包；结果页状态为「已降级交付」，可下载且 README 标注 gaps |
| 拒绝 | 状态 failed，文案「已放弃降级交付」；提供「重新生成」入口 |
| **超时** | 状态 failed；文案固定说明：「降级确认超过 15 分钟未操作，系统已默认拒绝，未进行降级交付」；提供「重新生成」 |
| 门禁来源 | 进度/结果页可展示 `threshold_source`（知识库/配置/默认），便于运营核对 |
| 管理端 | 可看 proposal 全文与审计，但不提供代确认按钮 |

禁止：仅 toast 询问后无记录确认；禁止前端在未调用 confirm API 时把 UI 标成已交付。

---

## 10. 安全与合规

| 项 | 要求 |
|----|------|
| 路径 | Skill 内解析 artifact 根目录，禁止模型传绝对路径 |
| 注入 | tool 入参 Pydantic 校验；文本进 prompt 前长度截断 |
| 幂等费用 | 同 skill 产物复用不重复计费 |
| 取消 | 取消后不得继续调用付费媒体 API |
| 评估绕过 | package 前 gate 由壳层强制，非 Agent 可选步骤 |
| HITL 绕过 | `package_delivery` 校验 `gate_pass_token`；token 仅在 streak≥2 pass 或 HITL accept 后由壳层签发 |
| 降级伪造 | Agent 工具集中**无** confirm 工具；confirm 只能走用户鉴权 HTTP API |
| 密钥 | 维持现状，不进 tool 返回 |

---

## 11. 实施阶段（建议）

| 阶段 | 内容 | 出口标准 |
|------|------|----------|
| **M0 Spec** | 本文 + MVP 测试 Spec | 评审通过 |
| **M1 Plan Agent 闭环** | decompose/retrieve/compose/validate/refine/render + plan 级 evaluate + **连续 2 次 pass** + **分垂类阈值** | MVP 测试 T1–T3、T4.2 通过 |
| **M2 门禁 + HITL + resume** | 壳层强制 evaluate；gate_pass_token；降级 HITL API + 前端卡片；`resume_from` | T4、T8、T1.8、T7.3 通过 |
| **M3 媒体接入 Agent** | preview_* 作为工具；媒体后二次 evaluate | T5–T6 通过 |
| **M4 可观测与运营** | agent_steps / gate_results / 前端进度增强 | T6、T7.5 通过 |
| **M5 切流** | 特性开关 `PLAN_AGENT_ENABLED`，灰度对比旧管线 | 对比报告 |

**MVP = M1 + M2**：方案生成 Agent 化 + 门禁不可绕过 + **降级必须用户确认** + **可中游重试**。

---

## 12. 已拍板决策（2026-08-30）

| # | 问题 | 决策 |
|---|------|------|
| 1 | 降级交付默认策略 | **HITL**：不得静默降级；`degraded_candidate` → 用户确认后才打包；前端必须有确认 UI（§6.7、§9.3） |
| 2 | 阈值是否分垂类 | **是**。解析顺序：**垂类知识库 → 配置文件 → default**（§6.3） |
| 3 | refine 后是否连续 2 次 pass | **是**。`GATE_PASS_STREAK=2`；refine/重生成后 streak 清零（§6.5） |
| 4 | `resume_from` 是否进 MVP | **是**。属 M2，见测试 T1.8 |
| 5 | evaluate 次数用尽后运营动作 | 用户侧 failed + 「重新生成」；管理员仅查看，不代确认降级（延后「人工审核队列」） |
| 6 | 媒体阶段是否 Agent 化 | MVP 保持壳层固定顺序；Agent 只在 plan 阶段自治（M3 再评估） |
| 7 | 评估分展示对象 | 用户：降级卡片中的 score/threshold/缺口；管理员：完整 issues + 审计 |
| 8 | **HITL 确认时限** | **15 分钟**；超时默认拒绝；**前端必须说明超时已按未确认处理** |
| 9 | **阈值配置源** | **优先垂类知识库**，其次配置文件，再次 default |
| 10 | **llm_review** | **默认全量 ON**；仅 CI mock 可关 |

仍开放（不阻塞 M1/M2）：

1. 知识库阈值条目的运营写入路径（ingest 脚本 / admin API）M几做？
2. HITL 超时后是否允许「仅延长一次」（产品未拍板，默认不允许）？

---

## 13. 参考

- 对话 Agent 循环：`backend/agent/loop.py`
- Tool 定义风格：`backend/agent/tools.py`
- 现有管线总览：`docs/backend-docs/spec-studio-delivery-pipeline.md`
- F2–F5：`docs/backend-docs/pipeline/spec-f*.md`
- 交叉校验 R1–R7：`spec-f5-final-package-skill.md` §5
