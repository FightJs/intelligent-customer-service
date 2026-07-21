"""FastAPI 应用 + 4 个端点。

端点：
- POST   /api/session          创建会话，返回 session_id + 初始 form_state + 开场白
- GET    /api/session/{id}     取回会话 form_state（跨会话恢复）
- POST   /api/chat             普通 POST 对话（非 SSE），返回 JSON
- POST   /api/generate/{type}  生成交付物（markdown/excel/word）

chat 端点接入 agent.run_agent，返回 { reply, tool_events, form_state, form_complete }。
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from agent.gather import initial_greeting
from agent.loop import run_agent
from delivery.markdown import generate_markdown
from delivery.excel import generate_excel
from delivery.word import generate_word
from store import db
from survey.state import create_initial_state, to_dict, from_dict


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title='ICS Backend', version='0.2.0', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_methods=['*'],
    allow_headers=['*'],
)


# ── 请求/响应模型 ─────────────────────────────────────────────

class SessionResponse(BaseModel):
    session_id: str
    form_state: dict
    greeting: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    history: list[dict] | None = None


class ChatResponse(BaseModel):
    reply: str
    tool_events: list[dict]
    form_state: dict
    form_complete: bool
    suggestions: list[dict] = []


# ── 端点 ──────────────────────────────────────────────────────

@app.post('/api/session', response_model=SessionResponse)
def create_session() -> SessionResponse:
    """创建新会话，生成开场白。"""
    state = create_initial_state()
    session_id = db.create_session(to_dict(state))
    greeting = initial_greeting(state)
    return SessionResponse(
        session_id=session_id,
        form_state=to_dict(state),
        greeting=greeting,
    )


@app.get('/api/session/{session_id}', response_model=SessionResponse)
def get_session(session_id: str) -> SessionResponse:
    """取回会话 form_state（跨会话恢复）。无开场白（已开始过）。"""
    data = db.get_session(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail='session not found')
    return SessionResponse(session_id=session_id, form_state=data, greeting='')


@app.post('/api/chat', response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """普通 POST 对话（非 SSE）。"""
    data = db.get_session(req.session_id)
    if data is None:
        raise HTTPException(status_code=404, detail='session not found')

    state = from_dict(data)
    result = run_agent(state, req.message, req.history)

    # 持久化
    db.save_session(req.session_id, to_dict(result.state))
    db.add_message(req.session_id, 'user', req.message)
    db.add_message(req.session_id, 'assistant', result.reply)

    # tool_events 转 dict
    events_dict = [asdict(e) for e in result.tool_events]

    return ChatResponse(
        reply=result.reply,
        tool_events=events_dict,
        form_state=to_dict(result.state),
        form_complete=result.form_complete,
        suggestions=result.suggestions,
    )


@app.post('/api/generate/{doc_type}')
def generate(
    doc_type: Literal['markdown', 'excel', 'word'],
    session_id: str,
) -> Response:
    """生成交付物，返回文件流下载。

    - markdown: text/markdown
    - excel:   application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
    - word:    application/vnd.openxmlformats-officedocument.wordprocessingml.document
    """
    data = db.get_session(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail='session not found')

    state = from_dict(data)

    # 文件名用品牌名（如有）
    brand = state.sections.get('customer', None)
    brand_name = ''
    if brand:
        brand_field = brand.fields.get('brand')
        if brand_field and brand_field.type == 'text' and brand_field.value:
            brand_name = brand_field.value

    if doc_type == 'markdown':
        content = generate_markdown(state).encode('utf-8')
        media_type = 'text/markdown; charset=utf-8'
        suffix = 'md'
    elif doc_type == 'excel':
        content = generate_excel(state)
        media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        suffix = 'xlsx'
    elif doc_type == 'word':
        content = generate_word(state)
        media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        suffix = 'docx'
    else:
        raise HTTPException(status_code=400, detail=f'unknown type: {doc_type}')

    filename = f'{brand_name}直播间搭建方案.{suffix}' if brand_name else f'交付物.{suffix}'
    # 中文文件名 RFC 5987 编码
    from urllib.parse import quote
    encoded = quote(filename)

    return Response(
        content=content,
        media_type=media_type,
        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{encoded}"},
    )
