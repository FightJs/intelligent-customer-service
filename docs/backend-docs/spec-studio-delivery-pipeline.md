# 直播间智能交付管线 Spec

> 对应需求：在现有对话采集链路之后，新增 5 个 Agent 能力，形成「知识库 → 方案 PDF → 预览图 → 预览视频 → 最终交付包」完整管线。
>
> 本文是**调研与规范文档**，约定技术选型、模块边界、数据契约与实施阶段，**本阶段不编写业务代码**。
>
> 关联文档：
> - **分阶段详细 Spec（F1–F5）**：`docs/backend-docs/pipeline/`
> - 现有对话链路：`docs/backend-docs/spec-ai-streaming-output.md`
> - 表单单一真相源：`backend/survey/schema_def.py`
> - 交付物生成：`backend/delivery/`
>
> 本文为总览；实现以 `pipeline/` 下五份 Spec 的契约为准。

---

## 1. 背景与目标

### 1.1 现状

当前系统通过多轮对话采集直播间搭建需求（10 章节调研表），会话完成后：

1. 用户确认提交 → `POST /api/orders` 写入 `deliveries`
2. 可临时导出 Markdown / Excel / Word（`POST /api/generate/{type}`）
3. 管理员后台查看需求记录

**尚无**：垂类知识库、方案智能生成、视觉预览、视频预览、综合交付包。

### 1.2 目标能力

| # | 能力 | 一句话定义 |
|---|------|-----------|
| F1 | 向量知识库 | Milvus 存储设备参数、搭建方案、垂类知识，支持混合检索 |
| F2 | 方案拆解 Skill | 需求文档拆解 + RAG 检索 → 结构化方案 PDF（设备清单/套餐/搭建规划） |
| F3 | 预览图 Skill | 根据方案生成 3 张多机位（0°/120°/240°）直播间预览图 |
| F4 | 预览视频 Skill | 根据方案 + 预览图生成环绕/漫游预览视频 |
| F5 | 汇总交付 Skill | 交叉校验 F2–F4 产物，完善一致性，打包最终交付物 |

### 1.3 产品边界

- **做什么**：在订单提交后异步生成「方案文档 + 多机位图 + 预览视频」综合交付包；知识库支持运营侧维护。
- **不做什么**：
  - 不替代现有对话采集（`/api/chat` 职责不变）
  - 不做真实电商下单/支付
  - 不做真·equirectangular 360° 全景（国内 API 几何不稳，见 §6.3）
  - 不做在线 3D 编辑器
  - 不自部署大模型推理（生图/生视频走云 API）

---

## 2. 总体架构

```text
┌─────────────────────────────────────────────────────────────────┐
│                         前端工作台 (React)                        │
│  对话采集 → 确认订单 → [异步交付进度] → 交付包预览/下载              │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / SSE
┌────────────────────────────▼────────────────────────────────────┐
│                      FastAPI 后端 (现有)                          │
│  agent/  对话状态机（不变）                                        │
│  delivery/  md/xlsx/docx（保留）                                  │
│  ── 新增 ─────────────────────────────────────────────────────  │
│  knowledge/   Milvus 客户端 + Embedding + 检索封装                 │
│  pipeline/    5 个 Skill 的编排与任务状态机                        │
│  media/       DashScope 生图/生视频异步客户端 + 落盘                 │
│  delivery/    pdf.py（WeasyPrint）+ package.py（最终打包）         │
└──────┬──────────────────┬──────────────────┬────────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
 ┌──────────┐      ┌────────────┐     ┌──────────────┐
 │ Milvus   │      │ DashScope  │     │ 本地/OSS 存储  │
 │ Standalone│     │ 图+视频 API │     │ 图/视频/PDF   │
 │ (3 coll) │      │ (万相/可灵) │     │              │
 └──────────┘      └────────────┘     └──────────────┘
       │
       ▼
 ┌──────────┐
 │Embedding │  生产：text-embedding-v3
 │+ Rerank  │  本地：BGE-M3 / bge-reranker-v2-m3
 └──────────┘
```

### 2.1 Skill 定义（本 Spec 中的含义）

