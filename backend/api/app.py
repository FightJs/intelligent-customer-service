"""FastAPI 应用 + 端点。

端点：
- POST   /api/auth/register     注册（开放注册，role=user）
- POST   /api/auth/login        登录，返回 JWT
- GET    /api/auth/me           当前用户信息
- POST   /api/session           创建会话（需登录）
- GET    /api/session/{id}      取回会话 form_state（需登录 + 归属校验）
- POST   /api/chat              对话（需登录 + 归属校验）
- POST   /api/generate/{type}   生成交付物（需登录 + markdown 落库）
- GET    /api/admin/users       用户列表（admin only）
- GET    /api/admin/deliverables 交付物列表+筛选（admin only）
- GET    /api/admin/deliverables/{id} 交付物详情含 markdown（admin only）
"""
from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Literal

from dotenv import load_dotenv
from anthropic import APIStatusError
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from agent.auth import (
    create_token,
    get_admin_user,
    get_current_user,
    hash_password,
    verify_password,
)
from agent.gather import initial_greeting
from agent.loop import run_agent
from agent.tools import apply_updates, ToolEvent
from delivery.markdown import generate_markdown
from delivery.excel import generate_excel
from delivery.word import generate_word
from store import db
from survey.state import create_initial_state, to_dict, from_dict

load_dotenv()

logger = logging.getLogger(__name__)
LLM_BALANCE_ERROR = 'LLM 服务余额不足，请联系管理员充值后重试。'

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123456')  # 仅测试期默认，生产必改 env


def _seed_admin() -> None:
    """启动时确保管理员账号存在（按 env 凭证，不存在则创建）。"""
    if db.get_user_by_username(ADMIN_USERNAME) is None:
        db.create_user(ADMIN_USERNAME, hash_password(ADMIN_PASSWORD), role='admin')


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    _seed_admin()
    yield


app = FastAPI(title='ICS Backend', version='0.3.0', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_methods=['*'],
    allow_headers=['*'],
)


# ── 请求/响应模型 ─────────────────────────────────────────────

class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    role: str


class SessionResponse(BaseModel):
    session_id: str
    form_state: dict
    greeting: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    history: list[dict] | None = None
    updates: list[dict] | None = None


class ChatResponse(BaseModel):
    reply: str
    tool_events: list[dict]
    form_state: dict
    form_complete: bool
    suggestions: list[dict] = []


# ── Auth 端点 ─────────────────────────────────────────────────

@app.post('/api/auth/register', response_model=AuthResponse)
def register(req: AuthRequest) -> AuthResponse:
    """开放注册。username 唯一，重复返回 409。新用户 role 固定为 user。"""
    if db.get_user_by_username(req.username) is not None:
        raise HTTPException(status_code=409, detail='用户名已存在')
    if len(req.username) < 2 or len(req.password) < 6:
        raise HTTPException(status_code=400, detail='用户名≥2字符，密码≥6字符')
    user_id = db.create_user(req.username, hash_password(req.password), role='user')
    user = db.get_user_by_id(user_id)
    token = create_token(user)
    return AuthResponse(token=token, user={'id': user['id'], 'username': user['username'], 'role': user['role']})


@app.post('/api/auth/login', response_model=AuthResponse)
def login(req: AuthRequest) -> AuthResponse:
    """登录。用户不存在或密码错误返回 401（统一文案，防枚举）。"""
    user = db.get_user_by_username(req.username)
    if user is None or not verify_password(req.password, user['password_hash']):
        raise HTTPException(status_code=401, detail='用户名或密码错误')
    token = create_token(user)
    return AuthResponse(token=token, user={'id': user['id'], 'username': user['username'], 'role': user['role']})


@app.get('/api/auth/me', response_model=UserResponse)
def me(current: dict = Depends(get_current_user)) -> UserResponse:
    """返回当前登录用户信息。"""
    return UserResponse(id=current['id'], username=current['username'], role=current['role'])


# ── 请求/响应模型 ─────────────────────────────────────────────

class SessionResponse(BaseModel):
    session_id: str
    form_state: dict
    greeting: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    history: list[dict] | None = None
    updates: list[dict] | None = None


class ChatResponse(BaseModel):
    reply: str
    tool_events: list[dict]
    form_state: dict
    form_complete: bool
    suggestions: list[dict] = []


class AdminUserCreate(BaseModel):
    username: str
    password: str
    role: Literal['user', 'admin'] = 'user'


class AdminUserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    role: Literal['user', 'admin'] | None = None


class AdminDeliveryUpdate(BaseModel):
    customer_name: str | None = None
    markdown: str | None = None


# ── 端点 ──────────────────────────────────────────────────────

@app.post('/api/session', response_model=SessionResponse)
def create_session(current: dict = Depends(get_current_user)) -> SessionResponse:
    """创建新会话（绑定当前 user），生成开场白。"""
    state = create_initial_state()
    session_id = db.create_session(current['id'], to_dict(state))
    greeting = initial_greeting(state)
    return SessionResponse(
        session_id=session_id,
        form_state=to_dict(state),
        greeting=greeting,
    )


