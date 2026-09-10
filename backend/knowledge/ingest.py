"""知识写入：业务主键 upsert、PDF 切块、整批回滚。

幂等键（Spec §4.3）：
- 设备 brand+name+source
- 方案 scheme_name+source
- 垂类 source+chunk_index

Embedding 失败 → 整批回滚，不写半截数据。
"""
from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any, Iterable, Sequence

from knowledge.config import KnowledgeConfig, get_config
from knowledge.embedding import Embedder, EmbeddingError, get_embedder
from knowledge.models import (
    COLLECTION_EQUIPMENT,
    COLLECTION_SCHEMES,
    COLLECTION_VERTICAL,
    CollectionName,
)
from knowledge.store import VectorStore, get_store, now_ts

logger = logging.getLogger(__name__)

_HEADING_RE = re.compile(r'^(#{1,6}\s+.+|[一二三四五六七八九十]+[、.]\s*.+)$', re.M)
_CJK_CHAR_RE = re.compile(r'[一-鿿]')


def business_id(*parts: str) -> int:
    """稳定正 int64，作为向量库主键，保证同业务键可覆盖更新。"""
    raw = '|'.join(parts).encode('utf-8')
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return int(digest, 16) & 0x7FFFFFFFFFFFFFFF


def source_tag(filename: str, content: bytes | str) -> str:
    """文件名 + 内容 hash 前 8 位，便于覆盖更新。"""
    data = content if isinstance(content, bytes) else content.encode('utf-8')
    digest = hashlib.sha256(data).hexdigest()[:8]
    stem = Path(filename).name
    return f'{stem}#{digest}'


def _cjk_len(text: str) -> int:
    return len(_CJK_CHAR_RE.findall(text))


def chunk_vertical_text(
    text: str,
    *,
    industry: str,
    scene: str = '',
    min_chars: int = 200,
    max_chars: int = 500,
) -> list[str]:
    """按小标题切块，目标 200–500 汉字；块头注入行业/场景上下文。"""
    body = text.strip()
    if not body:
        return []

    parts = _HEADING_RE.split(body)
    # split 后：[前言, 标题1, 段1, 标题2, 段2, ...]
    sections: list[tuple[str, str]] = []
    preamble = parts[0].strip() if parts else ''
    if preamble:
        sections.append(('', preamble))
    i = 1
    while i + 1 < len(parts) + 1 and i < len(parts):
        title = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ''
        sections.append((title, content))
        i += 2

    if not sections:
        sections = [('', body)]

    chunks: list[str] = []
    header_bits = ['适用场景', scene or '通用', '行业', industry]
    header = f"[{' / '.join(header_bits)}]"

    for title, content in sections:
        if not content and not title:
            continue
        piece = f'{title}\n{content}'.strip() if title else content
        if not piece:
            continue
        for part in _split_by_length(piece, min_chars=min_chars, max_chars=max_chars):
            chunk = f'{header}\n{part}'.strip()
            chunks.append(chunk)
    return chunks


def _split_by_length(text: str, min_chars: int, max_chars: int) -> list[str]:
    """超长段落按句读再切，保证每块汉字数落在 [min, max] 附近。"""
    if _cjk_len(text) <= max_chars:
        return [text]

    sentences = re.split(r'(?<=[。！？；\n])', text)
    pieces: list[str] = []
    buf = ''
    for sent in sentences:
        if not sent:
            continue
        if _cjk_len(buf) + _cjk_len(sent) > max_chars and buf:
            pieces.append(buf.strip())
            buf = sent
        else:
            buf += sent
        while _cjk_len(buf) > max_chars:
            # 仍超长则硬切
            cut = buf[:max_chars]
            # 尽量在汉字边界
            pieces.append(cut.strip())
            buf = buf[max_chars:]
    if buf.strip():
        pieces.append(buf.strip())

    # 过短块与前块合并
    merged: list[str] = []
    for p in pieces:
        if merged and _cjk_len(merged[-1]) < min_chars:
            merged[-1] = (merged[-1] + p).strip()
        else:
            merged.append(p)
    return [p for p in merged if p]


def equipment_row(
    *,
    name: str,
    category: str,
    brand: str,
    price_band: str,
    room_size: str,
    industry: str,
    specs: dict[str, Any],
    text: str,
    source: str,
    updated_at: int | None = None,
) -> dict[str, Any]:
    return {
        'id': business_id(brand, name, source),
        'name': name,
        'category': category,
        'brand': brand,
        'price_band': price_band,
        'room_size': room_size,
        'industry': industry,
        'specs': specs,
        'text': text,
        'source': source,
        'updated_at': updated_at or now_ts(),
    }


