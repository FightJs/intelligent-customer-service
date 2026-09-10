# F5 Spec — 汇总完善与最终交付 Skill

> 管线阶段：`final_package`。交叉校验 F2/F3/F4 产物，互完善说明文案，打包最终交付物。
>
> 关联：
> - F2 方案 PDF：`spec-f2-plan-document-skill.md`
> - F3 预览图：`spec-f3-preview-images-skill.md`
> - F4 预览视频：`spec-f4-preview-video-skill.md`

---

## 1. 目标与边界

### 1.1 目标

1. **交叉校验**：设备清单 vs 图片/视频存在性 vs 原始需求预算
2. **互完善**：统一话术、标注缺失、写清如何看图选套餐
3. **打包**：生成可下载交付目录（+ 可选 zip）与 manifest

### 1.2 明确不做

| 不做 | 原因 |
|------|------|
| 重新生成图/视频 | 失败重试属 F3/F4 |
| 擅自增删设备型号/改价格区间 | plan.json 为真相源 |
| 伪造未生成成功的媒体 | 宁缺勿假 |
| 多方案 A/B 对比包 | 后期 |
| 合并进现有 Word 确认书 | 保持独立 zip；开放问题 |

---

## 2. 选型

| 项 | 选型 | 说明 |
|----|------|------|
| LLM | 现有 Anthropic 兼容端点 | 仅写交付说明与差异标注 |
| 打包 | Python `zipfile` + 目录落盘 | |
| 校验 | 规则引擎（确定性）+ LLM 润色 | 规则优先，LLM 不改硬件数据 |
| hash | sha256 | manifest 完整性 |

---

## 3. 输入契约

```python
class FinalPackageInput(BaseModel):
    skill: Literal['final_package'] = 'final_package'
    pipeline_run_id: str
    session_id: str
    form_state: dict
    plan_output: dict          # F2 PlanDocumentOutput
    images_output: dict        # F3 PreviewImagesOutput
    video_output: dict         # F4 PreviewVideoOutput
```

上游任一 `failed` 不阻塞 F5：按 **降级包** 继续。

---

## 4. 最终交付物清单

| 产物 | 最低要求 | 路径 |
|------|----------|------|
| 360 预览图 | **≥3 张**；partial ≥1 并标注缺失机位 | `images/preview_*.png` |
| 预览视频 | 1 条 5–15s mp4；失败则省略并在 README 说明 | `video/preview.mp4` |
| 方案 PDF | 设备清单 + 套餐 + 搭建规划 | `docs/plan.pdf` |
| 方案 JSON | 机器可读真相源 | `docs/plan.json` |
| 交付说明 | 中文 README | `README.md` |
| 设备 Excel（可选） | 复用 openpyxl | `docs/equipment.xlsx` |
| Manifest | 文件列表 + sha256 + 各 skill 状态 | `manifest.json` |

目录根：

```text
data/artifacts/{pipeline_run_id}/package/
```

---

## 5. 交叉校验规则（硬约束）

```text
R1 plan.equipment_list 每项 knowledge_id 必须在 F1 存在，或 is_custom=true
R2 套餐 total_range 与用户 budget_total 自洽（±10% / flexible ±25%），否则 warning
R3 图片张数、角度标签与 scene_card.camera_angles 对齐；缺失写入 manifest.gaps
R4 视频存在性与 source_image 可追溯
R5 所有纳入包的文件必须 sha256 入 manifest
R6 禁止在 README/说明中声称不存在的媒体文件
R7 form_state 必填核心字段若 incomplete，README 顶部显著标注
```

校验失败分级：

| 级别 | 处理 |
|------|------|
| error（R1/R5/R6） | 阻断打包 → `failed`（或 R1 可降级为去掉该项 + warning，待产品确认） |
| warning（R2/R3 partial/R7） | 继续打包，`status=ready_with_warnings` |

---

## 6. LLM 汇总职责边界

### 6.1 允许

- 撰写 `README.md`：如何看三机位图、如何选套餐、下一步联系/实施建议
- 统一全文话术与品牌名称
- 指出「图偏冷 vs 方案写暖光」类风格差异，**建议以 plan.json 为准**
- 生成一页「交付摘要」放 PDF 末页（可选，需重新渲染则仅追加 markdown 附件）