@app.get('/api/session/{session_id}', response_model=SessionResponse)
def get_session(session_id: str, current: dict = Depends(get_current_user)) -> SessionResponse:
    """取回会话 form_state（跨会话恢复）。校验归属：本人或 admin。"""
    rec = db.get_session(session_id)
    if rec is None:
        raise HTTPException(status_code=404, detail='session not found')
    if rec['user_id'] != current['id'] and current['role'] != 'admin':
        raise HTTPException(status_code=403, detail='无权访问该会话')
    return SessionResponse(session_id=session_id, form_state=rec['form_state'], greeting='')


@app.post('/api/chat', response_model=ChatResponse)
def chat(req: ChatRequest, current: dict = Depends(get_current_user)) -> ChatResponse:
    """普通 POST 对话（非 SSE）。校验 session 归属。"""
    rec = db.get_session(req.session_id)
    if rec is None:
        raise HTTPException(status_code=404, detail='session not found')
    if rec['user_id'] != current['id'] and current['role'] != 'admin':
        raise HTTPException(status_code=403, detail='无权操作该会话')

    state = from_dict(rec['form_state'])

    # 前端权威 updates（chip 点击）绕过 LLM 抽取，在 run_agent 前直接 apply
    update_events: list[ToolEvent] = []
    if req.updates:
        apply_updates(state, req.updates)
        for upd in req.updates:
            update_events.append(ToolEvent(
                kind='fill', section_id=upd['section_id'],
                field_id=upd['field_id'].split('.')[-1], value=upd.get('value'),
            ))

    # 从 DB 取最近 50 条历史。
    # 前端 history 仅作为空会话 fallback，DB 是权威源。
    history = db.get_messages(req.session_id, limit=50) or req.history

    try:
        result = run_agent(state, req.message, history)
    except APIStatusError as exc:
        if exc.status_code != 402:
            raise
        logger.warning('LLM chat unavailable because the account balance is insufficient')
        raise HTTPException(status_code=503, detail=LLM_BALANCE_ERROR) from exc

    # tool_events 转 dict（updates 事件 + agent 事件）
    events_dict = [asdict(e) for e in (update_events + result.tool_events)]

    # 持久化
    db.save_session(req.session_id, to_dict(result.state))
    db.add_message(req.session_id, 'user', req.message)
    db.add_message(req.session_id, 'assistant', result.reply, events_dict)

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
    current: dict = Depends(get_current_user),
) -> Response:
    """生成交付物，返回文件流下载。markdown 同步落库到 deliveries。

    - markdown: text/markdown
    - excel:   application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
    - word:    application/vnd.openxmlformats-officedocument.wordprocessingml.document
    """
    rec = db.get_session(session_id)
    if rec is None:
        raise HTTPException(status_code=404, detail='session not found')
    if rec['user_id'] != current['id'] and current['role'] != 'admin':
        raise HTTPException(status_code=403, detail='无权操作该会话')

    state = from_dict(rec['form_state'])

    # 文件名用品牌名（如有）
    brand = state.sections.get('customer', None)
    brand_name = ''
    if brand:
        brand_field = brand.fields.get('brand')
        if brand_field and brand_field.type == 'text' and brand_field.value:
            brand_name = brand_field.value

    if doc_type == 'markdown':
        md_text = generate_markdown(state)
        content = md_text.encode('utf-8')
        media_type = 'text/markdown; charset=utf-8'
        suffix = 'md'
        # 仅 markdown 落库（excel/word 实时重算，不存二进制）
        db.create_delivery(session_id, rec['user_id'], brand_name or None, md_text)
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


# ── Admin 端点（仅 role=admin 可访问） ────────────────────────

@app.get('/api/admin/users')
def admin_list_users(
    search: str | None = None,
    sort_by: str = 'id',
    order: str = 'asc',
    page: int = 1,
    size: int = 20,
    admin: dict = Depends(get_admin_user),
) -> dict:
    """列出用户，支持搜索、排序和分页。"""
    return db.list_users(
        search=search,
        sort_by=sort_by,
        order=order,
        page=page,
        size=size,
    )


@app.post(
    '/api/admin/users',
    status_code=201,
)
def admin_create_user(
    req: AdminUserCreate,
    admin: dict = Depends(get_admin_user),
) -> dict:
    """由管理员创建普通用户或管理员。"""
    username = req.username.strip()

    if len(username) < 2:
        raise HTTPException(
            status_code=400,
            detail='用户名至少需要 2 个字符',
        )

    if len(req.password) < 6:
        raise HTTPException(
            status_code=400,
            detail='密码至少需要 6 个字符',
        )

    try:
        user_id = db.create_user(
            username,
            hash_password(req.password),
            role=req.role,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail='用户名已存在',
        ) from exc

    detail = db.get_user_detail(user_id)

    if detail is None:
        raise HTTPException(
            status_code=500,
            detail='创建用户后读取失败',
        )

    return detail


