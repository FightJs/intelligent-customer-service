# 联调 Spec — 分功能测试与 F1–F5 端到端联调

> 阶段：五项功能**各自完成后、上线前**的测试与联调规范。
>
> 前置 Spec：
> - [F1 知识库](./spec-f1-vector-knowledge-base.md)
> - [F2 方案 PDF](./spec-f2-plan-document-skill.md)
> - [F3 预览图](./spec-f3-preview-images-skill.md)
> - [F4 预览视频](./spec-f4-preview-video-skill.md)
> - [F5 最终交付包](./spec-f5-final-package-skill.md)
>
> 本文约定：**测什么、怎么测、Mock 边界、联调剧本、通过标准**。不新增业务能力。

---

## 1. 目标与范围

### 1.1 目标

1. 每个 Skill / 基础设施可独立验收（单元 + 契约 + 降级）
2. 五段串起来跑通真实/半真实链路，契约不漂移
3. 降级矩阵、幂等、成本、鉴权在联调中被验证
4. CI 可重复执行，不依赖生产密钥；联调环境可选接真实 Milvus / DashScope

### 1.2 范围内

| 层 | 内容 |
|----|------|
| 单元 | 纯函数、校验规则、映射、切块、prompt 组装 |
| 契约 | Pydantic 输入输出、artifact 路径、manifest 字段 |
| 集成 | Skill 内步骤串联（含 mock 外部依赖） |
| 联调 | F1→F2→F3→F4→F5 全链路 + API + 前端展示 |
| 非功能 | 幂等、超时、成本记账、鉴权、并发限制 |

### 1.3 范围外

| 不做 | 说明 |
|------|------|
| 生图/生视频画质主观评分自动化 | 人工抽检清单代替 |
| 压测 / 容量规划 | 另立项 |
| 生产数据迁移演练 | 运维手册另写 |
| 改五份 Spec 中已锁定的产品语义 | 有冲突先改 Spec 再改测例 |

---

## 2. 测试分层与目录

```text
backend/
  tests/
    knowledge/           # F1
      test_schema.py
      test_chunking.py
      test_search_contract.py
      test_ingest_idempotent.py
    pipeline/
      test_plan_document.py      # F2
      test_preview_images.py     # F3
      test_preview_video.py      # F4
      test_final_package.py      # F5
      test_orchestrator.py       # 状态机 / 重试 / 取消
    integration/
      test_e2e_mock.py           # CI 全 mock 端到端
      test_e2e_lite.py           # 可选：Milvus Lite
      test_api_pipeline.py       # HTTP 契约
    fixtures/
      form_state_minimal.json
      form_state_full.json
      form_state_incomplete.json
      plan_sample.json
      knowledge_seed_mini.json
```

**命名**：`test_<模块>_<行为>`；失败信息必须含 `pipeline_run_id` / `skill`。

---

## 3. Mock 与环境边界

| 依赖 | CI（默认） | 本地可选 | 联调环境 |
|------|------------|----------|----------|
| Milvus | mock 客户端 | Lite 文件库 | Standalone Docker |
| Embedding | 固定向量 / hash 伪向量 | BGE 本地或 mock | DashScope 真实 |
| LLM | 固定 JSON fixture | 真实端点（手动） | 真实 |
| WeasyPrint | 真实（系统依赖） | 真实 | 真实 |
| DashScope 生图/生视频 | mock 任务状态机 + 假 PNG/MP4 | 可选真实 | 真实（限额） |
| 文件系统 | tmp_path | `data/artifacts` | 独立 ARTIFACT_ROOT |

### 3.1 Mock 原则

1. **契约优先**：mock 返回结构必须与官方/Spec 输出字段一致（可多字段，不可少字段）
2. **可注入失败**：每个 mock 支持 `fail_mode`（timeout / http_error / empty / partial）
3. **不 mock 校验逻辑**：R1–R7、预算自洽、路径约定必须真实跑
4. **假媒体合法**：CI 用程序生成的最小 PNG（非 0 字节）与可探测的假 MP4 头

### 3.2 DashScope Mock 状态机

```text
submit → PENDING → RUNNING → SUCCEEDED | FAILED
  SUCCEEDED: 返回过期 URL（指向本地 fixture 服务或 file://）
  FAILED: 带可分类 error_code
```

联调真实环境：每日预算上限 + 每 pipeline_run 限 1 次全链路媒体生成。

---

## 4. F1 分功能测试

### 4.1 单元

| 用例 ID | 断言 |
|---------|------|
| F1-U01 | room_size / budget_level 枚举映射覆盖调研表全部选项 |
| F1-U02 | 设备切块=整行；垂类切块 200–500 汉字且含上下文头 |
| F1-U03 | upsert 业务主键幂等：同 brand+name+source 不产生重复行 |
| F1-U04 | Embedding 失败 → 整批回滚，库内无半截数据 |

