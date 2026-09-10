# Backend — ICS

AI 对话采集 + 交付物生成后端。FastAPI + LLM Agent，SQLite 持久化。

详细上手指南见[根目录 README](../README.md)，这里是要点。

## 启动

```bash
cp .env.example .env          # 填入 LLM_API_KEY
uv sync --extra dev
uv run uvicorn api.app:app --reload
```

需要 Python ≥ 3.12，推荐用 [uv](https://docs.astral.sh/uv/)。

## 测试

```bash
uv run pytest
```

## 结构

| 目录 | 职责 |
|---|---|
| `agent/` | LLM 调用（Anthropic 兼容端点）、tool-use 循环、表单状态机 |
| `api/` | FastAPI 路由（`app.py`：session / chat / generate / admin） |
| `survey/` | 表单 schema 单一真相源 + codegen（生成前端 `schema.json`） |
| `store/` | SQLite 持久化（`db.py`：sessions / messages，无 ORM） |
| `delivery/` | 交付物生成（markdown / excel / word） |
| `knowledge/` | F1 向量知识库（Qdrant hybrid 检索 / ingest / mapping） |
| `tests/` | pytest（`conftest.py` 自动 init_db，API 测试 mock LLM） |

## 知识库（F1）

```bash
# 本地无 Docker：内存库 + mock embedding
export QDRANT_URI=memory:// EMBEDDING_PROVIDER=mock RERANK_PROVIDER=identity
uv run python scripts/seed_knowledge.py

# 本地嵌入式（持久化，零 Docker）
export QDRANT_URI=./data/qdrant EMBEDDING_PROVIDER=dashscope DASHSCOPE_API_KEY=...
uv run --extra qdrant python scripts/seed_knowledge.py

# 服务端（单容器）
docker compose -f ../deploy/qdrant.yml up -d
export QDRANT_URI=http://localhost:6333 EMBEDDING_PROVIDER=dashscope DASHSCOPE_API_KEY=...
uv run --extra qdrant python scripts/seed_knowledge.py
uv run --extra qdrant python scripts/ingest_knowledge.py path/to/docs.json
```

## 改了表单 schema 后

```bash
uv run python -m survey.export    # 重新生成 frontend/schema.json
```
