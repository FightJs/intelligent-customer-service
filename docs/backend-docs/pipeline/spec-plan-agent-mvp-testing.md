# MVP 测试 Spec — Plan Agent + Delivery Gate

> 版本：v0.3（**本阶段不写业务代码**）
>
> 配套架构：[spec-plan-agent.md](./spec-plan-agent.md)（v0.3：HITL 15min、阈值 KB→config、llm_review 默认全开、streak=2、resume_from）
>
> MVP 范围：**M1 + M2**（Plan Agent 闭环、门禁强制、**降级 HITL**、**连续 2 次 pass**、**分垂类阈值**、**resume_from**）；媒体接入 Agent（M3）仅列预留用例。

---

## 1. 目标与范围

### 1.1 目标

1. Plan Agent 能在预算内自主完成「拆解 → 检索 → 组合 → 校验 → 改写 → 渲染 → 评估」闭环
2. Delivery Evaluator 硬门禁不可绕过：未 pass 不得 `package_delivery`
3. 确定性规则（H1–H8、软分结构项）可在 **无真实 LLM** 下 CI 全绿
4. 轨迹与成本可观测，便于回放与对账

### 1.2 范围内

| 层 | 内容 |
|----|------|
| 单元 | Skill 纯函数、门禁规则、分数加权、tool schema 映射 |
| 契约 | PlanAgentInput/Result、DeliveryGateResult、skill 返回结构 |
| 集成 | mock LLM 下 Agent 循环、refine 路径、壳层强制门禁 |
| 负面 | 违规调用顺序、预算熔断、取消、评估崩溃 |
| E2E（mock） | form_state → gate pass → package；gate fail → 无 package |

### 1.3 范围外

| 不做 | 说明 |
|------|------|
| 真实生图/生视频画质主观分 | 人工抽检，见联调 Spec |
| 对话采集 Agent（`agent/loop`）回归 | 已有 `test_loop.py`，本 Spec 不重复 |
| 压测 / 多租户隔离 | 另立项 |
| 前端 UI 断言 | 仅断言 API 进度契约字段 |

---

## 2. 测试分层与目录

```text
backend/tests/
  plan_agent/
    test_tool_schema.py           # tool 定义与入参校验
    test_agent_loop_mock.py       # mock messages.create 的循环行为
    test_agent_constraints.py     # A1–A7 阶段约束（壳层断言）
    test_budget_and_timeout.py    # 轮次/成本熔断/超时
    test_agent_trace.py           # tool_trace / agent_steps 落库
  delivery_gate/
    test_hard_gates.py            # H1–H8
    test_soft_scores.py           # 维度分与加权（分垂类）
    test_evaluate_skill.py        # evaluate_delivery 契约与只读
    test_gate_blocks_package.py   # 未 pass / 无 token 禁止打包
    test_consecutive_pass.py      # streak=2 防抖
  hitl/
    test_degraded_proposal.py     # 进入 awaiting + proposal 字段
    test_confirm_reject.py        # 确认/拒绝/审计
    test_hitl_timeout.py          # 超时默认拒绝
    test_hitl_auth.py             # 非属主 403
    test_hitl_no_agent_tool.py    # Agent 工具集无 confirm
  pipeline_agent_integration/
    test_plan_agent_happy_path.py
    test_plan_agent_refine_loop.py
    test_plan_agent_template_degrade.py
    test_orchestrator_forced_gate.py
    test_e2e_mock_mvp.py
  fixtures/
    form_state_minimal.json
    form_state_full.json
    form_state_incomplete.json
    plan_sample_ok.json
    plan_sample_bad_budget.json
    plan_sample_phantom_device.json
    gate_result_pass.json
    gate_result_fail_fixable.json
    mock_llm_script_agent.json    # 脚本化 tool_use 序列
```

命名：`test_<模块>_<行为>`；断言失败信息必须带 `pipeline_run_id`。

---

