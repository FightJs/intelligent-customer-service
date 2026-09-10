"""artifacts 路径与 skill_runs 持久化辅助。"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from store import db


def get_artifact_root() -> Path:
    raw = os.getenv('ARTIFACT_ROOT', '').strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / 'data' / 'artifacts'


def plan_paths(pipeline_run_id: str, root: Path | None = None) -> tuple[Path, Path, Path]:
    base = (root or get_artifact_root()) / pipeline_run_id / 'docs'
    return base, base / 'plan.json', base / 'plan.pdf'


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def try_reuse_plan(pipeline_run_id: str, root: Path | None = None) -> dict[str, Any] | None:
    """已有成功 plan.json 时返回复用上下文，否则 None。"""
    docs_dir, plan_json_path, plan_pdf_path = plan_paths(pipeline_run_id, root)
    if not plan_json_path.exists():
        return None
    try:
        plan = json.loads(plan_json_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(plan, dict) or not plan.get('summary'):
        return None
    return {
        'plan': plan,
        'plan_json_path': str(plan_json_path),
        'pdf_path': str(plan_pdf_path) if plan_pdf_path.exists() else None,
        'docs_dir': docs_dir,
    }


def persist_plan_artifacts(
    pipeline_run_id: str,
    plan: dict[str, Any],
    *,
    root: Path | None = None,
    pdf_bytes: bytes | None = None,
    word_bytes: bytes | None = None,
) -> tuple[str, str | None]:
    docs_dir, plan_json_path, plan_pdf_path = plan_paths(pipeline_run_id, root)
    docs_dir.mkdir(parents=True, exist_ok=True)
    plan_json_path.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    pdf_path: str | None = None
    if pdf_bytes is not None:
        plan_pdf_path.write_bytes(pdf_bytes)
        pdf_path = str(plan_pdf_path)
        db.upsert_artifact(
            pipeline_run_id=pipeline_run_id,
            kind='plan_pdf',
            path=pdf_path,
            sha256=sha256_file(plan_pdf_path),
        )
    elif word_bytes is not None:
        word_path = docs_dir / 'plan.docx'
        word_path.write_bytes(word_bytes)
        db.upsert_artifact(
            pipeline_run_id=pipeline_run_id,
            kind='plan_docx',
            path=str(word_path),
            sha256=sha256_file(word_path),
        )

    db.upsert_artifact(
        pipeline_run_id=pipeline_run_id,
        kind='plan_json',
        path=str(plan_json_path),
        sha256=sha256_file(plan_json_path),
    )
    return str(plan_json_path), pdf_path