### 6.2 禁止

- 增删设备型号、改数量、改价格区间
- 把 partial 写成「完整三机位」
- 编造未生成的视频/图
- 修改 plan.json 硬件字段（最多输出 `plan_patch_notes` 给 F5 展示，不回写）

### 6.3 Prompt 输入

- RequirementBrief + plan.json（截断）+ 各 skill status + gaps 列表
- 输出：`README.md` 文本 + `warnings_extended: list[str]`

---

## 7. 输出契约

```python
class FinalPackageOutput(BaseModel):
    skill: Literal['final_package']
    status: Literal['ready', 'ready_with_warnings', 'failed']
    package_dir: str | None
    zip_path: str | None
    manifest: dict
    delivery_notes_md: str
    total_cost_cny: float
    warnings: list[str]
    error: str | None = None
```

### 7.1 manifest 结构

```json
{
  "pipeline_run_id": "uuid",
  "session_id": "…",
  "generated_at": "ISO-8601",
  "skills": {
    "plan_document": {"status": "succeeded", "cost_cny": 0.1},
    "preview_images": {"status": "partial", "cost_cny": 1.2, "angles": ["front", "left"]},
    "preview_video": {"status": "failed", "cost_cny": 0},
    "final_package": {"status": "ready_with_warnings", "cost_cny": 0.02}
  },
  "files": [
    {"path": "docs/plan.pdf", "kind": "plan_pdf", "sha256": "…", "bytes": 123456},
    {"path": "images/preview_front.png", "kind": "image", "sha256": "…", "bytes": 2345678}
  ],
  "gaps": ["missing_angle:rear", "video_failed"],
  "total_cost_cny": 1.32,
  "warnings": ["套餐接近预算上限"]
}
```

---

## 8. 降级包矩阵

| F2 | F3 | F4 | F5 状态 | 交付内容 |
|----|----|----|---------|----------|
| ok | ok | ok | ready / ready_with_warnings | 完整包 |
| ok | partial | ok | ready_with_warnings | 缺机位标注 |
| ok | ok | failed | ready_with_warnings | 无视频 + 说明 |
| ok | failed | failed | ready_with_warnings | 仅 PDF 方案包 |
| failed | * | * | failed | 不打包；pipeline=failed |
| degraded | ok | ok | ready_with_warnings | PDF 标注未接知识库 |

产品验收最低线：**有 plan.pdf 即可交付**；媒体为增强项。

---

## 9. 幂等与重试

- 上游 skill 重试成功后，可单独重跑 F5（`retry skill=final_package`）
- 重跑重新生成 README + manifest + zip；复用已有媒体文件
- 不重复调用生图/生视频

---

## 10. 成本与时延

| 项 | 估算 |
|----|------|
| LLM 说明撰写 | ~0.01–0.05 元 |
| 打包/hash | CPU |
| 时延 | ≤60s |

---

## 11. 与现有系统衔接

| 现有 | 关系 |
|------|------|
| `/api/generate/{md,excel,word}` | 保留，不进智能包 |
| `deliveries` | 需求确认；pipeline 产物挂 artifacts |
| 前端 `/plans` | 展示 package 下载与各 skill 状态（已有页面契约） |
| Admin | 可查询 pipeline_runs / skill_runs 成本 |

下载：`GET /api/pipeline/{id}/package` 返回 zip 或按文件鉴权下载；不直出外部存储临时 URL。

---

## 12. 验收清单

- [ ] 完整上游时产出 package 目录 + zip + manifest
- [ ] manifest 含全部文件 sha256 与各 skill 状态
- [ ] 缺图/缺视频时包仍可交付且 README 明确说明
- [ ] README 不包含虚假媒体声称
- [ ] plan.json 未被 F5 改写硬件字段
- [ ] 成本汇总写入 skill_runs
- [ ] mock 上游输出的单测进 CI

---

## 13. 开放问题

1. R1 失败是阻断还是剔除该项？建议：剔除 + warning，保证可交付。
2. zip 是否默认生成？建议默认生成，便于微信发送。
3. 交付包保留天数与清理策略？建议与 deliveries 对齐（如 90 天）。
