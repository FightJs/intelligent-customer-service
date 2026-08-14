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

import asyncio
import json
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Literal
from uuid import UUID, uuid4

from dotenv import load_dotenv
from anthropic import APIConnectionError, APIStatusError
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, field_validator, model_validator

from agent.auth import (
    create_token,
    get_admin_user,
    get_current_user,
    hash_password,
    verify_password,
)
from agent.gather import initial_greeting
from agent.flow import (
    form_complete,
    next_unfilled_field,
)
from agent.loop import (
    AgentStreamDelta,
    AgentStreamResult,
    AgentStreamStatus,
    AgentStreamToolEvent,
    run_agent,
    run_agent_stream,
)
from agent.tools import apply_updates, ToolEvent
from delivery.markdown import generate_markdown
from delivery.excel import generate_excel
from delivery.word import generate_word
from store import db
from store.uploads import SavedImage, UploadError, is_data_uri, save_upload
from survey.state import create_initial_state, to_dict, from_dict

load_dotenv()

logger = logging.getLogger(__name__)
LLM_BALANCE_ERROR = 'LLM 服务余额不足，请联系管理员充值后重试。'
LLM_CONNECTION_ERROR = 'LLM 服务暂时无法连接，请检查网络或联系管理员。'

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


IMAGE_MIME_WHITELIST = {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}


def _parse_data_uri(uri: str) -> tuple[str, str]:
    """解析 data URI,返回 (mime_type, base64_data)。非法格式抛 400。"""
    if not uri.startswith('data:'):
        raise HTTPException(status_code=400, detail='图片格式无效,需要 data URI')
    try:
        header, data = uri.split(',', 1)
        mime = header.split(':')[1].split(';')[0]
    except (IndexError, ValueError):
        raise HTTPException(status_code=400, detail='图片 data URI 格式无效')
    if mime not in IMAGE_MIME_WHITELIST:
        raise HTTPException(status_code=400, detail=f'不支持的图片格式: {mime}')
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail='图片过大,单张不能超过 15MB')
    return mime, data


def _persist_user_content(message: str, images: list[str] | None) -> str | list[dict]:
    """构造存入 messages 表的 user content（保留原图 base64，供会话恢复时回显）。"""
    if not images:
        return message or ''
    content: list[dict] = [{'type': 'text', 'text': message or '请分析这张图片'}]
    for uri in images:
        mime, data = _parse_data_uri(uri)
        content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': mime, 'data': data}})
    return content


def _save_images(session_id: str, images: list[str] | None) -> list[SavedImage] | None:
    """上传图片缩放落盘，返回 SavedImage 列表；非法图片抛 400。"""
    if not images:
        return None
    saved = []
    for uri in images:
        try:
            saved.append(save_upload(session_id, uri))
        except UploadError as exc:
            raise HTTPException(status_code=400, detail=f'图片无效: {exc}') from exc
    return saved


def _normalize_image_updates(session_id: str, updates: list[dict] | None) -> None:
    """updates 直推的 image 字段值若是 data URI，落盘并替换为图片 id（原地修改）。"""
    if not updates:
        return
    for upd in updates:
        value = upd.get('value')
        if not isinstance(value, list):
            continue
        normalized = []
        changed = False
        for item in value:
            if is_data_uri(item):
                try:
                    normalized.append(save_upload(session_id, item).id)
                except UploadError as exc:
                    raise HTTPException(status_code=400, detail=f'图片无效: {exc}') from exc
                changed = True
            else:
                normalized.append(item)
        if changed:
            upd['value'] = normalized


class ChatRequest(BaseModel):
    session_id: str
    message: str
    history: list[dict] | None = None
    updates: list[dict] | None = None
    images: list[str] | None = None


class ChatResponse(BaseModel):
    reply: str
    tool_events: list[dict]
    form_state: dict
    form_complete: bool
    suggestions: list[dict] = []


class ChatStreamRequest(BaseModel):
    request_id: UUID
    session_id: str
    message: str
    history: list[dict] | None = None
    updates: list[dict] | None = None
    images: list[str] | None = None

    @field_validator('message')
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if len(value) > 8000:
            raise ValueError('message 不能超过 8000 个字符')
        return value

    @model_validator(mode='after')
    def require_message_or_images(self) -> 'ChatStreamRequest':
        if not self.message.strip() and not self.images:
            raise ValueError('message 和 images 不能同时为空')
        return self


class OrderRequest(BaseModel):
    session_id: str


class OrderResponse(BaseModel):
    delivery_id: int
    sent: bool
    message: str


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


