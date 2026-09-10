"""Admin 知识库文档：上传落盘 → 切块向量化 → 状态落 SQLite。"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Literal

from knowledge.config import get_config
from knowledge.embedding import get_embedder
from knowledge.ingest import ingest_pdf
from knowledge.models import COLLECTION_VERTICAL
from knowledge.store import get_store
from store import db

logger = logging.getLogger(__name__)

KNOWLEDGE_UPLOAD_ROOT = Path(__file__).resolve().parents[1] / 'data' / 'knowledge_uploads'

DocCategory = Literal['equipment', 'scheme', 'vertical']

CATEGORY_TO_COLLECTION = {
    'equipment': 'equipment_specs',
    'scheme': 'setup_schemes',
    'vertical': COLLECTION_VERTICAL,
}

_CATEGORY_TO_DB = {v: k for k, v in CATEGORY_TO_COLLECTION.items()}


def _collection_to_category(collection: str) -> str:
    return _CATEGORY_TO_DB.get(collection, 'vertical')


def save_knowledge_pdf(filename: str, content: bytes) -> Path:
    if not filename.lower().endswith('.pdf'):
        raise ValueError('仅支持 PDF 文件')
    if not content:
        raise ValueError('空文件')
    KNOWLEDGE_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    path = KNOWLEDGE_UPLOAD_ROOT / f'{uuid.uuid4().hex[:12]}.pdf'
    path.write_bytes(content)
    return path


def create_pending_doc(
    *,
    filename: str,
    category: DocCategory,
    path: str | None = None,
    industry: str | None = None,
    scene: str | None = None,
) -> dict[str, Any]:
    doc_id = db.create_knowledge_doc(
        filename=filename,
        category=category,
        status='pending',
        path=path,
        industry=industry,
        scene=scene,
        note='已上传，等待切块与向量化',
    )
    rec = db.get_knowledge_doc(doc_id)
    assert rec is not None
    return rec


def run_pdf_ingest(doc_id: int) -> dict[str, Any]:
    """同步执行一条文档的入库。失败状态写 failed，异常继续抛给调用方。"""
    rec = db.get_knowledge_doc(doc_id)
    if rec is None:
        raise LookupError(f'knowledge doc {doc_id} not found')
    if rec['status'] == 'ready':
        return rec

    path = rec.get('path')
    if not path or not Path(path).exists():
        db.update_knowledge_doc(
            doc_id, status='failed', note='文件不存在，请重新上传'
        )
        raise FileNotFoundError(path or f'knowledge doc {doc_id} path missing')

    db.update_knowledge_doc(doc_id, status='embedding', note='切块完成，正在写入向量库')
    collection = CATEGORY_TO_COLLECTION.get(rec['category'], COLLECTION_VERTICAL)
    try:
        result = ingest_pdf(
            path,
            collection=collection,  # type: ignore[arg-type]
            industry=rec.get('industry') or 'all',
            scene=rec.get('scene') or '',
            store=get_store(get_config()),
            embedder=get_embedder(get_config()),
        )
    except Exception as exc:
        logger.exception('knowledge ingest failed doc_id=%s', doc_id)
        db.update_knowledge_doc(doc_id, status='failed', note=str(exc)[:500])
        raise

    db.update_knowledge_doc(
        doc_id,
        status='ready',
        chunks=result['chunks'],
        source=result['source'],
        note='入库完成',
    )
    updated = db.get_knowledge_doc(doc_id)
    assert updated is not None
    return updated


def retry_doc(doc_id: int) -> dict[str, Any]:
    rec = db.get_knowledge_doc(doc_id)
    if rec is None:
        raise LookupError(f'knowledge doc {doc_id} not found')
    if rec['status'] == 'ready':
        return rec
    if not rec.get('path'):
        raise ValueError('缺少原始文件，无法重试')
    return run_pdf_ingest(doc_id)


def list_docs(
    *,
    status: str | None = None,
    category: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    return db.list_knowledge_docs(status=status, category=category, limit=limit)


def remove_upload(path: str | None) -> None:
    if not path:
        return
    p = Path(path)
    if p.exists() and KNOWLEDGE_UPLOAD_ROOT in p.parents:
        p.unlink(missing_ok=True)