「Skill」指**后端可独立编排、可单独重试的流水线阶段模块**，不是 Claude Desktop Skill。

每个 Skill 满足：

| 约定 | 说明 |
|------|------|
| 输入/输出契约 | 显式 Pydantic 模型，禁止隐式全局状态 |
| 幂等 | 相同 `pipeline_run_id + skill` 重复执行不产生重复费用（有缓存/已有产物则复用） |
| 可观测 | 写入 `pipeline_runs` / `skill_runs` 状态与耗时 |
| 失败策略 | 可单独重试；有降级路径（见各 Skill） |
| 成本可见 | 每次外部调用记录估算费用 |

### 2.2 触发时机

```text
用户确认订单 (POST /api/orders 成功)
  → 创建 pipeline_run
  → 后台任务队列依次执行 F2 → F3 → F4 → F5
  → 前端通过进度接口/SSE 轮询状态
  → 全部完成后交付包可下载
```

现有 `deliveries` 记录**需求确认**；新增 `pipeline_runs` 记录**智能交付生成**。二者一对一（同一 session）。

---

## 3. F1 — Milvus 向量知识库

### 3.1 选型结论

| 项 | 选型 | 理由 |
|----|------|------|
| 向量库 | **Milvus Standalone**（生产）/ **Milvus Lite**（开发测试） | 原生 BM25+稠密混合检索、中文 Jieba 分词、分区键；与 Qdrant/Chroma/pgvector 相比更适合结构化设备知识 |
| SDK | `pymilvus` 3.x | 配 Milvus 3.x |
| Embedding（生产） | 阿里云 **text-embedding-v3**（1024 维） | 国内低延迟、免运维、与 DashScope 同账号 |
| Embedding（本地） | **BGE-M3**（`FlagEmbedding`） | 开源中文标杆，支持 dense |
| Rerank | **BAAI/bge-reranker-v2-m3**（本地）或 DashScope gte-rerank | hybrid top-30 → 精排 top-5~8 |
| 部署 | Docker Compose：`milvus-standalone` + MinIO + etcd | 中小 SaaS 足够；不上 Cluster/Zilliz |

> 用户原话「mlivs」按 **Milvus** 理解与落地。

### 3.2 Collection Schema

三个 Collection，均启用 **dense + sparse(BM25)** 混合检索。

#### 3.2.1 `equipment_specs` — 设备参数

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INT64 PK | 主键 |
| `name` | VARCHAR(256) | 设备名称，如「爱图仕 300D」 |
| `category` | VARCHAR(64) | 灯光/相机/镜头/声卡/支架/背景/其他 |
| `brand` | VARCHAR(64) | 品牌 |
| `price_band` | VARCHAR(16) | low / mid / high / ultra |
| `room_size` | VARCHAR(16) | small / medium / large（映射调研表面积段） |
| `industry` | VARCHAR(32) | 适用垂类；`all` 表示通用 |
| `specs` | JSON | 结构化参数（功率、色温、接口等） |
| `text` | VARCHAR(4096) `enable_analyzer=True` | 供 BM25 的正文（名称+描述+适用场景） |
| `dense` | FLOAT_VECTOR(1024) | 外部 embedding 写入 |
| `sparse` | SPARSE_FLOAT_VECTOR | BM25 Function 自 `text` 生成 |
| `source` | VARCHAR(128) | 知识来源/版本 |
| `updated_at` | INT64 | unix ts |

索引：`dense` → HNSW / COSINE；`sparse` → SPARSE_INVERTED_INDEX / BM25。  
分区键建议：`industry`。

#### 3.2.2 `setup_schemes` — 搭建方案

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INT64 PK | |
| `scheme_name` | VARCHAR(256) | 如「女装 20㎡ 高级感平价套装」 |
| `industry` | VARCHAR(32) | 垂类 |
| `budget_level` | VARCHAR(16) | 与调研表预算段映射 |
| `room_size` | VARCHAR(16) | |
| `live_type` | VARCHAR(32) | 达人/品牌/工厂/IP |
| `equipment_ids` | JSON | 引用的 equipment_specs id 列表 |
| `package_tiers` | JSON | 套餐方案：`[{tier, total_price, items[]}]` |
| `layout_notes` | VARCHAR(2048) | 布局/动线/布光要点 |
| `text` | VARCHAR(4096) | BM25 正文 |
| `dense` / `sparse` | 同上 | |
| `source` / `updated_at` | 同上 | |