@app.get('/api/admin/users/{user_id}')
def admin_get_user(
    user_id: int,
    admin: dict = Depends(get_admin_user),
) -> dict:
    """获取用户详情和交付物数量。"""
    detail = db.get_user_detail(user_id)

    if detail is None:
        raise HTTPException(
            status_code=404,
            detail='用户不存在',
        )

    return detail


@app.patch('/api/admin/users/{user_id}')
def admin_update_user(
    user_id: int,
    req: AdminUserUpdate,
    admin: dict = Depends(get_admin_user),
) -> dict:
    """修改用户名、密码或角色。"""
    target = db.get_user_by_id(user_id)

    if target is None:
        raise HTTPException(
            status_code=404,
            detail='用户不存在',
        )

    submitted_fields = req.model_fields_set

    if not submitted_fields:
        raise HTTPException(
            status_code=400,
            detail='至少需要提供一个修改字段',
        )

    changes: dict = {}

    if 'username' in submitted_fields:
        username = (
            req.username.strip()
            if req.username is not None
            else ''
        )

        if len(username) < 2:
            raise HTTPException(
                status_code=400,
                detail='用户名至少需要 2 个字符',
            )

        changes['username'] = username

    if 'password' in submitted_fields:
        if (
            req.password is None
            or len(req.password) < 6
        ):
            raise HTTPException(
                status_code=400,
                detail='密码至少需要 6 个字符',
            )

        changes['password_hash'] = hash_password(
            req.password,
        )

    if 'role' in submitted_fields:
        if req.role is None:
            raise HTTPException(
                status_code=400,
                detail='角色不能为空',
            )

        if (
            target['role'] == 'admin'
            and req.role != 'admin'
            and db.count_admins() <= 1
        ):
            raise HTTPException(
                status_code=409,
                detail='不能降级系统最后一个管理员',
            )

        changes['role'] = req.role

    try:
        updated = db.update_user(
            user_id,
            changes,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail='用户名已存在',
        ) from exc

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail='用户不存在',
        )

    return updated


@app.delete(
    '/api/admin/users/{user_id}',
    status_code=204,
)
def admin_delete_user(
    user_id: int,
    admin: dict = Depends(get_admin_user),
) -> Response:
    """删除用户及其会话、消息和交付物。"""
    target = db.get_user_by_id(user_id)

    if target is None:
        raise HTTPException(
            status_code=404,
            detail='用户不存在',
        )

    if target['id'] == admin['id']:
        raise HTTPException(
            status_code=409,
            detail='不能删除当前登录的管理员',
        )

    if (
        target['role'] == 'admin'
        and db.count_admins() <= 1
    ):
        raise HTTPException(
            status_code=409,
            detail='不能删除系统最后一个管理员',
        )

    deleted = db.delete_user(user_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail='用户不存在',
        )

    return Response(status_code=204)


@app.get('/api/admin/deliverables')
def admin_list_deliverables(
    user_id: int | None = None,
    search: str | None = None,
    sort_by: str = 'id',
    order: str = 'desc',
    page: int = 1,
    size: int = 20,
    admin: dict = Depends(get_admin_user),
) -> dict:
    """列出交付物，支持筛选、搜索和分页。"""
    return db.list_deliveries(
        user_id=user_id,
        search=search,
        sort_by=sort_by,
        order=order,
        page=page,
        size=size,
    )


@app.get('/api/admin/deliverables/{delivery_id}')
def admin_get_deliverable(
    delivery_id: int,
    admin: dict = Depends(get_admin_user),
) -> dict:
    """获取包含 Markdown 正文的交付物详情。"""
    detail = db.get_delivery(delivery_id)

    if detail is None:
        raise HTTPException(
            status_code=404,
            detail='交付物不存在',
        )

    return detail


@app.patch('/api/admin/deliverables/{delivery_id}')
def admin_update_delivery(
    delivery_id: int,
    req: AdminDeliveryUpdate,
    admin: dict = Depends(get_admin_user),
) -> dict:
    """修改交付物客户名称或 Markdown 正文。"""
    submitted_fields = req.model_fields_set

    if not submitted_fields:
        raise HTTPException(
            status_code=400,
            detail='至少需要提供一个修改字段',
        )

    changes: dict = {}

    if 'customer_name' in submitted_fields:
        changes['customer_name'] = (
            req.customer_name.strip()
            if req.customer_name
            else None
        )

    if 'markdown' in submitted_fields:
        if (
            req.markdown is None
            or not req.markdown.strip()
        ):
            raise HTTPException(
                status_code=400,
                detail='Markdown 正文不能为空',
            )

        changes['markdown'] = req.markdown

    updated = db.update_delivery(
        delivery_id,
        changes,
    )

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail='交付物不存在',
        )

    return updated


@app.delete(
    '/api/admin/deliverables/{delivery_id}',
    status_code=204,
)
def admin_delete_delivery(
    delivery_id: int,
    admin: dict = Depends(get_admin_user),
) -> Response:
    """删除指定交付物。"""
    deleted = db.delete_delivery(delivery_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail='交付物不存在',
        )

    return Response(status_code=204)