@app.post(
    '/api/auth/guest',
    response_model=AuthResponse,
)
def guest_login() -> AuthResponse:
    """创建独立游客身份，用于快速体验。"""

    db.cleanup_expired_guests(
        max_idle_hours=24,
    )

    guest_id = uuid4().hex

    username = (
        f'guest_{guest_id[:10]}'
    )

    user_id = db.create_user(
        username,
        hash_password(guest_id),
        role='guest',
    )

    user = db.get_user_by_id(user_id)
    token = create_token(user)

    return AuthResponse(
        token=token,
        user={
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
        },
    )


@app.get('/api/auth/me', response_model=UserResponse)
def me(current: dict = Depends(get_current_user)) -> UserResponse:
    """返回当前登录用户信息。"""
    return UserResponse(id=current['id'], username=current['username'], role=current['role'])


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
    state = create_initial_state(
        mode=(
            'quick'
            if current['role'] == 'guest'
            else 'full'
        ),
    )
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

    # 上传图片落盘（缩放），LLM 通过 id 引用；updates 里的 data URI 同样转 id
    saved_images = _save_images(req.session_id, req.images)
    _normalize_image_updates(req.session_id, req.updates)

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
        result = run_agent(state, req.message, history, saved_images)
    except APIStatusError as exc:
        if exc.status_code != 402:
            raise
        logger.warning('LLM chat unavailable because the account balance is insufficient')
        raise HTTPException(status_code=503, detail=LLM_BALANCE_ERROR) from exc
    except APIConnectionError as exc:
        logger.warning('LLM chat unavailable because the service cannot be reached')
        raise HTTPException(status_code=503, detail=LLM_CONNECTION_ERROR) from exc

    # tool_events 转 dict（updates 事件 + agent 事件）
    events_dict = [asdict(e) for e in (update_events + result.tool_events)]

    # 持久化（用户消息有图片时存 content block 数组的 JSON,保持兼容）
    user_content: str | list[dict] = _persist_user_content(req.message, req.images)
    db.save_session(req.session_id, to_dict(result.state))
    db.add_message(req.session_id, 'user', user_content)
    db.add_message(req.session_id, 'assistant', result.reply, events_dict)

    return ChatResponse(
        reply=result.reply,
        tool_events=events_dict,
        form_state=to_dict(result.state),
        form_complete=result.form_complete,
        suggestions=result.suggestions,
    )


def _encode_sse(
    request_id: str,
    sequence: int,
    event: str,
    data: dict,
) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    return (
        f'id: {request_id}:{sequence}\n'
        f'event: {event}\n'
        f'data: {payload}\n\n'
    )


