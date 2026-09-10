# F2 Spec — 需求拆解 + RAG + 方案 PDF Skill

> 管线阶段：`plan_document`。输入对话采集的 `form_state`，输出结构化 `plan.json` + 中文方案 PDF。
>
> 关联：
> - 知识库：`spec-f1-vector-knowledge-base.md`
> - 需求字段：`backend/survey/schema_def.py`
> - 现有交付渲染：`backend/delivery/render_data.py`

---

## 1. 目标与边界

### 1.1 目标

在订单提交后，将调研表 10 章节需求：

1. 规范化为 `RequirementBrief`
2. LLM 拆解为检索意图
3. 从 F1 三 collection 检索垂类知识
4. 组合成可审计的 `PlanDraft`（设备清单 / 三档套餐 / 搭建步骤）
5. 渲染为中文 PDF

**`plan.json` 是 F3/F4/F5 的唯一方案真相源。**

### 1.2 明确不做

| 不做 | 原因 |
|------|------|
| 实时电商比价 / 下链 | 价格时效与合规 |
| 改写用户已确认的需求字段 | 需求以 form_state 为准 |
| 法律合同级报价单 | 价格为区间参考，非成交价 |
| 在方案中虚构不存在的设备型号 | 必须可追溯 knowledge_id 或标注定制 |

---

## 2. 选型

| 项 | 选型 | 理由 |
|----|------|------|
| LLM | 现有 Anthropic 兼容端点（DeepSeek） | 复用 `agent/llm.py` |
| 检索 | F1 `hybrid_search` + rerank | |
| PDF | **jinja2 HTML + WeasyPrint** | 中文排版、表格、分页优于 reportlab |
| 降级文档 | python-docx Word | WeasyPrint 系统依赖失败时 |
| 中文字体 | 思源黑体 / 阿里普惠体 `@font-face` 内嵌 | 避免部署机缺字体 |

---

## 3. 输入契约

```python
class PlanDocumentInput(BaseModel):
    skill: Literal['plan_document'] = 'plan_document'
    pipeline_run_id: str
    session_id: str
    form_state: dict              # StudioFormState 序列化
    delivery_id: int | None = None
    allow_incomplete: bool = False
```

### 3.1 关键检索键映射

| 调研表字段 | 用途 |
|------------|------|
| `industry.category` / `subcategory` | 垂类过滤 + query |
| `venue.area` / `venue.size` | room_size 分档 |
| `budget.total` / `equipment` / `decor` | budget_level |
| `goal.core` | 方案深度（全新/优化/只调参） |
| `product.main` / `keywords` | 检索 query、风格词 |
| `equipment.inventory` | 已有设备，从推荐中扣减 |
| `benchmark.*` / `product.style_ref*` | 风格倾向 |
| `host.count` / `movement` | 机位与空间说明 |
| `goal.focus` / `deadline` | 优先级与交付节奏 |

必填核心字段缺失且 `allow_incomplete=False` → 直接 `failed`。

---

## 4. 处理流水线

```text
1. Normalize   form_state → RequirementBrief（结构化，保留原始区间）
2. Decompose   LLM 输出 3–6 条检索意图（query + collection 目标 + 过滤条件）
3. Retrieve    对 equipment_specs / setup_schemes / vertical_knowledge 分别 hybrid_search
4. Compose     LLM 结合 RequirementBrief + KnowledgeHits 生成 PlanDraft JSON
5. Validate    硬校验（见 §6）
6. Render      jinja2 → HTML → WeasyPrint PDF
7. Persist     artifacts：plan.json + plan.pdf；写 skill_runs
```

### 4.1 RequirementBrief（规范化摘要）

```json
{
  "brand": "云裳",
  "industry": "women",
  "subcategory": "高端香云纱女装",
  "price_band": "high",
  "positioning": "mid-high",
  "live_type": "brand",
  "room_size": "medium",
  "area_band": "20-30",
  "budget_total": "3-5w",
  "budget_equip": "1-2w",
  "budget_decor": "5k-1w",
  "budget_flex": "some",
  "goal_core": "new",
  "goal_focus": ["premium-look", "product-quality"],
  "product_main": "连衣裙",
  "product_keywords": ["国风", "高端", "雅致"],
  "host_count": "1",
  "host_movement": "occasional",
  "existing_equipment": [{"type": "相机", "model": "Sony A7M4", "qty": 1}],
  "window": "coverable",
  "window_pos": "right",
  "renovation": "minor",
  "deadline": "2w",
  "completeness": 0.86
}
```

### 4.2 检索意图示例

```json
[
  {"collection": "setup_schemes", "query": "女装 20㎡ 中高客单 品牌自播 搭建方案", "filters": {"industry": "women", "room_size": "medium"}},
  {"collection": "equipment_specs", "query": "三点布光 COB 常亮灯 服装类", "filters": {"category": "灯光", "industry": ["women", "all"]}},
  {"collection": "vertical_knowledge", "query": "女装直播间 背景层次 商品质感", "filters": {"industry": "women", "scene": "背景"}}
]
```

---

## 5. PlanDraft（中间真相源）