## 3. Mock 与环境边界

| 依赖 | CI 默认 | 本地可选 |
|------|---------|----------|
| LLM（Anthropic 兼容） | **脚本化 mock**：按 `mock_llm_script_agent.json` 依次返回 tool_use | 可选真端点 smoke |
| 知识库 Qdrant | memory:// 或 fixture hits 注入 | 真库 |
| Embedding / Rerank | mock / identity | 真服务 |
| WeasyPrint PDF | mock `render_document` 返回假 bytes + 路径；或最小 HTML | 真渲染 |
| 媒体 API | 不进入 MVP 必测路径 | 联调 |

**原则**：CI 不依赖密钥、不依赖网络；`llm_review` 维度 CI 默认 OFF。

---

## 4. 用例集

> 优先级：P0 阻断发布；P1 MVP 必须；P2 建议本阶段做完。

### T1 — Plan Agent 循环（集成，mock LLM）

| 用例 | 优先级 | 前置 | 步骤 | 期望 |
|------|--------|------|------|------|
| T1.1 快乐路径（需 2 次 pass） | P0 | full form_state；脚本：…→evaluate(pass,streak=1)→evaluate(pass,streak=2) | 跑 `run_plan_agent` | `status=succeeded`；plan.json + pdf；streak=2；有 gate_pass_token |
| T1.2 跳过 decompose 直接 compose | P0 | 脚本：首步 compose_plan | Agent 循环 | 被 tool 层拒绝或壳层断言 fail；**不得**静默成功 |
| T1.3 evaluate 失败后 refine + 连续 2 次 pass | P0 | 脚本：evaluate(fail,fixable) → refine → evaluate(pass) → evaluate(pass) | 跑 Agent | refine 后 streak 清零；最终 `consecutive_pass_count≥2`；才允许 package |
| T1.4 硬错误 refine 仍失败 | P0 | evaluate 连续 fail 且 hard | 跑 Agent | `status=failed`；无 package；**不得**进入 HITL |
| T1.5 知识库 0 命中 | P1 | search_fn 返回空；Agent 选择 template | 跑 Agent | plan.meta 含 `knowledge_unavailable`；knowledge_grounding ≤ 0.4；若 score∈[degraded,pass) → `degraded_candidate` |
| T1.6 中断/取消 | P1 | 第 2 次 tool 调用时 `status=cancelled` | 跑 Agent | 立即停止；不再调付费 Skill；trace 完整 |
| T1.7 最大迭代 | P1 | 脚本永不 end_turn / 永不 pass | 跑 Agent | 达 `MAX_AGENT_ITERATIONS` 或 `REFINE_MAX_ATTEMPTS` 后 failed；不无限循环 |
| T1.8 中游恢复 resume_from=images | **P0（进 MVP）** | 已有 plan.json 且 plan 级 gate 已 pass | 跑壳层 | 跳过 plan 闭环；从媒体阶段继续；streak/token 继承策略见 T1.9 |
| T1.9 resume 后 streak/token | P0 | resume_from 时 streak=1 | 跑壳层 | 媒体后 evaluate 需再凑满 2 次 pass 或 HITL；禁止直接沿用旧 token 打包 |
| T1.10 单次 pass 不得 package | P0 | 脚本：… evaluate(pass) 后 end_turn | 跑 Agent/壳层 | `delivery_decision≠pass` 或 package 拒绝；需第二次 evaluate |

### T2 — Skill 工具契约（单元）

