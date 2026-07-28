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
| `agent/` | LLM 调用（Anthropic SDK → DeepSeek）、tool-use 循环、表单状态机 |
| `api/` | FastAPI 路由（`app.py`：session / chat / generate） |
| `survey/` | 表单 schema 单一真相源 + codegen（生成前端 `schema.json`） |
| `store/` | SQLite 持久化（`db.py`：sessions / messages，无 ORM） |
| `delivery/` | 交付物生成（markdown / excel / word） |
| `tests/` | pytest（`conftest.py` 自动 init_db，API 测试 mock LLM） |

## 改了表单 schema 后

```bash
uv run python -m survey.export    # 重新生成 frontend/schema.json
```
