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
from datetime import datetime, timezone
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
                role           TEXT NOT NULL DEFAULT 'user',   -- 'user' | 'admin'
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
    content: str,
    tool_events: list[dict[str, Any]] | None = None,
) -> None:
    """追加一条对话消息。"""
    now = _now()
    events_json = json.dumps(tool_events, ensure_ascii=False) if tool_events else None
    with _connect() as conn:
        conn.execute(
            'INSERT INTO messages (session_id, role, content, tool_events, created_at) VALUES (?, ?, ?, ?, ?)',
            (session_id, role, content, events_json, now),
        )


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
        msg: dict[str, Any] = {'role': r['role'], 'content': r['content']}
        if r['tool_events']:
            msg['tool_events'] = json.loads(r['tool_events'])
        result.append(msg)
    return result


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


def list_users() -> list[dict[str, Any]]:
    """列出所有用户（不含 password_hash），按创建时间倒序。"""
    with _connect() as conn:
        rows = conn.execute(
            'SELECT id, username, role, created_at FROM users ORDER BY id ASC'
        ).fetchall()
    return [dict(r) for r in rows]


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


def list_deliveries(user_id: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """列出交付物（不含 markdown 正文，避免列表过重）。可按 user_id 筛选。"""
    with _connect() as conn:
        if user_id is None:
            rows = conn.execute(
                '''SELECT d.id, d.session_id, d.user_id, d.customer_name, d.created_at,
                          u.username AS owner_username
                   FROM deliveries d LEFT JOIN users u ON d.user_id = u.id
                   ORDER BY d.id DESC LIMIT ?''',
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                '''SELECT d.id, d.session_id, d.user_id, d.customer_name, d.created_at,
                          u.username AS owner_username
                   FROM deliveries d LEFT JOIN users u ON d.user_id = u.id
                   WHERE d.user_id = ?
                   ORDER BY d.id DESC LIMIT ?''',
                (user_id, limit),
            ).fetchall()
    return [dict(r) for r in rows]


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
