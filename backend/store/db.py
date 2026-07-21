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
    """建表（幂等）。应用启动时调一次。"""
    with _connect() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id     TEXT PRIMARY KEY,
                form_state     TEXT NOT NULL,
                created_at     TEXT NOT NULL,
                updated_at     TEXT NOT NULL
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
        ''')
        # 旧库兼容：messages 表可能缺 tool_events 列
        cols = [r[1] for r in conn.execute('PRAGMA table_info(messages)').fetchall()]
        if 'tool_events' not in cols:
            conn.execute('ALTER TABLE messages ADD COLUMN tool_events TEXT')


# ── Session ──────────────────────────────────────────────────

def create_session(form_state: dict[str, Any]) -> str:
    """新建会话，返回 session_id。"""
    session_id = uuid.uuid4().hex[:12]
    now = _now()
    with _connect() as conn:
        conn.execute(
            'INSERT INTO sessions (session_id, form_state, created_at, updated_at) VALUES (?, ?, ?, ?)',
            (session_id, json.dumps(form_state, ensure_ascii=False), now, now),
        )
    return session_id


def get_session(session_id: str) -> dict[str, Any] | None:
    """取会话的 form_state。不存在返回 None。"""
    with _connect() as conn:
        row = conn.execute(
            'SELECT form_state FROM sessions WHERE session_id = ?', (session_id,)
        ).fetchone()
    if row is None:
        return None
    return json.loads(row['form_state'])


def save_session(session_id: str, form_state: dict[str, Any]) -> None:
    """更新会话的 form_state（upsert）。"""
    now = _now()
    with _connect() as conn:
        conn.execute(
            '''INSERT INTO sessions (session_id, form_state, created_at, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET form_state = excluded.form_state, updated_at = excluded.updated_at''',
            (session_id, json.dumps(form_state, ensure_ascii=False), now, now),
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


def get_messages(session_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """取会话的对话历史（按时间正序）。"""
    with _connect() as conn:
        rows = conn.execute(
            '''SELECT role, content, tool_events FROM messages
               WHERE session_id = ? ORDER BY id ASC LIMIT ?''',
            (session_id, limit),
        ).fetchall()
    result = []
    for r in rows:
        msg: dict[str, Any] = {'role': r['role'], 'content': r['content']}
        if r['tool_events']:
            msg['tool_events'] = json.loads(r['tool_events'])
        result.append(msg)
    return result