### 4.2 契约 / 集成

| 用例 ID | 断言 |
|---------|------|
| F1-C01 | `hybrid_search` 返回 `KnowledgeHit` 必填字段 |
| F1-C02 | 过滤表达式：industry/room_size/budget 生效（mock 客户端记录 filter） |
| F1-C03 | Milvus 不可达 → 空列表 + degraded，不抛未捕获异常 |
| F1-C04 | BM25-only 降级路径可调用 |

### 4.3 可选真库（本地/联调）

| 用例 ID | 断言 |
|---------|------|
| F1-R01 | seed 后中文 query「女装 20㎡ 三点布光」top-5 含相关设备或方案 |
| F1-R02 | 分区键 industry 过滤减少无关垂类命中 |

**F1 通过门禁**：U+C 全绿；R 在联调环境至少抽 3 条 query 人工确认相关。

---

## 5. F2 分功能测试

### 5.1 单元

| 用例 ID | 断言 |
|---------|------|
| F2-U01 | `form_state` → `RequirementBrief`：区间值不被擅自改档 |
| F2-U02 | 缺必填且 `allow_incomplete=false` → failed |
| F2-U03 | 检索意图 JSON schema 校验（3–6 条、含 collection） |
| F2-U04 | PlanDraft pydantic 校验：equipment_list / package_tiers / setup_steps |
| F2-U05 | 预算自洽：超出 ±10% 产生 warning（flexible 放宽） |
| F2-U06 | knowledge_id 不在命中集 → 剔除或 is_custom（按 Spec R 策略） |
| F2-U07 | scene_card 必填字段齐全 |

### 5.2 集成（mock LLM + mock 检索）

| 用例 ID | 断言 |
|---------|------|
| F2-I01 | 端到端产出 `plan.json` + `plan.pdf` 路径存在 |
| F2-I02 | PDF 可读、页数 ≥1、文件头 `%PDF` |
| F2-I03 | WeasyPrint 失败 → 降级 docx，status=degraded |
| F2-I04 | LLM 失败重试 1 次后仍失败 → failed |
| F2-I05 | 同 pipeline_run_id 幂等：二次调用复用产物、不双计费 |

### 5.3 联调抽检

| 用例 ID | 断言 |
|---------|------|
| F2-H01 | 真实 form_state（女装/美妆/珠宝 至少 2 垂类）PDF 中文可读、无乱码 |
| F2-H02 | 设备清单型号在知识库可查或标注定制 |
| F2-H03 | 三档套餐金额与调研预算同量级 |

---

## 6. F3 分功能测试

### 6.1 单元

| 用例 ID | 断言 |
|---------|------|
| F3-U01 | SceneCard → 三机位 prompt 含公共锁与角度差异段 |
| F3-U02 | forbidden 进入 prompt 或过滤说明 |
| F3-U03 | 缺 front 时选图顺序 left → rear |
| F3-U04 | 文件名/角度标签与 Spec 路径约定一致 |

### 6.2 集成（mock 生图）

| 用例 ID | 断言 |
|---------|------|
| F3-I01 | 组图成功 → 3 文件 + manifest + seed |
| F3-I02 | 组图失败 → 串行同 seed 3 次成功 |
| F3-I03 | 仅 2 张成功 → status=partial，images 长度=2 |
| F3-I04 | 全失败 → failed，无空文件残留 |
| F3-I05 | 损坏图（0 字节）被丢弃并重试 |
| F3-I06 | 幂等：已有 3 张成功则不再提交任务 |
| F3-I07 | sha256 / width / height / cost 写入输出 |

### 6.3 联调抽检（人工）

| 用例 ID | 断言 |
|---------|------|
| F3-H01 | 三张图像同一房间（家具/色板连贯） |
| F3-H02 | 无乱码文字/水印 |
| F3-H03 | 角度与 front/left/rear 语义大致相符 |

---

## 7. F4 分功能测试

### 7.1 单元

| 用例 ID | 断言 |
|---------|------|
| F4-U01 | duration 校验 5–15；resolution 枚举 |
| F4-U02 | 无可用图 → 输入层 failed，不调外部 API |
| F4-U03 | motion prompt 含 scene_card 风格词与 forbidden |

### 7.2 集成（mock 生视频）

| 用例 ID | 断言 |
|---------|------|
| F4-I01 | 成功 → mp4 路径 + meta（source_image、duration、model、cost） |
| F4-I02 | 1080P 失败 → 自动降 720P 成功一次 |
| F4-I03 | 主模型失败 → 备选模型一次 |
| F4-I04 | 超时 → failed，可 retry |
| F4-I05 | 0 字节文件视为失败并重试 |
| F4-I06 | 幂等：已有成功 mp4 则复用 |