@app.post('/api/chat/stream')
async def chat_stream(
    req: ChatStreamRequest,
    current: dict = Depends(get_current_user),
) -> StreamingResponse:
    """真实 LLM stream 的 SSE 聊天接口，支持 request_id 幂等回放。"""
    rec = db.get_session(req.session_id)
    if rec is None:
        raise HTTPException(status_code=404, detail='session not found')
    if rec['user_id'] != current['id'] and current['role'] != 'admin':
        raise HTTPException(status_code=403, detail='无权操作该会话')

    request_id = str(req.request_id)
    request_status, saved_payload = db.begin_chat_request(
        request_id=request_id,
        session_id=req.session_id,
        user_id=current['id'],
        message=req.message,
        updates=req.updates,
        images=req.images,
    )
    if request_status == 'running':
        raise HTTPException(status_code=409, detail='request_in_progress')
    if request_status == 'conflict':
        raise HTTPException(status_code=409, detail='request_conflict')

    async def event_generator():
        sequence = 0

        def event(name: str, data: dict) -> str:
            nonlocal sequence
            encoded = _encode_sse(request_id, sequence, name, data)
            sequence += 1
            return encoded

        yield event('start', {'request_id': request_id, 'status': 'started'})

        if request_status == 'completed':
            yield event('done', saved_payload or {})
            return

        state = from_dict(rec['form_state'])
        saved_images = _save_images(req.session_id, req.images)
        _normalize_image_updates(req.session_id, req.updates)
        update_events: list[ToolEvent] = []
        if req.updates:
            apply_updates(state, req.updates)
            for update in req.updates:
                update_events.append(ToolEvent(
                    kind='fill',
                    section_id=update['section_id'],
                    field_id=update['field_id'].split('.')[-1],
                    value=update.get('value'),
                ))
        for update_event in update_events:
            yield event('tool_event', asdict(update_event))
        history = db.get_messages(req.session_id, limit=50) or req.history
        phase = 'generating'
        try:
            result: AgentStreamResult | None = None
            async for item in run_agent_stream(state, req.message, history, saved_images):
                if item is None:
                    yield ': heartbeat\n\n'
                elif isinstance(item, AgentStreamDelta):
                    yield event('delta', {'text': item.text})
                elif isinstance(item, AgentStreamStatus):
                    phase = item.phase
                    yield event('status', {
                        'phase': item.phase,
                        'message': item.message,
                    })
                elif isinstance(item, AgentStreamToolEvent):
                    yield event('tool_event', asdict(item.event))
                elif isinstance(item, AgentStreamResult):
                    result = item

            if result is None:
                raise RuntimeError('agent stream ended without result')

            all_events = [*update_events, *result.tool_events]
            events_dict = [asdict(item) for item in all_events]
            done_payload = {
                'request_id': request_id,
                'reply': result.reply,
                'tool_events': events_dict,
                'form_state': to_dict(result.state),
                'form_complete': result.form_complete,
                'suggestions': result.suggestions,
            }
            yield event('status', {
                'phase': 'persisting',
                'message': '正在保存会话',
            })
            assistant_message_id = db.persist_chat_completion(
                request_id=request_id,
                session_id=req.session_id,
                form_state=done_payload['form_state'],
                user_message=req.message,
                assistant_reply=result.reply,
                tool_events=events_dict,
                done_payload=done_payload,
                images=req.images,
            )
            yield event('done', {
                **done_payload,
                'assistant_message_id': assistant_message_id,
            })
        except asyncio.CancelledError:
            db.fail_chat_request(request_id, 'stream_interrupted')
            raise
        except APIStatusError as exc:
            if exc.status_code == 402:
                code = 'llm_balance_insufficient'
                message = LLM_BALANCE_ERROR
                retryable = False
            else:
                code = 'llm_unavailable'
                message = '顾问暂时无法回复，请稍后重试。'
                retryable = True
            logger.warning('stream chat failed: request_id=%s code=%s', request_id, code)
            db.fail_chat_request(request_id, code)
            yield event('error', {
                'request_id': request_id,
                'code': code,
                'message': message,
                'retryable': retryable,
                'phase': phase,
            })
        except APIConnectionError:
            logger.warning('stream chat connection failed: request_id=%s', request_id)
            db.fail_chat_request(request_id, 'llm_unavailable')
            yield event('error', {
                'request_id': request_id,
                'code': 'llm_unavailable',
                'message': '顾问暂时无法回复，请稍后重试。',
                'retryable': True,
                'phase': phase,
            })
        except Exception:
            code = 'tool_failed' if phase == 'tool_call' else 'persistence_failed'
            message = (
                '表单更新失败，请重试本轮回答。'
                if code == 'tool_failed'
                else '回复生成完成，但保存失败，请重试。'
            )
            logger.exception('stream chat failed: request_id=%s code=%s', request_id, code)
            db.fail_chat_request(request_id, code)
            yield event('error', {
                'request_id': request_id,
                'code': code,
                'message': message,
                'retryable': True,
                'phase': phase,
            })

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


@app.post(
    '/api/orders',
    response_model=OrderResponse,
)
def submit_order(
    req: OrderRequest,
    current: dict = Depends(get_current_user),
) -> OrderResponse:
    """确认当前需求并发送订单。

    只有发送成功后才写入 deliveries，
    管理员后台才会看到该会话。
    """
    if current['role'] == 'guest':
        raise HTTPException(
            status_code=403,
            detail=(
                '快速体验模式不支持'
                '发送订单'
            ),
        )

    rec = db.get_session(req.session_id)

    if rec is None:
        raise HTTPException(
            status_code=404,
            detail='session not found',
        )

    if (
        rec['user_id'] != current['id']
        and current['role'] != 'admin'
    ):
        raise HTTPException(
            status_code=403,
            detail='无权发送该会话的订单',
        )

    state = from_dict(rec['form_state'])

    if not form_complete(state):
        missing = next_unfilled_field(
            state,
        )

        detail = (
            '必填信息尚未采集完成'
        )

        if missing is not None:
            _, field = missing

            detail = (
                f'{detail}：{field.label}'
            )

        raise HTTPException(
            status_code=409,
            detail=detail,
        )

    # 防止重复点击产生多条相同订单。
    existing = db.get_delivery_by_session(
        req.session_id
    )

    if existing is not None:
        return OrderResponse(
            delivery_id=existing['id'],
            sent=True,
            message='订单已经发送，请勿重复提交',
        )

    customer = state.sections.get('customer')
    customer_name = None

    if customer is not None:
        brand_field = customer.fields.get('brand')

        if (
            brand_field is not None
            and brand_field.type == 'text'
            and brand_field.value
        ):
            customer_name = brand_field.value

    # 后台的一条记录保存完整综合需求。
    markdown = generate_markdown(state)

    delivery_id = db.create_delivery(
        req.session_id,
        rec['user_id'],
        customer_name,
        markdown,
    )

    return OrderResponse(
        delivery_id=delivery_id,
        sent=True,
        message='订单发送成功',
    )


@app.post('/api/generate/{doc_type}')
def generate(
    doc_type: Literal['markdown', 'excel', 'word'],
    session_id: str,
    current: dict = Depends(get_current_user),
) -> Response:
    """临时生成文件流，不写入管理员交付物列表。

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
