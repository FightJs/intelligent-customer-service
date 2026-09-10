# F1 Spec — Qdrant 向量知识库

> 管线阶段：知识底座。供 F2 检索设备参数 / 搭建方案 / 垂类知识。
>
> 关联：
> - 总览：`docs/backend-docs/spec-studio-delivery-pipeline.md`
> - 需求字段：`backend/survey/schema_def.py`
> - 前端知识库管理页：`docs/compose/spec/plan-delivery-pages.md`
>
> **变更记录**：向量库由 Milvus Standalone（etcd + MinIO + milvus 三容器）
> 改为 **Qdrant**（单容器 / 本地嵌入式），接口层 `VectorStore` 不变。

---

## 1. 目标与边界

### 1.1 目标

用 **Qdrant** 建立可维护的直播间搭建知识库，支持：

1. 按垂类 / 面积 / 预算档过滤的 **dense + BM25 混合检索**
2. 运营侧通过脚本与 Admin 上传 PDF 导入知识
3. F2 Skill 通过稳定内部 API 取回结构化命中（含 `knowledge_id` 可审计）

### 1.2 明确不做

| 不做 | 原因 |
|------|------|
| 自动爬取电商平台商品库 | 合规与数据质量风险 |
| 知识图谱 / 多跳推理 | 冷启动成本过高 |
| 用户会话内容直接写入生产库 | 需人工审核流，后期再议 |
| 在线向量编辑器 | 运营用 JSON/PDF 导入即可 |
| Cluster / Zilliz Cloud | 当前规模单机足够 |

---

## 2. 选型结论

| 项 | 选型 | 备选 | 理由 |
|----|------|------|------|
| 向量库 | **Qdrant 1.13** | 本地嵌入式 `QDRANT_URI=./data/qdrant` | 单容器；named dense + sparse 向量；payload 结构化过滤；运维远轻于 Milvus 三件套 |
| SDK | `qdrant-client` ≥ 1.12 | — | 服务端 / 本地路径同一客户端 |
| Embedding（生产） | 阿里 **text-embedding-v3**（1024 维） | — | 与 DashScope 同账号，国内延迟低 |
| Embedding（本地/CI） | **BGE-M3** | — | 开源中文标杆；CI 不依赖外网 |
| Rerank | **BAAI/bge-reranker-v2-m3** | DashScope gte-rerank | hybrid top-30 → 精排 top-5~8 |
| 部署 | 单容器 `deploy/qdrant.yml`，或本地嵌入式路径 | — | 无 etcd / MinIO |
| 替换原因 | Milvus Standalone | — | 三容器过重；中小知识库不需要 Milvus 级运维 |

> 历史：初版选型为 Milvus Standalone；后因运维成本与启动速度改为 Qdrant。

---

## 3. Collection Schema

三个 Collection，统一约定：

- 主键：`id` INT64（业务 upsert，非 auto_id）
- 正文字段：`text` VARCHAR(4096)，入库时 tokenize 生成稀疏向量
- 稠密向量：`dense` named vector，1024 维，COSINE
- 稀疏向量：`sparse` named vector，客户端 token-hash TF
- 公共审计：`source` VARCHAR(128)、`updated_at` INT64
- 过滤字段（payload）：`industry` / `room_size` / `budget_level` 等

### 3.1 `equipment_specs` — 设备参数

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | VARCHAR(256) | 设备名，如「爱图仕 300D」 |
| `category` | VARCHAR(64) | 灯光/相机/镜头/声卡/支架/背景/采集卡/其他 |
| `brand` | VARCHAR(64) | 品牌 |
| `price_band` | VARCHAR(16) | low / mid / high / ultra |
| `room_size` | VARCHAR(16) | small / medium / large / xlarge |
| `industry` | VARCHAR(32) | 垂类；`all` 通用 |
| `specs` | JSON | 功率、色温、接口、尺寸等结构化参数 |
| `text` | VARCHAR(4096) | 稀疏检索正文 = 名称+描述+适用场景 |

**过滤字段**：`industry`

### 3.2 `setup_schemes` — 搭建方案

| 字段 | 类型 | 说明 |
|------|------|------|
| `scheme_name` | VARCHAR(256) | 如「女装 20㎡ 高级感平价套装」 |
| `industry` | VARCHAR(32) | 垂类 |
| `budget_level` | VARCHAR(16) | 对齐调研表预算段映射 |
| `room_size` | VARCHAR(16) | |
| `live_type` | VARCHAR(32) | 达人/品牌/工厂/IP |
| `equipment_ids` | JSON | 引用 equipment_specs 的 id 列表 |
| `package_tiers` | JSON | `[{tier, total_price_range, items[]}]` |
| `layout_notes` | VARCHAR(2048) | 布局/动线/布光要点 |
| `text` | VARCHAR(4096) | BM25 正文 |

### 3.3 `vertical_knowledge` — 垂类知识

