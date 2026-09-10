"""skill_runs / artifacts 持久化。复用 store.db 的 SQLite 连接。"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from store import db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    return db._connect()


def start_skill_run(
    pipeline_run_id: str,
    skill: str,
    *,
    input_payload: dict[str, Any] | None = None,
    attempt: int = 1,
) -> int:
    now = _now()
    with _connect() as conn:
        cur = conn.execute(
            '''
            INSERT INTO skill_runs
                (pipeline_run_id, skill, status, attempt, input_json, started_at)
            VALUES (?, ?, 'running', ?, ?, ?)
            ''',
            (
                pipeline_run_id,
                skill,
                attempt,
                json.dumps(input_payload or {}, ensure_ascii=False),
                now,
            ),
        )
        return int(cur.lastrowid)


def finish_skill_run(
    skill_run_id: int,
    *,
    status: str,
    output: dict[str, Any] | None = None,
    cost_cny: float = 0.0,
    error: str | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            '''
            UPDATE skill_runs
            SET status = ?, output_json = ?, cost_cny = ?, finished_at = ?, error = ?
            WHERE id = ?
            ''',
            (
                status,
                json.dumps(output or {}, ensure_ascii=False),
                cost_cny,
                _now(),
                error,
                skill_run_id,
            ),
        )


def save_artifact(
    pipeline_run_id: str,
    kind: str,
    path: str,
    *,
    sha256: str | None = None,
    meta: dict[str, Any] | None = None,
) -> int:
    with _connect() as conn:
        cur = conn.execute(
            '''
            INSERT INTO artifacts
                (pipeline_run_id, kind, path, sha256, meta_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                pipeline_run_id,
                kind,
                path,
                sha256,
                json.dumps(meta or {}, ensure_ascii=False),
                _now(),
            ),
        )
        return int(cur.lastrowid)


def find_latest_video_artifact(pipeline_run_id: str) -> dict[str, Any] | None:
    """返回最近一条 video artifact（含解析后的 meta），不存在则 None。"""
    with _connect() as conn:
        row = conn.execute(
            '''
            SELECT path, sha256, meta_json, created_at
            FROM artifacts
            WHERE pipeline_run_id = ? AND kind = 'video'
            ORDER BY id DESC
            LIMIT 1
            ''',
            (pipeline_run_id,),
        ).fetchone()
    if row is None:
        return None
    meta: dict[str, Any] = {}
    if row['meta_json']:
        try:
            meta = json.loads(row['meta_json'])
        except json.JSONDecodeError:
            meta = {}
    return {
        'path': row['path'],
        'sha256': row['sha256'],
        'meta': meta,
        'created_at': row['created_at'],
    }


def video_file_usable(path: str | Path, min_bytes: int = 100_000) -> bool:
    p = Path(path)
    return p.is_file() and p.stat().st_size >= min_bytes