#### 3.2.3 `vertical_knowledge` — 垂类知识

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INT64 PK | |
| `industry` | VARCHAR(32) | 女装/美妆/食品/珠宝… |
| `scene` | VARCHAR(64) | 布光/背景/机位/话术区/商品展示… |
| `content` | VARCHAR(8192) | 知识正文（切块后） |
| `text` | VARCHAR(4096) | BM25 正文（通常=content 摘要头） |
| `dense` / `sparse` | 同上 | |
| `source` / `updated_at` | 同上 | |

### 3.3 写入（Ingestion）

- **入口**：`backend/scripts/ingest_knowledge.py` + 可选 admin API（后期）
- **切块规则**：
  - 设备参数：**整行一块**，结构化字段进 metadata，不切碎
  - 搭建方案：方案为一块；超长按小节切
  - 垂类文档：按小标题切，200–500 汉字，保留「适用场景/设备清单」上下文头；禁止摘要式切块
- **幂等**：以业务主键（如 `brand+name+source`）做 upsert
- **向量化**：写入前调用 Embedding 服务；失败整批回滚并告警

### 3.4 检索 API（内部）

```python
# knowledge/search.py — 管线内部接口，不直接暴露给前端
async def hybrid_search(
    collection: Literal['equipment_specs', 'setup_schemes', 'vertical_knowledge'],
    query: str,
    *,
    industry: str | None = None,
    room_size: str | None = None,
    budget_level: str | None = None,
    limit: int = 8,
) -> list[KnowledgeHit]:
    """hybrid top-30 → rerank → top-limit"""

class KnowledgeHit(BaseModel):
    collection: str
    id: int
    score: float
    payload: dict  # 原始字段
```

过滤表达式示例：

```text
industry in ['女装', 'all'] and room_size in ['small', 'medium'] and budget_level in ['low', 'mid']
```

### 3.5 本地开发

- `MILVUS_URI=./data/milvus_demo.db`（Lite）或 `http://localhost:19530`（Standalone）
- CI 不依赖真实 Milvus；knowledge 层单测 mock 客户端
- 种子数据：`backend/scripts/seed_knowledge.py` 提供每垂类 ≥20 条样例

### 3.6 F1 边界

| 做 | 不做 |
|----|------|
| 三 collection + 混合检索 | 自动爬取电商商品库 |
| 运营脚本导入 JSON/CSV | 复杂知识图谱 |
| metadata 过滤 + rerank | 用户上传知识进生产库（需人工审核流，后期） |

---

## 4. F2 — 需求拆解 + RAG + 方案 PDF Skill

**Skill 名**：`plan_document`

### 4.1 输入

```python
class PlanDocumentInput(BaseModel):
    pipeline_run_id: str
    session_id: str
    form_state: dict          # 现有 StudioFormState 序列化
    delivery_id: int | None   # 若已提交订单
```

需求文档 = 当前调研表 10 章节的已填字段（`build_render_data` 同源），关键检索键：

| 来源字段 | 用途 |
|----------|------|
| `industry.category` / `subcategory` | 垂类过滤 |
| `venue.area` | room_size 分档 |
| `budget.total` / `budget.equip` / `budget.decor` | budget_level |
| `goal.core` | 全新/优化/只调参 → 方案深度 |
| `product.main` / `keywords` | 检索 query |
| `equipment.inventory` | 已有设备，从推荐中扣减 |
| `benchmark.*` | 风格倾向 |

### 4.2 处理步骤

```text
1. Normalize   form_state → RequirementBrief（结构化需求摘要）
2. Decompose   LLM 拆解为检索意图列表（3–6 条 query + 过滤条件）
3. Retrieve    对三 collection 分别 hybrid_search + rerank
4. Compose     LLM 结合需求 + 知识片段生成 PlanDraft JSON
5. Validate    校验设备 id 存在、预算区间自洽、必填章节齐全
6. Render      jinja2 HTML → WeasyPrint PDF
7. Persist     写 artifact：plan.json + plan.pdf
```

