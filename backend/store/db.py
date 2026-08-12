"""SQLite 持久化层。

两张表：
- sessions: 会话级 form state（跨会话恢复用）
- messages: 对话历史

单文件 SQLite 足够 MVP 并发量。无 ORM，直接 sqlite3。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / 'data' / 'ics.db'


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')  # 并发读不阻塞
    return conn


def init_db() -> None:
    """建表（幂等）。应用启动时调一次。

    注意：sessions 表在 auth 改造中加了 user_id 列。老库（无 user_id）通过
    DROP+CREATE 清掉——按设计决策"老会话清掉，必须登录后重新创建"。
    """
    with _connect() as conn:
        # 用户表
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                username       TEXT UNIQUE NOT NULL,
                password_hash  TEXT NOT NULL,
                role           TEXT NOT NULL DEFAULT 'user',   -- 'user' | 'admin' | 'guest'
                created_at     TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     TEXT NOT NULL,
                role           TEXT NOT NULL,       -- 'user' | 'ai'
                content        TEXT NOT NULL,
                tool_events    TEXT,                -- JSON，AI 消息附带的事件（填了哪些字段等）
                created_at     TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);

            CREATE TABLE IF NOT EXISTS deliveries (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     TEXT NOT NULL,
                user_id        INTEGER NOT NULL,
                customer_name  TEXT,
                markdown       TEXT NOT NULL,
                created_at     TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_deliveries_user ON deliveries(user_id);

            CREATE TABLE IF NOT EXISTS chat_requests (
                request_id       TEXT PRIMARY KEY,
                session_id       TEXT NOT NULL,
                user_id          INTEGER NOT NULL,
                message          TEXT NOT NULL,
                updates_json     TEXT,
                status           TEXT NOT NULL,
                final_payload    TEXT,
                error_code       TEXT,
                created_at       TEXT NOT NULL,
                updated_at       TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_chat_requests_session
                ON chat_requests(session_id);
        ''')

        # sessions 表：检测老结构（无 user_id），DROP 重建
        cols = [r[1] for r in conn.execute('PRAGMA table_info(sessions)').fetchall()]
        if 'user_id' not in cols:
            conn.execute('DROP TABLE IF EXISTS sessions')
            conn.execute('''
                CREATE TABLE sessions (
                    session_id     TEXT PRIMARY KEY,
                    user_id        INTEGER NOT NULL,
                    form_state     TEXT NOT NULL,
                    created_at     TEXT NOT NULL,
                    updated_at     TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            # sessions 重建后 messages 也清掉（外键指向的 session 已不存在）
            conn.execute('DELETE FROM messages')

        # 旧库兼容：messages 表可能缺 tool_events 列
        cols = [r[1] for r in conn.execute('PRAGMA table_info(messages)').fetchall()]
        if 'tool_events' not in cols:
            conn.execute('ALTER TABLE messages ADD COLUMN tool_events TEXT')

        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_users_role_created
            ON users(role, created_at)
        ''')
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_sessions_user_updated
            ON sessions(user_id, updated_at)
        ''')


# ── Session ──────────────────────────────────────────────────

def create_session(user_id: int, form_state: dict[str, Any]) -> str:
    """新建会话（绑定 user_id），返回 session_id。"""
    session_id = uuid.uuid4().hex[:12]
    now = _now()
    with _connect() as conn:
        conn.execute(
            'INSERT INTO sessions (session_id, user_id, form_state, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
            (session_id, user_id, json.dumps(form_state, ensure_ascii=False), now, now),
        )
    return session_id


def get_session(session_id: str) -> dict[str, Any] | None:
    """取会话记录（含 user_id 与 form_state）。不存在返回 None。

    返回结构：{'user_id': int, 'form_state': dict}
    """
    with _connect() as conn:
        row = conn.execute(
            'SELECT user_id, form_state FROM sessions WHERE session_id = ?', (session_id,)
        ).fetchone()
    if row is None:
        return None
    return {'user_id': row['user_id'], 'form_state': json.loads(row['form_state'])}


def save_session(session_id: str, form_state: dict[str, Any]) -> None:
    """更新会话的 form_state（ON CONFLICT 更新已存在记录）。"""
    now = _now()
    with _connect() as conn:
        conn.execute(
            'UPDATE sessions SET form_state = ?, updated_at = ? WHERE session_id = ?',
            (json.dumps(form_state, ensure_ascii=False), now, session_id),
        )


# ── Messages ─────────────────────────────────────────────────

def add_message(
    session_id: str,
    role: str,
    content: str | list[dict[str, Any]],
    tool_events: list[dict[str, Any]] | None = None,
) -> int:
    """追加一条对话消息，返回消息 id。

    content 为纯字符串时存原值（兼容旧数据），为 list 时 JSON 序列化（图片 content block 数组）。
    """
    now = _now()
    events_json = json.dumps(tool_events, ensure_ascii=False) if tool_events else None
    content_str = json.dumps(content, ensure_ascii=False) if isinstance(content, list) else content
    with _connect() as conn:
        cursor = conn.execute(
            'INSERT INTO messages (session_id, role, content, tool_events, created_at) VALUES (?, ?, ?, ?, ?)',
            (session_id, role, content_str, events_json, now),
        )
    return int(cursor.lastrowid)


def get_messages(
    session_id: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """取最近 limit 条会话消息，并按时间正序返回。"""
    with _connect() as conn:
        rows = conn.execute(
            '''SELECT role, content, tool_events FROM messages
               WHERE session_id = ? ORDER BY id DESC LIMIT ?''',
            (session_id, limit),
        ).fetchall()
    rows.reverse()
    result = []
    for r in rows:
        raw = r['content']
        try:
            parsed = json.loads(raw)
            content: str | list[dict[str, Any]] = parsed if isinstance(parsed, list) else raw
        except (json.JSONDecodeError, TypeError):
            content = raw
        msg: dict[str, Any] = {'role': r['role'], 'content': content}
        if r['tool_events']:
            msg['tool_events'] = json.loads(r['tool_events'])
        result.append(msg)
    return result


# ── Stream chat requests ──────────────────────────────────────

def begin_chat_request(
    request_id: str,
    session_id: str,
    user_id: int,
    message: str,
    updates: list[dict[str, Any]] | None,
    images: list[str] | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """创建或取得流式请求。返回 new/completed/running/conflict。"""
    now = _now()
    updates_json = json.dumps(updates, ensure_ascii=False) if updates is not None else None

    with _connect() as conn:
        images_json = json.dumps(images, ensure_ascii=False) if images else None

        row = conn.execute(
            '''SELECT session_id, user_id, message, updates_json, status, final_payload
               FROM chat_requests WHERE request_id = ?''',
            (request_id,),
        ).fetchone()

        if row is None:
            conn.execute(
                '''INSERT INTO chat_requests
                   (request_id, session_id, user_id, message, updates_json, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'running', ?, ?)''',
                (request_id, session_id, user_id, message, updates_json, now, now),
            )
            return 'new', None

        if (
            row['session_id'] != session_id
            or row['user_id'] != user_id
            or row['message'] != message
            or row['updates_json'] != updates_json
        ):
            return 'conflict', None

        if row['status'] == 'completed' and row['final_payload']:
            return 'completed', json.loads(row['final_payload'])

        if row['status'] == 'running':
            return 'running', None

        conn.execute(
            '''UPDATE chat_requests
               SET status = 'running', error_code = NULL, updated_at = ?
               WHERE request_id = ?''',
            (now, request_id),
        )
        return 'new', None


def fail_chat_request(request_id: str, error_code: str) -> None:
    """标记未完成流式请求为失败，使其可使用同一 request_id 重试。"""
    with _connect() as conn:
        conn.execute(
            '''UPDATE chat_requests
               SET status = 'failed', error_code = ?, updated_at = ?
               WHERE request_id = ? AND status = 'running' ''',
            (error_code, _now(), request_id),
        )


def persist_chat_completion(
    request_id: str,
    session_id: str,
    form_state: dict[str, Any],
    user_message: str,
    assistant_reply: str,
    tool_events: list[dict[str, Any]],
    done_payload: dict[str, Any],
    images: list[str] | None = None,
) -> int:
    """原子保存聊天最终状态并完成幂等请求。"""
    now = _now()
    # 用户消息：有图片时存 content block 数组的 JSON
    user_content: str | list[dict[str, Any]] = user_message
    if images:
        user_content = [{'type': 'text', 'text': user_message or '请分析这张图片'}]
        for uri in images:
            try:
                header, data_str = uri.split(',', 1)
                mime = header.split(':')[1].split(';')[0]
            except (IndexError, ValueError):
                mime = 'image/png'
                data_str = uri
            user_content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': mime, 'data': data_str}})
    user_content_str = json.dumps(user_content, ensure_ascii=False) if isinstance(user_content, list) else user_content
    with _connect() as conn:
        conn.execute(
            'UPDATE sessions SET form_state = ?, updated_at = ? WHERE session_id = ?',
            (json.dumps(form_state, ensure_ascii=False), now, session_id),
        )
        conn.execute(
            'INSERT INTO messages (session_id, role, content, tool_events, created_at) VALUES (?, ?, ?, ?, ?)',
            (session_id, 'user', user_content_str, None, now),
        )
        cursor = conn.execute(
            'INSERT INTO messages (session_id, role, content, tool_events, created_at) VALUES (?, ?, ?, ?, ?)',
            (
                session_id,
                'assistant',
                assistant_reply,
                json.dumps(tool_events, ensure_ascii=False) if tool_events else None,
                now,
            ),
        )
        assistant_message_id = int(cursor.lastrowid)
        final_payload = {
            **done_payload,
            'assistant_message_id': assistant_message_id,
        }
        updated = conn.execute(
            '''UPDATE chat_requests
               SET status = 'completed', final_payload = ?, error_code = NULL, updated_at = ?
               WHERE request_id = ? AND status = 'running' ''',
            (json.dumps(final_payload, ensure_ascii=False), now, request_id),
        )
        if updated.rowcount != 1:
            raise RuntimeError('chat request is not running')

    return assistant_message_id


# ── Users ──────────────────────────────────────────────────────

def create_user(username: str, password_hash: str, role: str = 'user') -> int:
    """新建用户，返回 user.id。username 唯一，冲突抛 sqlite3.IntegrityError。"""
    now = _now()
    with _connect() as conn:
        cur = conn.execute(
            'INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)',
            (username, password_hash, role, now),
        )
        return int(cur.lastrowid)


def get_user_by_username(username: str) -> dict[str, Any] | None:
    """按用户名查用户。不存在返回 None。"""
    with _connect() as conn:
        row = conn.execute(
            'SELECT id, username, password_hash, role, created_at FROM users WHERE username = ?',
            (username,),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    """按 id 查用户。不存在返回 None。"""
    with _connect() as conn:
        row = conn.execute(
            'SELECT id, username, password_hash, role, created_at FROM users WHERE id = ?',
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def count_admins() -> int:
    """返回数据库中的管理员总数。"""
    with _connect() as conn:
        row = conn.execute(
            '''
            SELECT COUNT(*)
            FROM users
            WHERE role = 'admin'
            '''
        ).fetchone()

    return int(row[0])


def get_user_detail(
    user_id: int,
) -> dict[str, Any] | None:
    """返回不含密码哈希的用户详情和交付物数量。"""
    with _connect() as conn:
        row = conn.execute(
            '''
            SELECT
                u.id,
                u.username,
                u.role,
                u.created_at,
                COUNT(d.id) AS delivery_count
            FROM users u
            LEFT JOIN deliveries d
                ON d.user_id = u.id
            WHERE u.id = ?
            GROUP BY
                u.id,
                u.username,
                u.role,
                u.created_at
            ''',
            (user_id,),
        ).fetchone()

    return dict(row) if row else None


_USER_UPDATE_COLUMNS = {
    'username',
    'password_hash',
    'role',
}


def update_user(
    user_id: int,
    changes: dict[str, Any],
) -> dict[str, Any] | None:
    """修改用户允许更新的字段，返回更新后的安全详情。"""
    safe_changes = {
        key: value
        for key, value in changes.items()
        if key in _USER_UPDATE_COLUMNS
    }

    if not safe_changes:
        return get_user_detail(user_id)

    assignments = ', '.join(
        f'{column} = ?'
        for column in safe_changes
    )
    params = [
        *safe_changes.values(),
        user_id,
    ]

    with _connect() as conn:
        cursor = conn.execute(
            f'''
            UPDATE users
            SET {assignments}
            WHERE id = ?
            ''',
            params,
        )

        if cursor.rowcount == 0:
            return None

    return get_user_detail(user_id)


def delete_user(user_id: int) -> bool:
    """删除用户，并在同一事务中清理关联数据。"""
    with _connect() as conn:
        exists = conn.execute(
            '''
            SELECT 1
            FROM users
            WHERE id = ?
            ''',
            (user_id,),
        ).fetchone()

        if exists is None:
            return False

        conn.execute(
            '''
            DELETE FROM messages
            WHERE session_id IN (
                SELECT session_id
                FROM sessions
                WHERE user_id = ?
            )
            ''',
            (user_id,),
        )
        conn.execute(
            '''
            DELETE FROM chat_requests
            WHERE user_id = ?
            ''',
            (user_id,),
        )
        conn.execute(
            '''
            DELETE FROM deliveries
            WHERE user_id = ?
            ''',
            (user_id,),
        )
        conn.execute(
            '''
            DELETE FROM sessions
            WHERE user_id = ?
            ''',
            (user_id,),
        )
        conn.execute(
            '''
            DELETE FROM users
            WHERE id = ?
            ''',
            (user_id,),
        )

    return True


def cleanup_expired_guests(
    max_idle_hours: int = 24,
    *,
    now: datetime | None = None,
) -> int:
    """删除超过指定闲置时间的游客及其全部关联数据。"""
    reference_time = now or datetime.now(timezone.utc)
    cutoff = (
        reference_time
        - timedelta(hours=max_idle_hours)
    ).isoformat()

    with _connect() as conn:
        conn.execute('''
            CREATE TEMP TABLE expired_guest_ids (
                id INTEGER PRIMARY KEY
            )
        ''')
        conn.execute(
            '''
            INSERT INTO expired_guest_ids (id)
            SELECT u.id
            FROM users u
            WHERE u.role = 'guest'
              AND u.created_at < ?
              AND NOT EXISTS (
                  SELECT 1
                  FROM sessions s
                  WHERE s.user_id = u.id
                    AND s.updated_at >= ?
              )
            ''',
            (cutoff, cutoff),
        )

        expired_count = conn.execute(
            'SELECT COUNT(*) FROM expired_guest_ids'
        ).fetchone()[0]

        if expired_count == 0:
            return 0

        conn.execute('''
            DELETE FROM messages
            WHERE session_id IN (
                SELECT s.session_id
                FROM sessions s
                JOIN expired_guest_ids e
                  ON e.id = s.user_id
            )
        ''')
        conn.execute('''
            DELETE FROM chat_requests
            WHERE user_id IN (
                SELECT id
                FROM expired_guest_ids
            )
        ''')
        conn.execute('''
            DELETE FROM deliveries
            WHERE user_id IN (
                SELECT id
                FROM expired_guest_ids
            )
        ''')
        conn.execute('''
            DELETE FROM sessions
            WHERE user_id IN (
                SELECT id
                FROM expired_guest_ids
            )
        ''')
        conn.execute('''
            DELETE FROM users
            WHERE id IN (
                SELECT id
                FROM expired_guest_ids
            )
        ''')

    return int(expired_count)


# users 列表允许排序的字段白名单（防 SQL 注入：列名不能参数化）
_USER_SORT_COLUMNS = {'id', 'username', 'created_at'}


def list_users(
    search: str | None = None,
    sort_by: str = 'id',
    order: str = 'asc',
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """列出用户并返回全局管理员数量。"""
    sort_col = (
        sort_by
        if sort_by in _USER_SORT_COLUMNS
        else 'id'
    )
    direction = (
        'DESC'
        if order.lower() == 'desc'
        else 'ASC'
    )
    page = max(page, 1)
    size = max(size, 1)
    offset = (page - 1) * size

    conditions = [
        "role != 'guest'",
    ]

    params: list[Any] = []

    if search:
        conditions.append(
            'username LIKE ?'
        )

        params.append(
            f'%{search}%'
        )

    where = (
        'WHERE '
        + ' AND '.join(conditions)
    )

    with _connect() as conn:
        admin_count = conn.execute(
            '''
            SELECT COUNT(*)
            FROM users
            WHERE role = 'admin'
            '''
        ).fetchone()[0]

        total = conn.execute(
            f'''
            SELECT COUNT(*)
            FROM users
            {where}
            ''',
            params,
        ).fetchone()[0]

        rows = conn.execute(
            f'''
            SELECT
                id,
                username,
                role,
                created_at
            FROM users
            {where}
            ORDER BY {sort_col} {direction}
            LIMIT ? OFFSET ?
            ''',
            [
                *params,
                size,
                offset,
            ],
        ).fetchall()

    return {
        'items': [
            dict(row)
            for row in rows
        ],
        'total': total,
        'admin_count': admin_count,
        'page': page,
        'size': size,
    }


# ── Deliveries（交付物持久化，仅 markdown） ───────────────────

def create_delivery(
    session_id: str,
    user_id: int,
    customer_name: str | None,
    markdown: str,
) -> int:
    """落库一条交付物，返回 delivery.id。"""
    now = _now()
    with _connect() as conn:
        cur = conn.execute(
            '''INSERT INTO deliveries (session_id, user_id, customer_name, markdown, created_at)
               VALUES (?, ?, ?, ?, ?)''',
            (session_id, user_id, customer_name, markdown, now),
        )
        return int(cur.lastrowid)


def get_delivery_by_session(
    session_id: str,
) -> dict[str, Any] | None:
    """获取会话已经发送的最新一条交付记录。"""
    with _connect() as conn:
        row = conn.execute(
            '''
            SELECT
                d.id,
                d.session_id,
                d.user_id,
                d.customer_name,
                d.markdown,
                d.created_at,
                u.username AS owner_username
            FROM deliveries d
            LEFT JOIN users u
                ON d.user_id = u.id
            WHERE d.session_id = ?
            ORDER BY d.id DESC
            LIMIT 1
            ''',
            (session_id,),
        ).fetchone()

    return dict(row) if row else None


# deliveries 列表允许排序的字段白名单（防 SQL 注入：列名不能参数化）。
# JOIN users 后需带表名前缀避免歧义。
_DELIVERY_SORT_COLUMNS = {'id': 'd.id', 'customer_name': 'd.customer_name', 'created_at': 'd.created_at'}


def list_deliveries(
    user_id: int | None = None,
    search: str | None = None,
    sort_by: str = 'id',
    order: str = 'desc',
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """列出交付物（不含 markdown 正文），支持用户筛选/搜索/排序/分页。

    - user_id: 按归属用户筛选，None 不过滤
    - search: 按 customer_name 或 owner_username 模糊匹配
    - sort_by: id | customer_name | created_at（白名单外回退 id）
    - order: asc | desc（默认 desc，最新在前）
    - page/size: 从 1 开始的分页，返回 {items, total, page, size}
    """
    sort_col = _DELIVERY_SORT_COLUMNS.get(sort_by, 'd.id')
    direction = 'DESC' if order.lower() == 'desc' else 'ASC'
    page = max(page, 1)
    size = max(size, 1)
    offset = (page - 1) * size

    clauses: list[str] = []
    params: list[Any] = []
    if user_id is not None:
        clauses.append('d.user_id = ?')
        params.append(user_id)
    if search:
        clauses.append('(d.customer_name LIKE ? OR u.username LIKE ?)')
        params.extend([f'%{search}%', f'%{search}%'])
    where = f'WHERE {" AND ".join(clauses)}' if clauses else ''

    with _connect() as conn:
        total = conn.execute(
            f'''SELECT COUNT(*) FROM deliveries d LEFT JOIN users u ON d.user_id = u.id {where}''',
            params,
        ).fetchone()[0]
        rows = conn.execute(
            f'''SELECT d.id, d.session_id, d.user_id, d.customer_name, d.created_at,
                      u.username AS owner_username
               FROM deliveries d LEFT JOIN users u ON d.user_id = u.id
               {where}
               ORDER BY {sort_col} {direction} LIMIT ? OFFSET ?''',
            [*params, size, offset],
        ).fetchall()
    return {'items': [dict(r) for r in rows], 'total': total, 'page': page, 'size': size}


def get_delivery(delivery_id: int) -> dict[str, Any] | None:
    """取单条交付物（含 markdown 正文）。不存在返回 None。"""
    with _connect() as conn:
        row = conn.execute(
            '''SELECT d.id, d.session_id, d.user_id, d.customer_name, d.markdown, d.created_at,
                      u.username AS owner_username
               FROM deliveries d LEFT JOIN users u ON d.user_id = u.id
               WHERE d.id = ?''',
            (delivery_id,),
        ).fetchone()
    return dict(row) if row else None


_DELIVERY_UPDATE_COLUMNS = {
    'customer_name',
    'markdown',
}


def update_delivery(
    delivery_id: int,
    changes: dict[str, Any],
) -> dict[str, Any] | None:
    """修改交付物允许更新的字段。"""
    safe_changes = {
        key: value
        for key, value in changes.items()
        if key in _DELIVERY_UPDATE_COLUMNS
    }

    if not safe_changes:
        return get_delivery(delivery_id)

    assignments = ', '.join(
        f'{column} = ?'
        for column in safe_changes
    )
    params = [
        *safe_changes.values(),
        delivery_id,
    ]

    with _connect() as conn:
        cursor = conn.execute(
            f'''
            UPDATE deliveries
            SET {assignments}
            WHERE id = ?
            ''',
            params,
        )

        if cursor.rowcount == 0:
            return None

    return get_delivery(delivery_id)


def delete_delivery(delivery_id: int) -> bool:
    """删除指定交付物，不影响用户和会话。"""
    with _connect() as conn:
        cursor = conn.execute(
            '''
            DELETE FROM deliveries
            WHERE id = ?
            ''',
            (delivery_id,),
        )

    return cursor.rowcount > 0
