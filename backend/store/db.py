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

from store import uploads

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
                submission_kind TEXT NOT NULL DEFAULT 'complete',
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

            CREATE TABLE IF NOT EXISTS chat_usage (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL,
                ip_address     TEXT NOT NULL,
                image_count    INTEGER NOT NULL DEFAULT 0,
                request_key    TEXT,
                created_at     TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_chat_usage_user_time
                ON chat_usage(user_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_chat_usage_ip_time
                ON chat_usage(ip_address, created_at);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_chat_usage_request
                ON chat_usage(request_key)
                WHERE request_key IS NOT NULL;

            CREATE TABLE IF NOT EXISTS skill_runs (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_run_id  TEXT NOT NULL,
                skill            TEXT NOT NULL,
                status           TEXT NOT NULL,
                attempt          INTEGER DEFAULT 1,
                input_json       TEXT,
                output_json      TEXT,
                cost_cny         REAL DEFAULT 0,
                started_at       TEXT,
                finished_at      TEXT,
                error            TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_skill_runs_pipeline
                ON skill_runs(pipeline_run_id, skill);

            CREATE TABLE IF NOT EXISTS artifacts (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_run_id  TEXT NOT NULL,
                kind             TEXT NOT NULL,
                path             TEXT NOT NULL,
                sha256           TEXT,
                meta_json        TEXT,
                created_at       TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_artifacts_pipeline_kind
                ON artifacts(pipeline_run_id, kind);
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

        delivery_cols = [
            row[1]
            for row in conn.execute('PRAGMA table_info(deliveries)').fetchall()
        ]
        if 'submission_kind' not in delivery_cols:
            conn.execute(
                "ALTER TABLE deliveries ADD COLUMN submission_kind TEXT NOT NULL DEFAULT 'complete'"
            )

        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_users_role_created
            ON users(role, created_at)
        ''')
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_sessions_user_updated
            ON sessions(user_id, updated_at)
        ''')

        # 智能交付管线（F1–F5）
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id             TEXT PRIMARY KEY,
                session_id     TEXT NOT NULL,
                delivery_id    INTEGER,
                user_id        INTEGER NOT NULL,
                status         TEXT NOT NULL,
                current_skill  TEXT,
                created_at     TEXT NOT NULL,
                updated_at     TEXT NOT NULL,
                error          TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_pipeline_runs_session
                ON pipeline_runs(session_id);
            CREATE INDEX IF NOT EXISTS idx_pipeline_runs_user
                ON pipeline_runs(user_id, created_at);

            CREATE TABLE IF NOT EXISTS skill_runs (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_run_id  TEXT NOT NULL,
                skill            TEXT NOT NULL,
                status           TEXT NOT NULL,
                attempt          INTEGER DEFAULT 1,
                input_json       TEXT,
                output_json      TEXT,
                cost_cny         REAL DEFAULT 0,
                started_at       TEXT,
                finished_at      TEXT,
                error            TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_skill_runs_pipeline
                ON skill_runs(pipeline_run_id, skill);

            CREATE TABLE IF NOT EXISTS artifacts (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_run_id  TEXT NOT NULL,
                kind             TEXT NOT NULL,
                path             TEXT NOT NULL,
                sha256           TEXT,
                meta_json        TEXT,
                created_at       TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_artifacts_pipeline_kind
                ON artifacts(pipeline_run_id, kind);

            CREATE TABLE IF NOT EXISTS knowledge_docs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                filename     TEXT NOT NULL,
                category     TEXT NOT NULL,
                status       TEXT NOT NULL,
                chunks       INTEGER NOT NULL DEFAULT 0,
                path         TEXT,
                industry     TEXT,
                scene        TEXT,
                source       TEXT,
                note         TEXT,
                created_at   TEXT NOT NULL,
                updated_at   TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_knowledge_docs_status
                ON knowledge_docs(status, updated_at);
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


def _form_has_content(form_state: dict[str, Any]) -> bool:
    sections = form_state.get('sections') or {}
    for section in sections.values():
        for field in (section.get('fields') or {}).values():
            if not isinstance(field, dict):
                continue
            value = field.get('value')
            if isinstance(value, str) and value.strip():
                return True
            if isinstance(value, (list, dict)) and value:
                return True
    return bool(form_state.get('completed'))


def get_latest_session_with_content(user_id: int) -> dict[str, Any] | None:
    """取该用户最近有内容的会话（有消息或表单有填写）。空壳会话跳过。"""
    with _connect() as conn:
        rows = conn.execute(
            '''
            SELECT s.session_id, s.form_state, s.updated_at,
                   (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.session_id) AS msg_count
            FROM sessions s
            WHERE s.user_id = ?
            ORDER BY s.updated_at DESC
            LIMIT 30
            ''',
            (user_id,),
        ).fetchall()
    for row in rows:
        form_state = json.loads(row['form_state'])
        if row['msg_count'] > 0 or _form_has_content(form_state):
            return {
                'session_id': row['session_id'],
                'form_state': form_state,
                'updated_at': row['updated_at'],
            }
    return None


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


def reserve_chat_usage(
    user_id: int,
    ip_address: str,
    image_count: int,
    *,
    per_minute_limit: int,
    daily_message_limit: int,
    daily_image_limit: int,
    request_key: str | None = None,
    now: datetime | None = None,
) -> str | None:
    """原子检查并预占一次聊天额度。

    返回 None 表示成功；超限时返回 rate/messages/images。
    request_key 用于流式请求重放，确保同一请求只计费一次。
    """
    current = now or datetime.now(timezone.utc)
    minute_cutoff = (current - timedelta(minutes=1)).isoformat()
    day_start = current.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    ).isoformat()
    cleanup_cutoff = (current - timedelta(days=2)).isoformat()
    created_at = current.isoformat()
    safe_image_count = max(0, image_count)

    with _connect() as conn:
        conn.execute('BEGIN IMMEDIATE')

        if request_key is not None:
            existing = conn.execute(
                'SELECT 1 FROM chat_usage WHERE request_key = ?',
                (request_key,),
            ).fetchone()
            if existing is not None:
                return None

        conn.execute(
            'DELETE FROM chat_usage WHERE created_at < ?',
            (cleanup_cutoff,),
        )

        user_minute_count = conn.execute(
            '''SELECT COUNT(*) FROM chat_usage
               WHERE user_id = ? AND created_at >= ?''',
            (user_id, minute_cutoff),
        ).fetchone()[0]
        ip_minute_count = conn.execute(
            '''SELECT COUNT(*) FROM chat_usage
               WHERE ip_address = ? AND created_at >= ?''',
            (ip_address, minute_cutoff),
        ).fetchone()[0]

        if max(user_minute_count, ip_minute_count) >= per_minute_limit:
            return 'rate'

        user_daily_messages = conn.execute(
            '''SELECT COUNT(*) FROM chat_usage
               WHERE user_id = ? AND created_at >= ?''',
            (user_id, day_start),
        ).fetchone()[0]
        ip_daily_messages = conn.execute(
            '''SELECT COUNT(*) FROM chat_usage
               WHERE ip_address = ? AND created_at >= ?''',
            (ip_address, day_start),
        ).fetchone()[0]

        if max(user_daily_messages, ip_daily_messages) >= daily_message_limit:
            return 'messages'

        user_daily_images = conn.execute(
            '''SELECT COALESCE(SUM(image_count), 0) FROM chat_usage
               WHERE user_id = ? AND created_at >= ?''',
            (user_id, day_start),
        ).fetchone()[0]
        ip_daily_images = conn.execute(
            '''SELECT COALESCE(SUM(image_count), 0) FROM chat_usage
               WHERE ip_address = ? AND created_at >= ?''',
            (ip_address, day_start),
        ).fetchone()[0]

        if (
            max(user_daily_images, ip_daily_images)
            + safe_image_count
            > daily_image_limit
        ):
            return 'images'

        conn.execute(
            '''INSERT INTO chat_usage
               (user_id, ip_address, image_count, request_key, created_at)
               VALUES (?, ?, ?, ?, ?)''',
            (
                user_id,
                ip_address,
                safe_image_count,
                request_key,
                created_at,
            ),
        )

    return None


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
            DELETE FROM chat_usage
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

    expired_session_ids: list[str] = []

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

        expired_session_ids = [
            row[0]
            for row in conn.execute('''
                SELECT s.session_id
                FROM sessions s
                JOIN expired_guest_ids e
                  ON e.id = s.user_id
            ''').fetchall()
        ]

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
            DELETE FROM chat_usage
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

    uploads.delete_session_uploads(
        expired_session_ids,
    )

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
    submission_kind: str = 'complete',
) -> int:
    """落库一条交付物，返回 delivery.id。"""
    now = _now()
    with _connect() as conn:
        cur = conn.execute(
            '''INSERT INTO deliveries
               (session_id, user_id, customer_name, markdown, submission_kind, created_at)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (session_id, user_id, customer_name, markdown, submission_kind, now),
        )
        return int(cur.lastrowid)


def create_delivery_and_complete_session(
    session_id: str,
    user_id: int,
    customer_name: str | None,
    markdown: str,
    submission_kind: str,
    form_state: dict[str, Any],
) -> tuple[int, bool]:
    """在同一事务内创建唯一交付物并把会话标记为已提交。

    ``BEGIN IMMEDIATE`` 让并发提交按顺序执行；后到的请求会读到首条
    交付记录并直接复用，避免重复订单和“订单已建但问卷未锁定”。
    """
    now = _now()
    serialized_state = json.dumps(form_state, ensure_ascii=False)
    with _connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        existing = conn.execute(
            '''SELECT id FROM deliveries
               WHERE session_id = ?
               ORDER BY id ASC
               LIMIT 1''',
            (session_id,),
        ).fetchone()
        if existing is not None:
            return int(existing['id']), False

        inserted = conn.execute(
            '''INSERT INTO deliveries
               (session_id, user_id, customer_name, markdown, submission_kind, created_at)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (
                session_id,
                user_id,
                customer_name,
                markdown,
                submission_kind,
                now,
            ),
        )
        updated = conn.execute(
            '''UPDATE sessions
               SET form_state = ?, updated_at = ?
               WHERE session_id = ? AND user_id = ?''',
            (serialized_state, now, session_id, user_id),
        )
        if updated.rowcount != 1:
            raise RuntimeError('session not found while completing delivery')
        return int(inserted.lastrowid), True


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
                d.submission_kind,
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
            f'''SELECT d.id, d.session_id, d.user_id, d.customer_name,
                       d.submission_kind, d.created_at,
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
            '''SELECT d.id, d.session_id, d.user_id, d.customer_name, d.markdown,
                      d.submission_kind, d.created_at,
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


# ── Knowledge docs（F1 运营侧文档状态） ─────────────────────

def create_knowledge_doc(
    *,
    filename: str,
    category: str,
    status: str = 'pending',
    path: str | None = None,
    industry: str | None = None,
    scene: str | None = None,
    note: str | None = None,
) -> int:
    now = _now()
    with _connect() as conn:
        cursor = conn.execute(
            '''
            INSERT INTO knowledge_docs
                (filename, category, status, chunks, path, industry, scene, note, created_at, updated_at)
            VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
            ''',
            (filename, category, status, path, industry, scene, note, now, now),
        )
    return int(cursor.lastrowid)


def update_knowledge_doc(doc_id: int, **fields: Any) -> bool:
    allowed = {'status', 'chunks', 'path', 'note', 'source', 'industry', 'scene'}
    safe = {k: v for k, v in fields.items() if k in allowed}
    if not safe:
        return False
    safe['updated_at'] = _now()
    assignments = ', '.join(f'{k} = ?' for k in safe)
    with _connect() as conn:
        cursor = conn.execute(
            f'UPDATE knowledge_docs SET {assignments} WHERE id = ?',
            (*safe.values(), doc_id),
        )
    return cursor.rowcount > 0


def get_knowledge_doc(doc_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            'SELECT * FROM knowledge_docs WHERE id = ?', (doc_id,)
        ).fetchone()
    return dict(row) if row else None


def list_knowledge_docs(
    *,
    status: str | None = None,
    category: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append('status = ?')
        params.append(status)
    if category:
        clauses.append('category = ?')
        params.append(category)
    where = f'WHERE {" AND ".join(clauses)}' if clauses else ''
    with _connect() as conn:
        rows = conn.execute(
            f'''
            SELECT * FROM knowledge_docs
            {where}
            ORDER BY updated_at DESC
            LIMIT ?
            ''',
            (*params, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Pipeline runs ─────────────────────────────────────────────

PIPELINE_SKILLS = ('plan_document', 'preview_images', 'preview_video', 'final_package')
PIPELINE_ACTIVE_STATUSES = ('pending', 'running')
PIPELINE_TERMINAL_STATUSES = ('ready', 'ready_with_warnings', 'failed', 'cancelled')


def create_pipeline_run(
    *,
    session_id: str,
    user_id: int,
    delivery_id: int | None = None,
    status: str = 'pending',
) -> str:
    """创建 pipeline_run，返回 run id。"""
    run_id = f'pr_{uuid.uuid4().hex[:16]}'
    now = _now()
    with _connect() as conn:
        conn.execute(
            '''
            INSERT INTO pipeline_runs
                (id, session_id, delivery_id, user_id, status, current_skill, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (run_id, session_id, delivery_id, user_id, status, PIPELINE_SKILLS[0], now, now),
        )
    return run_id


def get_pipeline_run(pipeline_run_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            'SELECT * FROM pipeline_runs WHERE id = ?',
            (pipeline_run_id,),
        ).fetchone()
    return dict(row) if row else None


def update_pipeline_run(
    pipeline_run_id: str,
    *,
    status: str | None = None,
    current_skill: str | None = None,
    error: str | None = None,
    delivery_id: int | None = None,
) -> None:
    fields: list[str] = ['updated_at = ?']
    values: list[Any] = [_now()]
    if status is not None:
        fields.append('status = ?')
        values.append(status)
    if current_skill is not None:
        fields.append('current_skill = ?')
        values.append(current_skill)
    if error is not None:
        fields.append('error = ?')
        values.append(error)
    if delivery_id is not None:
        fields.append('delivery_id = ?')
        values.append(delivery_id)
    values.append(pipeline_run_id)
    with _connect() as conn:
        conn.execute(
            f'UPDATE pipeline_runs SET {", ".join(fields)} WHERE id = ?',
            values,
        )


def list_pipeline_runs(
    *,
    user_id: int | None = None,
    session_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if user_id is not None:
        clauses.append('user_id = ?')
        values.append(user_id)
    if session_id is not None:
        clauses.append('session_id = ?')
        values.append(session_id)
    where = f'WHERE {" AND ".join(clauses)}' if clauses else ''
    values.append(limit)
    with _connect() as conn:
        rows = conn.execute(
            f'''
            SELECT * FROM pipeline_runs
            {where}
            ORDER BY created_at DESC
            LIMIT ?
            ''',
            values,
        ).fetchall()
    return [dict(row) for row in rows]


def count_active_pipeline_runs(user_id: int) -> int:
    with _connect() as conn:
        row = conn.execute(
            f'''
            SELECT COUNT(*) AS n FROM pipeline_runs
            WHERE user_id = ? AND status IN ({','.join('?' * len(PIPELINE_ACTIVE_STATUSES))})
            ''',
            (user_id, *PIPELINE_ACTIVE_STATUSES),
        ).fetchone()
    return int(row['n']) if row else 0


def latest_skill_status_map(pipeline_run_id: str) -> dict[str, str]:
    """每个 skill 最近一次 run 的 status。"""
    with _connect() as conn:
        rows = conn.execute(
            '''
            SELECT skill, status FROM skill_runs sr
            WHERE pipeline_run_id = ?
              AND id = (
                SELECT MAX(id) FROM skill_runs
                WHERE pipeline_run_id = sr.pipeline_run_id AND skill = sr.skill
              )
            ''',
            (pipeline_run_id,),
        ).fetchall()
    return {row['skill']: row['status'] for row in rows}


# ── Pipeline skill_runs / artifacts ─────────────────────────

def start_skill_run(
    *,
    pipeline_run_id: str,
    skill: str,
    input_json: dict[str, Any] | None = None,
) -> int:
    """开始一次 skill 运行，返回 run id。"""
    now = _now()
    with _connect() as conn:
        cursor = conn.execute(
            '''
            INSERT INTO skill_runs (
                pipeline_run_id, skill, status, attempt,
                input_json, started_at
            ) VALUES (?, ?, 'running', 1, ?, ?)
            ''',
            (
                pipeline_run_id,
                skill,
                json.dumps(input_json, ensure_ascii=False) if input_json else None,
                now,
            ),
        )
        return int(cursor.lastrowid)


def finish_skill_run_latest(
    *,
    pipeline_run_id: str,
    skill: str,
    status: str,
    output_json: dict[str, Any] | None = None,
    cost_cny: float = 0.0,
    error: str | None = None,
) -> None:
    """结束该 pipeline+skill 最近一条 running 记录。"""
    now = _now()
    with _connect() as conn:
        row = conn.execute(
            '''
            SELECT id FROM skill_runs
            WHERE pipeline_run_id = ? AND skill = ? AND status = 'running'
            ORDER BY id DESC LIMIT 1
            ''',
            (pipeline_run_id, skill),
        ).fetchone()
        if row is None:
            conn.execute(
                '''
                INSERT INTO skill_runs (
                    pipeline_run_id, skill, status, output_json,
                    cost_cny, started_at, finished_at, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    pipeline_run_id,
                    skill,
                    status,
                    json.dumps(output_json, ensure_ascii=False) if output_json else None,
                    cost_cny,
                    now,
                    now,
                    error,
                ),
            )
            return
        conn.execute(
            '''
            UPDATE skill_runs
            SET status = ?, output_json = ?, cost_cny = ?,
                finished_at = ?, error = ?
            WHERE id = ?
            ''',
            (
                status,
                json.dumps(output_json, ensure_ascii=False) if output_json else None,
                cost_cny,
                now,
                error,
                row['id'],
            ),
        )


def list_skill_runs(pipeline_run_id: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            '''
            SELECT * FROM skill_runs
            WHERE pipeline_run_id = ?
            ORDER BY id ASC
            ''',
            (pipeline_run_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def upsert_artifact(
    *,
    pipeline_run_id: str,
    kind: str,
    path: str,
    sha256: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    now = _now()
    with _connect() as conn:
        conn.execute(
            '''
            INSERT INTO artifacts (
                pipeline_run_id, kind, path, sha256, meta_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                pipeline_run_id,
                kind,
                path,
                sha256,
                json.dumps(meta, ensure_ascii=False) if meta else None,
                now,
            ),
        )


def list_artifacts(pipeline_run_id: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            '''
            SELECT * FROM artifacts
            WHERE pipeline_run_id = ?
            ORDER BY id ASC
            ''',
            (pipeline_run_id,),
        ).fetchall()
    return [dict(row) for row in rows]