```json
{
  "meta": {
    "brand": "云裳",
    "industry": "women",
    "room_size": "medium",
    "budget_total": "3-5w",
    "generated_at": "2026-01-01T00:00:00Z",
    "pipeline_run_id": "uuid",
    "knowledge_refs": [{"collection": "equipment_specs", "id": 1001}],
    "completeness": 0.86,
    "status_flags": []
  },
  "summary": "一句话方案定位",
  "layout": {
    "zones": [{"name": "主播区", "notes": "..."}],
    "lighting_plan": "三点布光…",
    "camera_plan": "主机位…",
    "background_plan": "…"
  },
  "equipment_list": [
    {
      "knowledge_id": 1001,
      "category": "灯光",
      "name": "爱图仕 300D II",
      "model": "300D II",
      "brand": "Aputure",
      "qty": 2,
      "unit_price_band": "high",
      "reason": "适配 20㎡ 中高客单女装",
      "is_custom": false
    }
  ],
  "package_tiers": [
    {"tier": "性价比", "total_range": "1.2-1.6w", "items": [{"name": "...", "qty": 1}]},
    {"tier": "进阶", "total_range": "2.2-2.8w", "items": []},
    {"tier": "高配", "total_range": "3.5-4.2w", "items": []}
  ],
  "setup_steps": ["第1步：…", "第2步：…"],
  "risks": ["窗户在主播右侧需遮光…"],
  "scene_card": {
    "room_size_band": "medium",
    "style_keywords": ["国风", "高端", "雅致"],
    "color_palette": ["#f5f0e8", "#2c2c2c", "#c4a574"],
    "color_temp": "4000K",
    "furniture": ["主播桌", "展示架"],
    "lighting_fixtures": ["COB主灯×2", "柔光箱×2", "发丝灯×1"],
    "product_category": "女装",
    "camera_angles": ["front", "left", "rear"],
    "forbidden": ["文字水印", "品牌logo"]
  }
}
```

> `scene_card` 专供 F3 生图使用，由 F2 一次生成，F3/F4 禁止重新发挥。

---

## 6. 硬校验规则

| 规则 | 失败行为 |
|------|----------|
| `equipment_list` 项必须有 `knowledge_id` 或 `is_custom=true` | 拒绝该项并 warning |
| 套餐 `total_range` 须落在 `budget_total` ±10%（`budget_flex=flexible` 时放宽到 ±25%） | warning + 标注 |
| 三档套餐缺一不可（用户预算极低时可两档） | 降级两档 + warning |
| `setup_steps` ≥ 3 条 | failed |
| `summary` / `layout` 非空 | failed |
| JSON schema 校验（pydantic） | failed |

---

## 7. PDF 结构

| 章节 | 内容 |
|------|------|
| 封面 | 品牌名、生成日期、版本 |
| 需求摘要 | RequirementBrief 关键项 |
| 空间与布局 | zones / 布光 / 机位 / 背景 |
| 设备清单表 | 类别/型号/数量/理由 |
| 三档套餐 | 性价比 / 进阶 / 高配 |
| 搭建步骤 | 分步 |
| 风险与提示 | 窗户、装修权限、预算弹性 |
| 附录（可选） | knowledge_refs 审计 |

模板：`backend/delivery/templates/plan.html`  
字体：内嵌，不依赖系统字体。

---

## 8. 输出契约

```python
class PlanDocumentOutput(BaseModel):
    skill: Literal['plan_document']
    status: Literal['succeeded', 'degraded', 'failed']
    plan_json_path: str
    pdf_path: str | None
    requirement_brief: dict
    knowledge_hits: list[dict]
    scene_card: dict
    cost_cny: float
    warnings: list[str]
    error: str | None = None
```

产物路径：

```text
data/artifacts/{pipeline_run_id}/docs/plan.json
data/artifacts/{pipeline_run_id}/docs/plan.pdf
```

---

## 9. 降级策略

| 场景 | 行为 |
|------|------|
| Milvus 不可用 | 使用预置「通用模板方案」按行业+面积匹配；PDF 标注「未接入知识库」；`status=degraded` |
| Embedding 失败 | F1 BM25-only 回退，继续生成 |
| LLM 失败 | 重试 1 次；仍失败 → failed（可人工重试） |
| WeasyPrint 失败 | 降级输出 Word（现有 python-docx）；pdf_path 为 None |
| 需求不完整 | `allow_incomplete=true` 时继续，PDF 顶部标注「信息不完整」 |

---

## 10. 成本与时延

| 项 | 估算 |
|----|------|
| LLM（拆解+组合，~8k token） | ~0.05–0.15 元 |
| Embedding 检索 | 忽略不计（或按 DashScope 计） |
| WeasyPrint | CPU，本地 |
| 端到端时延 | 30–90s |

超时：≤ 120s。

---

## 11. 幂等

- 同一 `pipeline_run_id` 已有成功 `plan.json` → 直接复用，不重复计费
- 重试：允许 `POST /api/pipeline/{id}/retry` 指定 skill
- 强制重生成：admin 参数 `force=true`（记审计）

---

## 12. 验收清单

- [ ] 从真实 form_state 端到端产出 plan.json + 中文 PDF
- [ ] PDF 含设备清单 + 三档套餐 + 搭建步骤 + 风险提示
- [ ] equipment_list 可追溯 knowledge_id
- [ ] 套餐金额与用户预算自洽（或明确 warning）
- [ ] scene_card 字段完整，可供 F3 使用
- [ ] Milvus 不可用时 degraded 可交付
- [ ] 单测 mock LLM + mock 检索进 CI

---

## 13. 开放问题

1. 三档套餐的命名是否统一为「性价比/进阶/高配」？产品可改。
2. 已有设备是「从清单剔除」还是「保留在清单并标注已有」？建议后者。
3. PDF 是否要插入 F3 预览图？当前不插，图在 F5 包内独立文件。