| 用例 | 优先级 | 期望 |
|------|--------|------|
| T2.1 TOOL_DEFS 合法 | P0 | 每个 tool 有 name/description/input_schema；JSON Schema 可序列化 |
| T2.2 禁止模型传绝对路径 | P0 | `preview_*` / `render` / `package` 的 schema **无** path 字段；入参仅业务开关 |
| T2.3 Skill 返回结构 | P0 | 每个 Skill 成功时含 `status/data/warnings/next_hints/cost_cny` |
| T2.4 幂等 | P1 | 同 pipeline_run_id 二次 `compose_plan`（force=false）复用产物，cost 不增加或为 0 |
| T2.5 validate 与 evaluate 分离 | P0 | 两者实现不共享同一 prompt 常量；evaluate 可单独跑 |
| T2.6 非法 collection/枚举 | P1 | decompose 输出非法 collection → parse 失败 → fallback intents + warning |

### T3 — Delivery Evaluator 硬门禁（单元）

| 用例 | 优先级 | fixture | 期望 |
|------|--------|---------|------|
| T3.1 H1 核心字段缺失 | P0 | form_state_incomplete + allow_incomplete=False | hard fail；issue.fixable=false 或指向需求补全 |
| T3.2 H1 incomplete 但已标注 | P1 | allow_incomplete=True 且交付说明含标注 | 不因 H1 拒绝 |
| T3.3 H2 summary/layout/steps | P0 | plan 缺 setup_steps 或 <3 | hard fail |
| T3.4 H3 幻影设备 | P0 | plan_sample_phantom_device.json | hard fail；消息含设备名 |
| T3.5 H4 套餐档位不足/金额不可解析 | P0 | 仅 1 档或 total_range=`''` | hard fail |
| T3.6 H5 PDF 空/缺章节 | P0 | mock pdf 为空 bytes 或无关键标题 | hard fail |
| T3.7 H6 文件缺失 | P1 | manifest 声称的文件被删 | hard fail |
| T3.8 H7 声称不存在媒体 | P1 | README 提到 video/preview.mp4 但文件不存在 | hard fail |
| T3.9 H8 评估内部异常 | P0 | 注入 evaluate 依赖抛错 | 返回 failed 门禁结果，**不得**抛裸异常给 Agent 当 pass |
| T3.10 全 hard 通过 | P0 | plan_sample_ok.json | hard_errors == [] |

### T4 — 软评分与门禁阻断（单元 + 集成）

| 用例 | 优先级 | 期望 |
|------|--------|------|
| T4.1 加权计算 | P0 | 构造 dimensions 分数，weighted_score = Σ(score×weight)；四舍五入策略文档化 |
| T4.2 **分垂类**阈值边界 | P0 | 配置：beauty pass=0.78；women 0.75；other→default；结果含 `threshold`/`threshold_source=config` |
| T4.2b 阈值优先知识库 | P0 | KB 有 beauty pass=0.80 + 配置 0.78 | 采用 KB；`threshold_source=kb` |
| T4.2c KB 非法回落配置 | P0 | KB payload 缺字段或 degraded≥pass | 落回 config；warning 记录 |
| T4.2d KB 不可用回落 | P1 | search 抛错 | 走 config/default；evaluate 不 fail |
| T4.3 预算偏差 | P1 | 套餐中位价超容差 → budget_alignment 低分 + soft issue |
| T4.4 template 降级 knowledge 封顶 | P1 | 无 hits 时 knowledge_grounding ≤ 0.4 |
| T4.5 未 evaluate 禁止 package | P0 | Agent 直接 package_delivery | 壳层/tool 拒绝（无 gate_pass_token）；无 package 目录写出 |
| T4.6 evaluate fail 禁止 package | P0 | mock gate fail | package 不执行或写失败；pipeline 不得 `succeeded` |
| T4.7 壳层强制 plan 级门禁 + streak | P0 | evaluate 必跑；streak&lt;2 | 不得 package |
| T4.8 媒体后二次门禁（M3） | P2 | include_media=True | 预留用例，MVP 可 skip |
| T4.9 token 签发时机 | P0 | 仅 streak≥2 或 HITL accept | `gate_pass_token` 其它路径不存在或校验失败 |

### T5 — 预算、超时、成本（集成）