### 4.3 输出

```python
class PlanDocumentOutput(BaseModel):
    skill: Literal['plan_document']
    status: Literal['succeeded', 'degraded', 'failed']
    plan_json_path: str
    pdf_path: str
    requirement_brief: dict
    knowledge_hits: list[dict]   # 用于审计与 F5 引用
    warnings: list[str]
```

### 4.4 PlanDraft 结构（中间真相源）

```json
{
  "meta": {
    "brand": "云裳",
    "industry": "women",
    "room_size": "medium",
    "budget_total": "3-5w",
    "generated_at": "ISO-8601",
    "knowledge_refs": [{"collection": "...", "id": 123}]
  },
  "summary": "一句话方案定位",
  "layout": {
    "zones": [{"name": "主播区", "notes": "..."}],
    "lighting_plan": "三点布光…",
    "camera_plan": "主机位…"
  },
  "equipment_list": [
    {
      "knowledge_id": 1001,
      "category": "灯光",
      "name": "爱图仕 300D II",
      "model": "300D II",
      "qty": 2,
      "unit_price_band": "high",
      "reason": "适配 20㎡ 中高客单女装"
    }
  ],
  "package_tiers": [
    {
      "tier": "性价比",
      "total_range": "1.2-1.6w",
      "items": [{"name": "...", "qty": 1}]
    },
    {
      "tier": "进阶",
      "total_range": "2.2-2.8w",
      "items": []
    },
    {
      "tier": "高配",
      "total_range": "3.5-4.2w",
      "items": []
    }
  ],
  "setup_steps": ["第1步：…", "第2步：…"],
  "risks": ["窗户在主播右侧需遮光…"]
}
```

> **F3/F4/F5 均以 `plan.json` 为唯一方案真相源**，禁止各阶段重新自由发挥设备清单。

### 4.5 PDF 技术方案

| 项 | 选型 |
|----|------|
| 模板 | jinja2 HTML（`delivery/templates/plan.html`） |
| 渲染 | **WeasyPrint** |
| 字体 | 思源黑体 / 阿里普惠体，`@font-face` 内嵌 |
| 页面 | A4；封面 / 需求摘要 / 布局说明 / 设备表 / 三档套餐 / 搭建步骤 / 风险提示 |
| 附件 | 设备明细仍可并行导出 xlsx（复用 openpyxl） |

### 4.6 降级策略

| 场景 | 行为 |
|------|------|
| Milvus 不可用 | 使用预置「通用模板方案」按行业+面积匹配，`status=degraded`，PDF 标注「未接入知识库」 |
| Embedding 失败 | 回退关键词 metadata 过滤检索 |
| LLM 失败 | 保留最近一次成功 plan；无则 failed |
| WeasyPrint 失败 | 降级输出 Word（现有 python-docx 路径） |

### 4.7 F2 边界

| 做 | 不做 |
|----|------|
| 结构化方案 + 三档套餐 + 步骤 PDF | 实时比价/电商链接 |
| 引用 knowledge_id 可审计 | 自动改写用户已确认的需求字段 |
| 预算自洽校验 | 法律合同级报价单 |

---

## 5. F3 — 预览图生成 Skill

**Skill 名**：`preview_images`

### 5.1 输入

```python
class PreviewImagesInput(BaseModel):
    pipeline_run_id: str
    plan_json_path: str          # F2 产物
    image_count: int = 3         # 产品要求 ≥3
    quality: Literal['draft', 'standard', 'high'] = 'standard'
```

### 5.2 选型

| 项 | 主选 | 备选 |
|----|------|------|
| 模型 | **wan2.7-image-pro**（阿里百炼） | qwen-image-3.0-pro；kling-v3-image |
| 关键能力 | `enable_sequential=true` **组图模式**（一次最多 12 张故事连贯图） | 固定 seed 分次生成 |
| 风格锁定 | `seed` + `color_palette` | 参考图 image-to-image |
| 分辨率 | 高清档 2K/4K；draft 1K | |
| 调用 | DashScope 异步任务 + 轮询 | 同步仅用于 draft |

