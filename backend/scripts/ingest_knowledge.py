"""批量导入 JSON / 知识条目。

JSON 数组，每项形如：
  {"collection": "equipment_specs", "name": "...", "brand": "...", "text": "...", ...}

运行：
  cd backend
  .venv/bin/python scripts/ingest_knowledge.py path/to/docs.json
  .venv/bin/python scripts/ingest_knowledge.py path/to/handbook.pdf --collection vertical_knowledge --industry women
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge.config import get_config
from knowledge.embedding import get_embedder
from knowledge.ingest import (
    equipment_row,
    ingest_json_documents,
    ingest_pdf,
    ingest_rows,
    scheme_row,
    source_tag,
    vertical_row,
)
from knowledge.models import COLLECTION_VERTICAL
from knowledge.store import get_store


def _load_json_docs(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(data, dict):
        data = data.get('documents') or data.get('items') or [data]
    if not isinstance(data, list):
        raise SystemExit('JSON root must be an array or {documents: [...]}')
    return data


def _normalize_doc(doc: dict, source: str) -> dict:
    col = doc.get('collection')
    if col == 'equipment_specs':
        row = equipment_row(
            name=doc['name'],
            category=doc.get('category', '其他'),
            brand=doc.get('brand', ''),
            price_band=doc.get('price_band', 'mid'),
            room_size=doc.get('room_size', 'medium'),
            industry=doc.get('industry', 'all'),
            specs=doc.get('specs') or {},
            text=doc['text'],
            source=doc.get('source', source),
        )
        row['collection'] = col
        return row
    if col == 'setup_schemes':
        row = scheme_row(
            scheme_name=doc['scheme_name'],
            industry=doc.get('industry', 'all'),
            budget_level=doc.get('budget_level', 'mid'),
            room_size=doc.get('room_size', 'medium'),
            live_type=doc.get('live_type', 'brand'),
            equipment_ids=doc.get('equipment_ids') or [],
            package_tiers=doc.get('package_tiers') or [],
            layout_notes=doc.get('layout_notes', ''),
            text=doc['text'],
            source=doc.get('source', source),
        )
        row['collection'] = col
        return row
    if col == 'vertical_knowledge':
        row = vertical_row(
            industry=doc.get('industry', 'all'),
            scene=doc.get('scene', '通用'),
            content=doc.get('content') or doc['text'],
            text=doc['text'],
            source=doc.get('source', source),
            chunk_index=int(doc.get('chunk_index', 0)),
        )
        row['collection'] = col
        return row
    raise SystemExit(f'unknown collection in doc: {col!r}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Ingest knowledge JSON/PDF into Qdrant')
    parser.add_argument('path', type=Path, help='JSON 或 PDF 路径')
    parser.add_argument(
        '--collection',
        default=COLLECTION_VERTICAL,
        help='PDF 目标 collection（默认 vertical_knowledge）',
    )
    parser.add_argument('--industry', default='all')
    parser.add_argument('--scene', default='')
    args = parser.parse_args()

    cfg = get_config()
    store = get_store(cfg)
    embedder = get_embedder(cfg)
    store.ensure_collections()

    path: Path = args.path
    if path.suffix.lower() == '.pdf':
        result = ingest_pdf(
            path,
            collection=args.collection,
            industry=args.industry,
            scene=args.scene,
            store=store,
            embedder=embedder,
            config=cfg,
        )
        print(f"pdf ingested source={result['source']} chunks={result['chunks']}")
        return

    if path.suffix.lower() not in {'.json', '.jsonl'}:
        raise SystemExit('only .json / .jsonl / .pdf supported')

    if path.suffix.lower() == '.jsonl':
        docs = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    else:
        docs = _load_json_docs(path)

    tag = source_tag(path.name, path.read_bytes())
    normalized = [_normalize_doc(d, tag) for d in docs]
    counts = ingest_json_documents(
        normalized, store=store, embedder=embedder, config=cfg
    )
    print(f'json ingested source={tag} counts={counts}')


if __name__ == '__main__':
    main()