| 用例 | 优先级 | 期望 |
|------|--------|------|
| T5.1 迭代上限 | P0 | 循环次数达上限 → failed，reason 含 iterations |
| T5.2 成本熔断 | P0 | 累计 cost > COST_CAP → 停止；已产 plan 落盘；status=failed |
| T5.3 阶段超时 | P1 | mock sleep 超 TIMEOUT_SEC → 壳层 TimeoutError → failed；trace 标记 timeout |
| T5.4 成本记账 | P1 | 各 Skill cost 累加进 pipeline_run；evaluate.llm_review 失败仍有 cost 记录 |

### T6 — 轨迹与可观测

| 用例 | 优先级 | 期望 |
|------|--------|------|
| T6.1 tool_trace 完整 | P0 | 每次 tool：name、latency、input_digest、status、cost |
| T6.2 gate_results 落库 | P0 | passed/score/issues 可查 |
| T6.3 进度契约 | P1 | `build_pipeline_detail` 含 phase、current_skill、last_gate |
| T6.4 失败可回放 | P1 | 仅凭 agent_steps + skill_runs 能重建调用顺序（不要求重建 token 原文） |

### T7 — E2E（全 mock）

| 用例 | 优先级 | 剧本 | 通过标准 |
|------|--------|------|----------|
| T7.1 Happy E2E | P0 | form_state_full → Agent 成功 → gate pass → package | package 目录 + manifest；pipeline `succeeded` |
| T7.2 Fail Closed E2E | P0 | form_state 使 plan 必然 hard fail 且 refine 无效 | **无** package；pipeline `failed`；error 含门禁 id |
| T7.3 Degraded HITL E2E | P0 | score∈[degraded,pass)；缺视频 | 先 `awaiting_degraded_confirm`；**确认后**才 package；status=`degraded`；README 标 gaps |
| T7.4 幂等重跑 | P1 | 同 run 二次执行 force=false | 复用产物；费用不重复；状态一致 |
| T7.5 API 契约 | P0 | POST /api/pipeline... + GET detail | 含 phase/last_gate/hitl 块；鉴权 403 路径不变 |
| T7.6 Resume E2E | P0 | plan 成功后断言可从 images 中游重入 | 不重跑 plan 闭环；最终仍须过门禁 |

### T8 — 降级 HITL（集成，MVP 必测）

| 用例 | 优先级 | 前置 | 期望 |
|------|--------|------|------|
| T8.1 进入待确认 | P0 | gate → degraded_candidate | `status=awaiting_degraded_confirm`；写入 proposal（gaps/top_issues/what_user_gets/misses/expires_at） |
| T8.2 确认后打包 | P0 | T8.1；属主 POST confirm | 恢复 running → package → `degraded`；token 有效；审计含 actor=user |
| T8.3 拒绝 | P0 | T8.1；POST reject | `failed`；error=用户拒绝；**无** package |
| T8.4 **15 分钟**超时默认拒绝 | P0 | `expires_at` 过期（桩时钟 +900s） | `failed`；error 标明超时；**无** package |
| T8.4b 超时前端契约 | P0 | 超时后 GET detail | `hitl.expired=true` + `timeout_reason` 文案字段（供前端固定说明） |
| T8.5 非属主确认 | P0 | 他人 session 的 pipeline | 403；状态不变 |
| T8.6 Agent 无 confirm 工具 | P0 | TOOL_DEFS 审查 + 尝试工具名 confirm | 工具集不含 confirm/reject；壳层 API 才能改状态 |
| T8.7 未确认不得 package | P0 | awaiting 态下直接调 package API/工具 | 拒绝（无 token） |
| T8.8 hard 错误不进 HITL | P0 | 任一 H* 失败 | 直接 failed；不得 awaiting_degraded_confirm |
| T8.9 进度契约 hitl 块 | P0 | awaiting 态 GET detail | 命中 §9.1 字段；倒计时字段存在 |
| T8.10 前端契约字段稳定 | P1 | 同上 | snapshot 字段名与 Spec 一致（可仅测 API JSON，UI 另列） |