### 5.3 三机位「360 预览」策略（产品定义）

产品语境中的「三张 360 预览图」落地为 **同场景三机位连贯静帧**，而非几何等距柱状全景：

| 图 | 机位 | Prompt 要点 |
|----|------|-------------|
| P1 | 正面主视角（主播位） | 主机位构图、商品区可见 |
| P2 | 左侧 120° | 布光设备、背景层次 |
| P3 | 背面/右侧 240° | 线材收纳、空间纵深、动线 |

实现：

1. 从 `plan.json` 生成 **SceneCard**（房间尺寸档、风格、色温、家具/灯光/背景清单、商品类目）
2. 组装英文+中文混合 prompt 模板，锁定：`same room, same furniture set, same lighting setup, three camera angles: front / left-side / rear`
3. 单次 `enable_sequential` 任务出 3 张；失败重试固定 `seed`
4. 下载 URL（24h 过期）→ 立即落盘 `data/artifacts/{pipeline_run_id}/images/`

```python
class PreviewImagesOutput(BaseModel):
    skill: Literal['preview_images']
    status: Literal['succeeded', 'partial', 'failed']
    images: list[dict]  # [{angle: 'front'|'left'|'rear', path, seed, model, cost_cny}]
    seed_used: int | None
    warnings: list[str]
```

### 5.4 降级

| 场景 | 行为 |
|------|------|
| 组图失败 | 固定 seed 串行 3 次单图 |
| 主模型失败 | 切 qwen-image / kling-v3-image |
| 仅成功 1–2 张 | `partial`，允许进 F4（至少 1 张）；F5 标注缺失机位 |
| 全失败 | `failed`，F5 可出「无图交付包」 |

### 5.5 成本与时延（标准档）

- 3 × wan2.7-image-pro ≈ 1.5 元；20–60s
- draft 3 × z-image-turbo ≈ 0.3 元

### 5.6 F3 边界

| 做 | 不做 |
|----|------|
| 3 张连贯多机位静帧 | 真 equirectangular 360 全景（实验项，不进主路径） |
| 基于 plan.json 的确定性 SceneCard | 用户任意风格自由生成 |
| 落盘 + seed 记录可复现 | 修图/局部重绘编辑器 |

---

## 6. F4 — 预览视频生成 Skill

**Skill 名**：`preview_video`

### 6.1 输入

```python
class PreviewVideoInput(BaseModel):
    pipeline_run_id: str
    plan_json_path: str
    images: list[dict]           # F3 产物，至少 1 张
    duration_sec: int = 8        # 5–15
    resolution: Literal['720P', '1080P'] = '720P'
```

### 6.2 选型

| 项 | 主选 | 备选 |
|----|------|------|
| 模型 | **wan2.7-i2v**（首帧图生视频） | kling-v3-video；成本敏感 wan2.6-i2v-flash |
| 镜头语言 | prompt：`slow orbit / cinematic interior walkthrough around the livestream set` | 首尾帧插值（若用 P1→P2） |
| 调用 | DashScope 异步任务 + 轮询（1–4 分钟） | |
| 产物 | mp4，落盘 `data/artifacts/{id}/video/` | |

### 6.3 处理步骤

```text
1. 选择主视觉帧（默认 P1 正面；失败顺延）
2. 从 plan.json 抽取 motion prompt（空间尺寸感、灯光氛围、不出现文字 logo）
3. 提交 i2v 异步任务（duration / resolution / 是否有声默认无声）
4. 轮询至完成 → 下载 mp4 → 校验可播放（ffprobe 可选）
5. 写 artifact + 元数据（模型、时长、成本、源图 path）
```

### 6.4 输出

```python
class PreviewVideoOutput(BaseModel):
    skill: Literal['preview_video']
    status: Literal['succeeded', 'failed']
    video_path: str
    source_image: str
    duration_sec: float
    resolution: str
    model: str
    cost_cny: float
    warnings: list[str]
```

### 6.5 降级