| 字段 | 类型 | 说明 |
|------|------|------|
| `industry` | VARCHAR(32) | |
| `scene` | VARCHAR(64) | 布光/背景/机位/话术区/商品展示… |
| `content` | VARCHAR(8192) | 切块正文 |
| `text` | VARCHAR(4096) | BM25 正文（可为 content 摘要头） |

### 3.4 枚举映射（与调研表对齐）

```text
room_size:
  small   ← venue.area in ['<10', '10-20']
  medium  ← venue.area in ['20-30', '30-50']
  large   ← venue.area in ['50+']
  xlarge  ← 有具体尺寸且面积 > 80㎡

budget_level:
  low/mid/high/ultra ← budget.total 与 budget.equipment 综合
  user budget.<field> 原始区间值不得在 F1 内改写
```

---

## 4. 写入（Ingestion）

### 4.1 入口

| 入口 | 用途 |
|------|------|
| `backend/scripts/ingest_knowledge.py` | 批量 JSON/CSV 导入 |
| `backend/scripts/seed_knowledge.py` | 开发/演示种子数据（每垂类 ≥20 条） |
| Admin「知识库」Tab | 运营上传 PDF，后台异步解析入库 |

### 4.2 切块规则

| 类型 | 规则 |
|------|------|
| 设备参数 | **整行一块**，结构化字段进 metadata，不切碎 |
| 搭建方案 | 整方案一块；超长按小节切，保留 package_tiers 完整 |
| 垂类 PDF | 按小标题切，200–500 汉字；块头注入「适用场景/行业」上下文；禁止纯摘要式切块 |

### 4.3 幂等与失败

- 业务主键 upsert：设备 `brand+name+source`；方案 `scheme_name+source`；知识 `source+chunk_index`
- Embedding 失败 → 整批回滚并告警，不写半截数据
- 版本：`source` 记录文件名+hash 前 8 位，便于覆盖更新

---

## 5. 检索 API（内部）

```python
# backend/knowledge/search.py — 仅管线内部调用，不直接暴露给前端
async def hybrid_search(
    collection: Literal['equipment_specs', 'setup_schemes', 'vertical_knowledge'],
    query: str,
    *,
    industry: str | None = None,
    room_size: str | None = None,
    budget_level: str | None = None,
    category: str | None = None,
    limit: int = 8,
) -> list[KnowledgeHit]:
    """hybrid top-30 → rerank → top-limit"""

class KnowledgeHit(BaseModel):
    collection: str
    id: int
    score: float
    payload: dict
```

过滤条件示例（结构化 filter，字段间 AND、值间 OR）：

```python
{"industry": ["women", "all"], "room_size": ["small", "medium"], "budget_level": ["low", "mid"]}
```

### 5.1 融合策略

1. dense COSINE + sparse token 重合度各取 top-30
2. Weighted / RRF 融合（默认 Weighted：dense 0.6 + sparse 0.4，可配置）
3. Rerank 模型精排 → 返回 top-`limit`

### 5.2 降级

| 场景 | 行为 |
|------|------|
| 向量库不可达 | 返回空列表 + `degraded=true`；F2 走模板方案 |
| Embedding 服务失败 | 仅 metadata 过滤 + keyword（sparse only） |
| Rerank 失败 | 使用融合分排序，不中断 |

---

## 6. 本地开发与 CI

| 项 | 约定 |
|----|------|
| 开发 URI | `QDRANT_URI=memory://`（测试）或 `./data/qdrant`（嵌入式）或 `http://localhost:6333` |
| CI | **不依赖真实 Qdrant**；`knowledge` 层单测 mock 客户端 |
| 契约测试 | mock hybrid_search 固定返回，供 F2 联调 |
| Docker | `docker compose -f deploy/qdrant.yml up -d` |

---

## 7. 配置

```text
QDRANT_URI=memory:// | ./data/qdrant | http://localhost:6333
QDRANT_API_KEY=
EMBEDDING_PROVIDER=dashscope|local_bge
DASHSCOPE_API_KEY=
EMBEDDING_MODEL=text-embedding-v3
RERANK_PROVIDER=local|dashscope
RERANK_MODEL=bge-reranker-v2-m3
```

---

## 8. 验收清单

- [ ] 三 collection 可创建、可 upsert、可 hybrid 检索
- [ ] 可按 `industry` / `room_size` / `budget_level` 过滤并返回合理命中
- [ ] 中文 query「女装 20㎡ 三点布光 爱图仕」能召回设备+方案
- [ ] PDF 导入路径：上传 → 切块 → 向量化 → 可检索
- [ ] Embedding 失败整批回滚；向量库不可达返回 degraded
- [ ] CI 全绿，不依赖外网密钥与真实 Qdrant

---

## 9. 开放问题

1. 本地嵌入式路径是否需要定时 snapshot 到 OSS，还是本地盘足够？
2. 知识库是否需要软删除与审核状态（`pending_review`）？建议 P5 再加。
3. 设备价格是否存精确数值还是仅 price_band？当前仅 band，精确价走运营人工。