### 7.3 联调抽检

| 用例 ID | 断言 |
|---------|------|
| F4-H01 | mp4 可播放，时长误差 ≤ +2s |
| F4-H02 | 首帧与 F3 front 场景连贯 |

---

## 8. F5 分功能测试

### 8.1 单元（规则引擎，无 LLM）

| 用例 ID | 断言 |
|---------|------|
| F5-U01 | R1：无效 knowledge_id 处理符合策略（剔除/阻断） |
| F5-U02 | R2：预算越界产生 warning |
| F5-U03 | R3：缺 rear → gaps 含 `missing_angle:rear` |
| F5-U04 | R6：README 生成禁止声称不存在的文件 |
| F5-U05 | manifest 字段完整；file sha256 与磁盘一致 |
| F5-U06 | 硬件字段未被改写（对比 plan.json 输入输出） |

### 8.2 集成（mock LLM 润色）

| 用例 ID | 断言 |
|---------|------|
| F5-I01 | 全成功 → ready，package 目录 + zip |
| F5-I02 | 缺视频 → ready_with_warnings，zip 内无 video/ |
| F5-I03 | 缺图 partial → ready_with_warnings |
| F5-I04 | F2 failed → F5 failed，不产出空包 |
| F5-I05 | 仅 PDF → ready_with_warnings（最低交付线） |
| F5-I06 | 重跑 F5 复用媒体，重新生成 README/manifest |

### 8.3 降级矩阵（表驱动，必须全覆盖）

| # | F2 | F3 | F4 | 期望 F5 status | 包内最低内容 |
|---|----|----|----|----------------|--------------|
| M1 | ok | ok | ok | ready 或 ready_with_warnings | 全量 |
| M2 | ok | partial | ok | ready_with_warnings | 缺机位标注 |
| M3 | ok | ok | failed | ready_with_warnings | 无视频说明 |
| M4 | ok | failed | failed | ready_with_warnings | 仅 PDF |
| M5 | failed | * | * | failed | 无包 |
| M6 | degraded | ok | ok | ready_with_warnings | PDF 标注未接知识库 |

用例 ID：`F5-M01` … `F5-M06`。

---

## 9. 编排与 API 联调

### 9.1 状态机

| 用例 ID | 断言 |
|---------|------|
| ORCH-01 | 订单成功后创建 pipeline_run，current_skill 依次推进 |
| ORCH-02 | skill 失败：可 `retry` 该 skill，从失败点继续，不重跑已成功媒体 |
| ORCH-03 | `cancel` 仅 pending/running 允许；取消后不可 download 假成功包 |
| ORCH-04 | 每用户同时仅 1 个 running pipeline_run |
| ORCH-05 | 超时：plan≤120s / images≤180s / video≤300s / package≤60s |
| ORCH-06 | skill_runs 记录 attempt、cost、error；总成本可汇总 |
| ORCH-07 | SSE/轮询事件顺序：pending → per-skill running → terminal |

### 9.2 HTTP 契约

| Method | Path | 关键断言 |
|--------|------|----------|
| POST | `/api/pipeline` | Guest 403；重复启动策略符合约定 |
| GET | `/api/pipeline/{id}` | 非 owner/admin 403；字段与前端 PlanDetail 对齐 |
| POST | `/api/pipeline/{id}/retry` | 仅 failed skill；body 含 skill 名 |
| POST | `/api/pipeline/{id}/cancel` | 状态门禁 |
| GET | `/api/pipeline/{id}/package` | 仅 ready*；zip Content-Type |
| GET | `/api/pipeline/{id}/artifacts/{kind}` | 鉴权；禁止目录穿越 |

前端 `/plans` 联调：

| 用例 ID | 断言 |
|---------|------|
| UI-01 | 四 skill 进度点与后端一致 |
| UI-02 | 图廊灯箱；partial 缺失位 Warning |
| UI-03 | 视频区 failed 文案 + 有权限时重试 |
| UI-04 | PDF 摘要与下载 |
| UI-05 | Guest 可看列表、无生成/重试入口 |

---

## 10. 端到端联调剧本

### 10.1 剧本 A — CI 全 Mock（必过，每次 PR）

```text
Given 注入 fixture form_state_full（女装 20㎡ 中高预算）
And   mock Milvus 命中 2 设备 + 1 方案 + 1 垂类
And   mock LLM 返回合法 PlanDraft
And   mock 生图 3 成功、生视频 1 成功
When  POST /api/pipeline
Then  最终 status=ready 或 ready_with_warnings
And   package 内含 plan.pdf、3 图、preview.mp4、README、manifest
And   无未捕获异常；skill_runs 成本字段 ≥0
```

### 10.2 剧本 B — 半真实知识库（联调环境必过）

