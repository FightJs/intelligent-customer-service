# 智能交付管线 — 分阶段 Spec 索引

本目录将总览中的 F1–F5 拆成可独立评审、独立落地的 Spec，并附联调测试规范。

| 阶段 | Skill 名 | Spec | 一句话 |
|------|----------|------|--------|
| F1 | （基础设施） | [spec-f1-vector-knowledge-base.md](./spec-f1-vector-knowledge-base.md) | Qdrant 三 Collection + 混合检索知识库 |
| F2 | `plan_document` | [spec-f2-plan-document-skill.md](./spec-f2-plan-document-skill.md) | 需求拆解 + RAG → plan.json + 方案 PDF |
| F3 | `preview_images` | [spec-f3-preview-images-skill.md](./spec-f3-preview-images-skill.md) | 三机位 360 预览图 |
| F4 | `preview_video` | [spec-f4-preview-video-skill.md](./spec-f4-preview-video-skill.md) | 首帧图生视频预览 |
| F5 | `final_package` | [spec-f5-final-package-skill.md](./spec-f5-final-package-skill.md) | 交叉校验 + 说明 + 最终交付包 |
| 联调 | （测试） | [spec-integration-testing.md](./spec-integration-testing.md) | 分功能测试 + E2E 剧本 + 发布门禁 |
| **Agent 化** | `plan_agent` + skills | [spec-plan-agent.md](./spec-plan-agent.md) | Plan Agent + Skill 工具集 + Delivery Evaluator 门禁 |
| **Agent MVP 测** | （测试） | [spec-plan-agent-mvp-testing.md](./spec-plan-agent-mvp-testing.md) | M1/M2 用例、Mock 约定、发布阻断项 |

## 数据流

```text
form_state（调研表）
    │
    ▼
F1 知识库 ──hybrid_search──┐
    │                      │
    ▼                      │
F2 plan.json + plan.pdf ◄──┘
    │
    ├──────────────► F3 preview_*.png（3 机位）
    │                     │
    └──────────────► F4 preview.mp4（i2v）
                          │
                          ▼
                     F5 package/ + manifest + zip
```

### Agent 化目标态（MVP：M1+M2）

```text
form_state
    │
    ▼
Plan Agent（tool-use 循环）
    decompose → retrieve → compose → validate ⇄ refine → render
    │
    ▼
evaluate_delivery（硬门禁 H1–H8 + 分垂类软分阈值）
    │ decision=pass 且连续 2 次 → package
    │ decision=degraded_candidate → HITL 用户确认 → package | failed
    │ decision=fail → refine 或 failed
    ▼
preview_* → evaluate(include_media) → package（需 gate_pass_token）
```

详见 [spec-plan-agent.md](./spec-plan-agent.md)（v0.3：HITL 15 分钟确认、阈值 KB→config、llm_review 全开、连续 2 次 pass、resume_from）。未过门禁禁止打包（壳层强制）。

## 统一约定

- **真相源**：`plan.json` 是 F3/F4/F5 的唯一方案真相源，禁止各自发挥设备清单。
- **Skill 契约**：显式 Pydantic 输入/输出；幂等；写 `skill_runs` 成本与状态。
- **CI**：不依赖真实 Qdrant / DashScope；mock + 契约测试。
- **联调与发布门禁**：见 [spec-integration-testing.md](./spec-integration-testing.md)（剧本 A–E、降级矩阵 M1–M6、阻断项 B1–B5）。
- **本阶段**：仅调研与规范，**不写业务代码**。

## 总览文档

合并版架构与阶段划分见：[`../spec-studio-delivery-pipeline.md`](../spec-studio-delivery-pipeline.md)
