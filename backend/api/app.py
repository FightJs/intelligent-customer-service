"""FastAPI 应用 + 4 个端点。

端点：
- POST   /api/session          创建会话，返回 session_id + 初始 form_state + 开场白
- GET    /api/session/{id}     取回会话 form_state（跨会话恢复）
- POST   /api/chat             SSE 流式对话
- POST   /api/generate/{type}  生成交付物（markdown/excel/word）

chat 端点接入 agent.run_turn_stream，SSE 事件：
- tool:  字段更新事件（前端更新表单）
- token: AI 回复文本片段（流式）
- done:  本轮结束，附带最新 form_state
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agent.gather import run_turn_stream, initial_greeting
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


class GenerateResponse(BaseModel):
    type: str
    filename: str
    content: str


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


@app.post('/api/chat')
def chat(req: ChatRequest) -> EventSourceResponse:
    """SSE 流式对话。"""
    data = db.get_session(req.session_id)
    if data is None:
        raise HTTPException(status_code=404, detail='session not found')

    state = from_dict(data)

    async def event_generator():
        full_reply = []
        all_events = []
        for kind, payload in run_turn_stream(state, req.message, req.history):
            if kind == 'events':
                all_events = [asdict(e) for e in payload]
                yield {
                    'event': 'tool',
                    'data': json.dumps({'events': all_events}, ensure_ascii=False),
                }
            elif kind == 'token':
                full_reply.append(payload)
                yield {
                    'event': 'token',
                    'data': json.dumps({'text': payload}, ensure_ascii=False),
                }
            elif kind == 'done':
                # 持久化更新后的 state
                db.save_session(req.session_id, to_dict(payload.state))
                # 存对话消息
                db.add_message(req.session_id, 'user', req.message)
                db.add_message(
                    req.session_id, 'assistant', payload.reply,
                    tool_events=all_events,
                )
                yield {
                    'event': 'done',
                    'data': json.dumps({
                        'form_state': to_dict(payload.state),
                        'form_complete': payload.form_complete,
                    }, ensure_ascii=False),
                }

    return EventSourceResponse(event_generator())


@app.post('/api/generate/{doc_type}', response_model=GenerateResponse)
def generate(
    doc_type: Literal['markdown', 'excel', 'word'],
    session_id: str,
) -> GenerateResponse:
    """生成交付物。阶段 3 接入 DeliveryService。"""
    data = db.get_session(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail='session not found')

    suffix = {'markdown': 'md', 'excel': 'xlsx', 'word': 'docx'}[doc_type]
    return GenerateResponse(
        type=doc_type,
        filename=f'交付物.{suffix}',
        content=f'[阶段 3 待实现] {doc_type} 交付物生成',
    )