```text
Given Milvus Standalone + seed 真数据
And   Embedding 真实或本地 BGE
And   LLM 真实；生图/生视频 mock
When  用 2 个垂类 form_state 跑 F2
Then  检索命中相关垂类；plan.json knowledge_refs 非空
And   预算 warning 合理
```

### 10.3 剧本 C — 真实媒体小流量（联调，人工审批）

```text
Given 剧本 B 通过
And   每日媒体预算与 run 限额已配置
When  quality=draft，resolution=720P，跑完整 F1–F5
Then  3 图人工抽检连贯；mp4 可播放
And   成本记入 skill_runs，未超限
```

### 10.4 剧本 D — 故障注入（必过）

| 子剧本 | 注入 | 期望 |
|--------|------|------|
| D1 | F1 不可达 | F2 degraded 或模板方案；链路不断 |
| D2 | 生图全失败 | F5 ready_with_warnings 仅 PDF |
| D3 | 视频超时 | 同 D2 语义 + 无 video |
| D4 | LLM 返回非法 JSON | F2 重试后 failed；可 retry |
| D5 | 磁盘满/写失败 | 明确 error，无半截 zip |
| D6 | 重复提交订单 | 不产生两个 concurrent 恶意烧钱 run（按约定） |

### 10.5 剧本 E — 幂等与重试（必过）

```text
1. 全 mock 成功一次 → 记 cost C1、文件 hash H1
2. 重复触发 pipeline（同 session）→ 复用或按产品策略拒绝
3. 仅 retry F3 → 仅媒体可能变，plan.json 不变
4. retry F5 → README/manifest 更新，媒体 hash 保持（未 force）
```

---

## 11. 非功能与安全检查单

| 类别 | 检查 |
|------|------|
| 鉴权 | Guest 禁启动；跨用户 403；artifact 无直出未签名外链 |
| 路径安全 | artifact 路径规范化，拒绝 `..` |
| 密钥 | 日志/错误栈不打印 API Key |
| 成本 | 每次外部调用有 cost；日累计可查；超限拒绝新 run |
| 幂等 | 外部任务有 client token / 本地缓存键 |
| 可观测 | pipeline_run_id 贯穿日志 |
| 数据 | 用户上传图不进知识库；电话等 PII 不进 prompt 除非必要 |

---

## 12. 通过门禁（Definition of Done）

### 12.1 单功能完成（合并进 main 前）

- [ ] 该 Fx 的 Unit + Integration 用例在 CI 全绿
- [ ] 失败路径用例覆盖（见各节 fail 表）
- [ ] 契约测试锁定输入输出字段
- [ ] 不依赖真实付费 API

### 12.2 五功能联调完成（可发布预发）

- [ ] 剧本 A、D、E 在 CI/预发自动或脚本化跑通
- [ ] 剧本 B 在联调环境跑通 2 垂类
- [ ] 剧本 C 至少 1 次人工抽检通过（图+视频）
- [ ] 降级矩阵 M1–M6 全覆盖
- [ ] API 鉴权与 UI-01–05 通过
- [ ] 成本与超时配置生效
- [ ] 五份功能 Spec 验收清单全部勾选

### 12.3 发布阻断项（一票否决）

| ID | 阻断条件 |
|----|----------|
| B1 | 剧本 A 失败 |
| B2 | 降级矩阵 M5（F2 失败）仍产出空/假包 |
| B3 | 跨用户可下载他人 artifact |
| B4 | plan.json 硬件被 F5 改写 |
| B5 | CI 需真实 API Key 才能绿 |

---

## 13. 联调环境与数据

| 项 | 约定 |
|----|------|
| Compose | `milvus` + `minio` + `etcd` + `backend` |
| 种子 | `knowledge_seed_mini.json`：每测试垂类 ≥5 设备 + 1 方案 + 2 知识块 |
| Fixture 用户 | 正式用户 / Guest / 管理员 各一 |
| Artifact 根 | 联调独立目录，可 `make pipeline-reset` |
| 密钥 | `.env.local`，不入库；CI 无密钥 |

---

## 14. 建议执行顺序

```text
Phase 1  各 Fx Unit 填齐 → 各自 PR 合并
Phase 2  各 Fx Integration + mock 契约
Phase 3  ORCH + API + UI 联调
Phase 4  剧本 A/D/E 进 CI
Phase 5  联调环境剧本 B
Phase 6  审批后剧本 C
Phase 7  门禁清单签字 → 预发/上线
```

---

## 15. 开放问题

1. 剧本 C 是否允许生产账号？建议专用联调子账号 + 日限额。
2. 图/视频人工抽检是否需要评分表（连贯性 1–5）？建议简单表存 artifacts 外。
3. M5（F2 失败）产品是否允许「空包+错误说明」？当前 Spec 为不打包，若改需同步 F5 Spec。