| 场景 | 行为 |
|------|------|
| 1080P 失败 | 自动降 720P 重试一次 |
| 主模型失败 | 切 kling-v3-video |
| 无可用图 | 直接 failed（F5 出无视频包） |
| 超时（>5 min） | failed，可人工重试 |

### 6.6 成本与时延

- 5s @720P flash ≈ 0.75–1.5 元；1080P 质量档 ≈ 5 元
- 端到端 1–4 分钟，必须异步 UI

### 6.7 F4 边界

| 做 | 不做 |
|----|------|
| 单条 5–15s 环绕/漫游预览 | 多镜头剪辑成片、配音 BGM 工作流 |
| 基于 F3 静帧 | 文生视频无图直接生成（一致性差） |
| 无声或模型默认音频 | 专业配音 |

---

## 7. F5 — 汇总完善与最终交付 Skill

**Skill 名**：`final_package`

### 7.1 职责

1. **交叉校验**：设备清单（PDF）vs 预览图内容描述 vs 视频帧 vs 原始需求
2. **互完善**：
   - 若图片风格与方案文案冲突 → 修订 plan 摘要中的风格描述（不改设备硬件清单）
   - 若发现缺失机位/视频失败 → 在交付说明中标注
   - 补齐交付 README（如何看图、套餐如何选、下一步）
3. **打包**：生成最终交付目录 + 可选 zip

### 7.2 最终交付物清单（产品验收）

| 产物 | 最低要求 | 路径约定 |
|------|----------|----------|
| 360 预览图 | **≥3 张**（失败允许 partial ≥1 并标注） | `images/preview_front.png` 等 |
| 预览视频 | 1 条 5–15s mp4 | `video/preview.mp4` |
| 方案 PDF | 设备清单 + 三档套餐 + 搭建规划 | `docs/plan.pdf` |
| 方案 JSON | 机器可读真相源 | `docs/plan.json` |
| 交付说明 | 中文 README | `README.md` |
| （可选）设备 Excel | 复用现有 openpyxl | `docs/equipment.xlsx` |

### 7.3 交叉校验规则（硬约束）

```text
- plan.equipment_list 每项 knowledge_id 必须在 F1 存在或标记为「定制推荐」
- 套餐 total_range 必须落在用户 budget_total 允许区间 ±10%（除非用户选了效果优先）
- 图片数量、视频存在性写入 package_manifest
- 所有文件 sha256 入 manifest，供下载完整性校验
```

### 7.4 LLM 汇总 Prompt 职责边界

- **允许**：写交付说明、统一话术、指出图与文的风格差异并建议以谁为准
- **禁止**：擅自增删设备型号、改价格区间、伪造未生成成功的图片/视频

### 7.5 输出

```python
class FinalPackageOutput(BaseModel):
    skill: Literal['final_package']
    status: Literal['ready', 'ready_with_warnings', 'failed']
    package_dir: str
    manifest: dict   # 文件列表、hash、各 skill status、成本汇总
    delivery_notes_md: str
```

### 7.6 F5 边界

| 做 | 不做 |
|----|------|
| 校验 + 说明 + 打包 | 重新生成图/视频（失败重试属 F3/F4） |
| manifest 可审计 | 多方案 A/B 并行对比包（后期） |

---

## 8. 共享基础设施

### 8.1 任务与状态

```sql
-- 新表（SQLite，与现有 store/db.py 风格一致，无 ORM）
CREATE TABLE pipeline_runs (
  id TEXT PRIMARY KEY,              -- uuid
  session_id TEXT NOT NULL,
  delivery_id INTEGER,
  user_id INTEGER NOT NULL,
  status TEXT NOT NULL,             -- pending|running|succeeded|partial|failed|cancelled
  current_skill TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  error TEXT
);

CREATE TABLE skill_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pipeline_run_id TEXT NOT NULL,
  skill TEXT NOT NULL,              -- plan_document|preview_images|preview_video|final_package
  status TEXT NOT NULL,             -- pending|running|succeeded|degraded|partial|failed
  attempt INTEGER DEFAULT 1,
  input_json TEXT,
  output_json TEXT,
  cost_cny REAL DEFAULT 0,
  started_at TEXT,
  finished_at TEXT,
  error TEXT
);

CREATE TABLE artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pipeline_run_id TEXT NOT NULL,
  kind TEXT NOT NULL,               -- plan_json|plan_pdf|image|video|package_zip|manifest
  path TEXT NOT NULL,
  sha256 TEXT,
  meta_json TEXT,
  created_at TEXT NOT NULL
);
```