def scheme_row(
    *,
    scheme_name: str,
    industry: str,
    budget_level: str,
    room_size: str,
    live_type: str,
    equipment_ids: list[Any],
    package_tiers: list[dict[str, Any]],
    layout_notes: str,
    text: str,
    source: str,
    updated_at: int | None = None,
) -> dict[str, Any]:
    return {
        'id': business_id(scheme_name, source),
        'scheme_name': scheme_name,
        'industry': industry,
        'budget_level': budget_level,
        'room_size': room_size,
        'live_type': live_type,
        'equipment_ids': equipment_ids,
        'package_tiers': package_tiers,
        'layout_notes': layout_notes,
        'text': text,
        'source': source,
        'updated_at': updated_at or now_ts(),
    }


def vertical_row(
    *,
    industry: str,
    scene: str,
    content: str,
    text: str,
    source: str,
    chunk_index: int,
    updated_at: int | None = None,
) -> dict[str, Any]:
    return {
        'id': business_id(source, str(chunk_index)),
        'industry': industry,
        'scene': scene,
        'content': content,
        'text': text[:4096],
        'source': source,
        'updated_at': updated_at or now_ts(),
    }


def _embed_rows(
    embedder: Embedder,
    rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """先全部向量化；任一失败抛 EmbeddingError，调用方不写库。"""
    texts = [str(r.get('text') or r.get('content') or '') for r in rows]
    vectors = embedder.embed(texts)
    if len(vectors) != len(rows):
        raise EmbeddingError(
            f'embedding count mismatch: got {len(vectors)}, want {len(rows)}'
        )
    embedded: list[dict[str, Any]] = []
    for row, vec in zip(rows, vectors):
        item = dict(row)
        item['dense'] = list(vec)
        embedded.append(item)
    return embedded


def ingest_rows(
    collection: CollectionName,
    rows: Sequence[dict[str, Any]],
    *,
    store: VectorStore | None = None,
    embedder: Embedder | None = None,
    config: KnowledgeConfig | None = None,
) -> int:
    """向量化后 upsert。Embedding 失败整批回滚（不写任何行）。"""
    if not rows:
        return 0
    cfg = config or get_config()
    store = store or get_store(cfg)
    embedder = embedder if embedder is not None else get_embedder(cfg)

    store.ensure_collections()
    try:
        embedded = _embed_rows(embedder, rows)
    except EmbeddingError:
        logger.exception('embedding failed, abort batch collection=%s n=%d', collection, len(rows))
        raise

    store.upsert(collection, embedded)
    return len(embedded)


def extract_pdf_text(path: str | Path) -> str:
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError('pypdf is required for PDF ingestion') from exc

    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or '')
    return '\n'.join(parts).strip()


def ingest_pdf(
    path: str | Path,
    *,
    collection: CollectionName = COLLECTION_VERTICAL,
    industry: str = 'all',
    scene: str = '',
    store: VectorStore | None = None,
    embedder: Embedder | None = None,
    config: KnowledgeConfig | None = None,
) -> dict[str, Any]:
    """上传 → 切块 → 向量化 → 可检索。

    当前垂直知识走 vertical_knowledge；设备/方案 PDF 需结构化 JSON，
    这里仅处理垂类知识切块入库。
    """
    if collection != COLLECTION_VERTICAL:
        raise ValueError('ingest_pdf currently supports vertical_knowledge only')

    pdf_path = Path(path)
    raw = pdf_path.read_bytes()
    tag = source_tag(pdf_path.name, raw)
    text = extract_pdf_text(pdf_path)
    chunks = chunk_vertical_text(text, industry=industry, scene=scene)
    rows = [
        vertical_row(
            industry=industry,
            scene=scene or '通用',
            content=chunk,
            text=chunk,
            source=tag,
            chunk_index=i,
        )
        for i, chunk in enumerate(chunks)
    ]
    written = ingest_rows(collection, rows, store=store, embedder=embedder, config=config)
    return {
        'source': tag,
        'collection': collection,
        'chunks': written,
        'bytes': len(raw),
    }


def ingest_json_documents(
    documents: Iterable[dict[str, Any]],
    *,
    store: VectorStore | None = None,
    embedder: Embedder | None = None,
    config: KnowledgeConfig | None = None,
) -> dict[str, int]:
    """批量导入脚本用：documents 为带 `collection` 的行列表。"""
    grouped: dict[str, list[dict[str, Any]]] = {
        COLLECTION_EQUIPMENT: [],
        COLLECTION_SCHEMES: [],
        COLLECTION_VERTICAL: [],
    }
    for doc in documents:
        col = doc['collection']
        row = {k: v for k, v in doc.items() if k != 'collection'}
        grouped[col].append(row)

    counts: dict[str, int] = {}
    for col, rows in grouped.items():
        if not rows:
            continue
        counts[col] = ingest_rows(col, rows, store=store, embedder=embedder, config=config)
    return counts