---

## 5. 脚本化 LLM Mock 约定

CI 使用**有序脚本**而非自由对话，保证 Agent 行为可断言：

```json
{
  "name": "evaluate_fail_then_refine_pass_twice",
  "steps": [
    {"expect_tool": "decompose_requirements", "return_tool_use": true},
    {"expect_tool": "retrieve_knowledge", "return_tool_use": true},
    {"expect_tool": "compose_plan", "return_tool_use": true},
    {"expect_tool": "validate_plan", "return_tool_use": true},
    {"expect_tool": "render_document", "return_tool_use": true},
    {"expect_tool": "evaluate_delivery", "return_tool_use": true,
     "skill_result_override": {
       "delivery_decision": "fail",
       "passed": false,
       "fixable_count": 1
     }},
    {"expect_tool": "refine_plan", "return_tool_use": true},
    {"expect_tool": "evaluate_delivery", "return_tool_use": true,
     "skill_result_override": {
       "delivery_decision": "pass",
       "passed": true,
       "consecutive_pass_count": 1
     }},
    {"expect_tool": "evaluate_delivery", "return_tool_use": true,
     "skill_result_override": {
       "delivery_decision": "pass",
       "passed": true,
       "consecutive_pass_count": 2
     }},
    {"end_turn": true}
  ]
}
```

规则：

1. 实际调用工具序列 ≠ `expect_tool` → **测试失败**（防 Agent 漂移被 mock 吞掉）
2. `end_turn` 过早（未满足 streak=2 的 pass，或误入 degraded 未走 HITL 桩）→ 测试失败
3. 同一测试内禁止隐式 fallback 到真实网络
4. HITL 用例在 CI 中用「测试桩 confirm/reject」驱动，不启真实前端

---

## 6. Fixture 最低集

| 文件 | 用途 |
|------|------|
| `form_state_minimal.json` | 刚过核心字段门槛 |
| `form_state_full.json` | 10 章节尽量满 |
| `form_state_incomplete.json` | 缺 budget/industry 等 |
| `plan_sample_ok.json` | 可通过 H1–H8 |
| `plan_sample_phantom_device.json` | 无 knowledge_id 且 is_custom=false |
| `plan_sample_bad_budget.json` | 套餐超容差 |
| `gate_result_pass.json` | 回归基准 |
| `gate_result_fail_fixable.json` | refine 驱动 |
| `gate_result_degraded_candidate.json` | HITL 进入条件 |
| `score_thresholds_by_industry.json` | 分垂类阈值（配置层） |
| `knowledge_thresholds_beauty.json` | KB 优先阈值条目 |
| `knowledge_thresholds_invalid.json` | KB 非法回落 |
| `mock_llm_script_pass_twice.json` | 连续 2 次 pass |
| `mock_llm_script_refine_then_pass_twice.json` | refine → pass ×2 |
| `knowledge_hits_mini.json` | retrieve 注入 |
| `mock_llm_script_agent.json` | 多剧本 |

---

## 7. 通过标准（发布门禁）

| 级别 | 条件 |
|------|------|
| **MVP 阻断项（B）** | B1–B11 全绿（见下表） |
| **合并进 main** | CI：`uv run pytest tests/plan_agent tests/delivery_gate tests/hitl tests/pipeline_agent_integration` 全绿；无网络 |
| **灰度切流** | B 全绿 + 连续 3 次 nightly E2E mock + 1 次联调环境真 LLM smoke（可选） |
| **回滚开关** | `PLAN_AGENT_ENABLED=false` 一键回旧 `orchestrator` 串行路径（M5 前必须存在） |

### 阻断项一览