### 8.2 异步执行

| 项 | 约定 |
|----|------|
| 执行器 | FastAPI `BackgroundTasks` 起步；量大再换独立 worker |
| 超时 | plan ≤ 120s；images ≤ 180s；video ≤ 300s；package ≤ 60s |
| 重试 | 外部 API 瞬时错误自动重试 2 次（指数退避）；业务校验失败不自动重试 |
| 取消 | `POST /api/pipeline/{id}/cancel` 仅允许 pending/running |
| 并发 | 每用户同时 1 个 pipeline_run |

### 8.3 配置（环境变量）

```text
# 知识库
MILVUS_URI=
EMBEDDING_PROVIDER=dashscope|local_bge
DASHSCOPE_API_KEY=
EMBEDDING_MODEL=text-embedding-v3

# 生图/生视频
IMAGE_MODEL=wan2.7-image-pro
VIDEO_MODEL=wan2.7-i2v
MEDIA_QUALITY=standard
MEDIA_RESULT_TTL_HOURS=24

# 存储
ARTIFACT_ROOT=./data/artifacts
# 后期：OSS_ENDPOINT / OSS_BUCKET

# 开关
PIPELINE_ENABLED=true
```

### 8.4 存储

- 开发：本地 `ARTIFACT_ROOT`（与现有 `store/uploads.py` 同盘思路）
- 生产：生成 URL 24h 过期 → **必须转存**（OSS 或持久盘）；下载走后端鉴权代理，不直出 DashScope URL