| ID | 用例 | 一句话 |
|----|------|--------|
| B1 | T1.1 | 快乐路径能出 plan+pdf |
| B2 | T1.3 / T1.10 | refine 后必须连续 2 次 pass |
| B3 | T1.4 | 不可修 hard fail → failed，不进 HITL |
| B4 | T3.1/T3.4/T3.5/T3.6/T3.9 | 硬门禁有效 |
| B5 | T4.5/T4.6/T4.9 | 未过门禁/无 token 禁止 package |
| B6 | T4.2 / T4.2b / T4.2c | 分垂类阈值：KB 优先，非法/缺失回落配置 |
| B7 | T5.1/T5.2 | 迭代与成本熔断 |
| B8 | T7.1/T7.2/T7.3 | E2E 成功/失败/降级 HITL 闭环 |
| B9 | T6.1 | 轨迹完整可审计 |
| B10 | T8.1–T8.9 / T8.4b | HITL 全流程：进入/确认/拒绝/**15min 超时+前端说明字段**/鉴权/无 Agent 工具 |
| B11 | T1.8/T7.6 | resume_from 可用且不绕过门禁 |

---

## 8. 与旧管线对照（回归策略）

MVP 合入后，**不删除**旧路径直至 M5 切流完成：

| 对照项 | 方法 |
|--------|------|
| 同 form_state 旧 vs 新 | 结构字段 diff（设备类别集合、套餐档数）；不要求文案逐字一致 |
| 失败率 | 新路径不得高于旧路径 + 5pp（mock 数据集） |
| 平均成本 | 记录对比；超出旧路径 3× 需评审 |
| 门禁 | 旧路径无 gate；新路径 gate 结果单独报表 |

---

## 9. 测试实现约定

1. **无真实密钥**：`LLM_API_KEY` 等缺省时 CI 必须仍可通过
2. **时间可控**：超时用例用假时钟或注入 `timeout_sec=0.01`，禁止 sleep 真 120s
3. **文件系统**：artifact root 使用 `tmp_path`；禁止写 `data/artifacts` 真实目录
4. **确定性**：软分计算禁止依赖 dict 无序遍历；JSON dump `sort_keys=True`
5. **失败信息**：`AssertionError` 消息含 `pipeline_run_id` 与关键 issue id
6. **跳过策略**：M3 预留用例用 `@pytest.mark.m3`，默认不在 MVP 阻断列表

---

## 10. 人工抽检清单（门禁通过后）

门禁保证「结构不出错」，不保证「内容好看」。运营每周抽检：

- [ ] 设备型号是否在知识库可溯源（抽 3 单）
- [ ] 预览图机位与 scene_card 一致（抽 3 单）
- [ ] PDF 中文排版无乱码/截断
- [ ] README 降级说明与实际缺口一致
- [ ] gate 低分单是否进入用户确认而非静默交付
- [ ] 降级确认卡片缺口说明与实际产物一致

---

## 11. 已拍板决策（对应架构 Spec v0.3）

1. **降级 = HITL**，前端必须有确认卡片；无静默降级（用例 T8、T7.3）
2. **阈值分垂类，KB → 配置 → default**（用例 T4.2 / T4.2b / T4.2c）
3. **连续 2 次 evaluate pass** 才可交付；refine 后 streak 清零（用例 T1.3/T1.10）
4. **`resume_from` 进 MVP**（用例 T1.8/T1.9/T7.6）
5. **HITL 确认窗口 15 分钟**；超时默认拒绝；前端必须有超时说明（用例 T8.4 / T8.4b）
6. **`llm_review` 默认全量 ON**；CI mock 可关

仍开放（不阻塞用例编写）：知识库阈值条目的 admin 写入入口属于 M 几；超时后是否允许延长一次（默认不允许）。

---

## 12. 参考

- 架构：[spec-plan-agent.md](./spec-plan-agent.md)
- 旧联调 Spec：[spec-integration-testing.md](./spec-integration-testing.md)
- 现有测试风格：`backend/tests/test_loop.py`、`backend/tests/test_delivery.py`