### 8.5 API 契约（新增）

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/api/pipeline` | 为已提交 session 启动管线（或 orders 成功后自动启动） |
| `GET` | `/api/pipeline/{id}` | 状态 + 各 skill 进度 + 费用 |
| `GET` | `/api/pipeline/{id}/events` | SSE 进度推送（复用现有 chat stream 风格） |
| `POST` | `/api/pipeline/{id}/retry` | 重试指定 failed skill |
| `POST` | `/api/pipeline/{id}/cancel` | 取消 |
| `GET` | `/api/pipeline/{id}/package` | 下载 zip 或浏览 manifest |
| `GET` | `/api/pipeline/{id}/artifacts/{kind}` | 单文件鉴权下载 |

权限：仅 session owner 或 admin。Guest 角色禁止启动（与现有 orders 一致）。

### 8.6 与现有系统关系

| 现有 | 关系 |
|------|------|
| `/api/chat` 采集 | **不变**；form_state 仍是唯一需求源 |
| `/api/orders` | 成功后可选自动 `POST /api/pipeline` |
| `/api/generate/{md,excel,word}` | 保留；不进智能管线 |
| `deliveries` | 需求确认记录；pipeline 产物挂 artifacts，不覆盖 markdown |
| Admin | 后期增加 pipeline 列表页；本 Spec 仅约定数据可查询 |

---

## 9. 选型总表（锁定）

| 层 | 选型 | 备选/降级 |
|----|------|-----------|
| 向量库 | Milvus Standalone 3.x | Lite（开发）；Qdrant（运维极简时） |
| Embedding | text-embedding-v3 | BGE-M3 |
| Rerank | bge-reranker-v2-m3 | DashScope gte-rerank |
| LLM | 现有 Anthropic 兼容端点 | 不变 |
| PDF | jinja2 + WeasyPrint | Word 降级 |
| 生图 | wan2.7-image-pro（组图） | qwen-image / kling-v3-image |
| 生视频 | wan2.7-i2v | kling-v3 / wan2.6-flash |
| 统一 API | 阿里 DashScope | 火山方舟（长视频补充） |
| 产物存储 | 本地盘 → OSS | |

**不采用**：Midjourney（无 API）、DALL-E/Runway/Pika（国内生产链路不稳）、真 360 全景主路径、自建 GPU 推理。

---

## 10. 分阶段落地

| 阶段 | 内容 | 验收 |
|------|------|------|
| **P0 知识库** | Milvus Compose + schema + seed + hybrid_search + 单测 | 给定「女装 20㎡ 中预算」能召回合理设备/方案 |
| **P1 方案 PDF** | F2 Skill + WeasyPrint 模板 + plan.json | 端到端从 form_state 出 PDF，含三档套餐 |
| **P2 预览图** | F3 + DashScope 异步 + 落盘 | 稳定出 3 张连贯机位图 |
| **P3 预览视频** | F4 + i2v 轮询 | 出 5–15s 可播放 mp4 |
| **P4 汇总包** | F5 + pipeline API + SSE 进度 + 前端交付面板 | 订单后 2–5 分钟可下载完整包 |
| **P5 运营** | 知识库 admin 导入、成本看板、失败重试 UI | 运营可维护知识，成本可审计 |

每阶段单独 PR，CI 不依赖真实 Milvus/DashScope（mock + 契约测试）。

---

## 11. 风险与开放问题

| 风险 | 影响 | 缓解 |
|------|------|------|
| 组图机位一致性不足 | 三张图不像同一房间 | seed+color_palette；失败降级固定 seed 串行；人工可重 roll |
| DashScope 结果 URL 24h 过期 | 交付物丢失 | 启动即转存；artifact sha256 |
| 视频时延 1–4 分钟 | 用户等待焦虑 | SSE 进度 + 可离开后通知 |
| 知识库冷启动 | 召回差 | P0 先人工整理每垂类核心 50–100 条 |
| 成本失控 | 重复生成烧钱 | 幂等缓存；每用户日限额；成本写 skill_runs |
| WeasyPrint 系统依赖（pango/cairo） | 部署失败 | Docker 镜像预装；失败降级 Word |
| 需求过简（提前结束调研） | 方案空泛 | `allow_incomplete` 订单允许 pipeline，但 PDF 顶部标注「信息不完整」 |

### 开放问题（实现前需产品确认）

1. 订单提交后**自动**跑管线，还是用户点「生成智能交付包」？
2. Guest / 提前结束调研是否允许生成（建议：正式用户允许，Guest 禁止）？
3. 图片是否允许用户「重 roll」一次（建议：免费 1 次）？
4. 最终包是否要合并进现有 Word 确认书，还是独立 zip？
5. 生产 OSS 选型（阿里 OSS / 其他）与 CDN。

---

## 12. 验收清单（总）

- [ ] Milvus 三 collection 可写入、可 hybrid 检索、可按 industry 过滤
- [ ] F2：从真实 form_state 生成含设备清单+三档套餐+步骤的中文 PDF
- [ ] F3：单次任务产出 ≥3 张风格连贯的多机位图并落盘
- [ ] F4：基于主视觉图产出可播放 5–15s mp4 并落盘
- [ ] F5：manifest 含全部产物 hash；缺图/缺视频时包仍可交付且有说明
- [ ] Pipeline API 鉴权正确；Guest 不可启动；成本与耗时可查询
- [ ] 全链路 mock 测试进 CI；不依赖外网密钥

---

## 附录 A — 调研摘要

### A.1 Milvus / RAG / PDF

- Milvus 3.x Standalone；Lite 仅开发
- 混合检索：dense HNSW + BM25 sparse，RRF/Weighted 融合，再 rerank
- 中文 Embedding：生产 text-embedding-v3，本地 BGE-M3
- PDF：WeasyPrint + jinja2 优于 reportlab/LibreOffice

### A.2 图像 / 视频

- 阿里百炼一站聚合：万相、可灵、Vidu、海螺同一 Key
- `wan2.7-image-pro` 组图 `enable_sequential` 是多机位一致性最直接 API 能力
- 视频一律异步任务；产物 URL 24h 必须转存
- 单包（3 图 + 5–10s 视频）成本约 0.8–6.5 元，时延 2–5 分钟
