"""混合检索：dense + 稀疏融合 + rerank。

CI 与单测不依赖真实 Qdrant：通过注入 store / embedder / reranker 完成。
"""
from __future__ import annotations

import logging
from typing import Any

from knowledge.config import KnowledgeConfig, get_config
from knowledge.embedding import Embedder, EmbeddingError, get_embedder
from knowledge.models import (
    COLLECTIONS,
    CollectionName,
    KnowledgeHit,
    SearchResponse,
)
from knowledge.rerank import Reranker, get_reranker
from knowledge.store import (
    RawHit,
    StoreUnavailable,
    VectorStore,
    build_filter,
    get_store,
)

logger = logging.getLogger(__name__)

__all__ = [
    'fuse_rrf',
    'fuse_weighted',
    'hybrid_search',
]


def _to_hit(collection: CollectionName | str, hit: RawHit) -> KnowledgeHit:
    return KnowledgeHit(
        collection=collection,
        id=hit.id,
        score=float(hit.score),
        payload=dict(hit.payload or {}),
    )


def _normalize_scores(hits: list[RawHit]) -> list[RawHit]:
    if not hits:
        return []
    scores = [max(h.score, 0.0) for h in hits]
    max_score = max(scores) or 1.0
    return [
        RawHit(id=h.id, score=max(h.score, 0.0) / max_score, payload=h.payload)
        for h in hits
    ]


def fuse_weighted(
    dense: list[RawHit],
    sparse: list[RawHit],
    *,
    collection: str,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> list[KnowledgeHit]:
    """加权融合：各通道 min-max 归一后加权求和。"""
    merged: dict[int, float] = {}
    payloads: dict[int, dict[str, Any]] = {}

    for hit in _normalize_scores(dense):
        merged[hit.id] = merged.get(hit.id, 0.0) + dense_weight * hit.score
        payloads[hit.id] = hit.payload
    for hit in _normalize_scores(sparse):
        merged[hit.id] = merged.get(hit.id, 0.0) + sparse_weight * hit.score
        payloads.setdefault(hit.id, hit.payload)

    ordered = sorted(merged.items(), key=lambda item: item[1], reverse=True)
    return [
        KnowledgeHit(collection=collection, id=doc_id, score=score, payload=payloads.get(doc_id, {}))
        for doc_id, score in ordered
    ]


def fuse_rrf(
    dense: list[RawHit],
    sparse: list[RawHit],
    *,
    collection: str,
    k: int = 60,
) -> list[KnowledgeHit]:
    """RRF 融合：score = Σ 1/(k + rank)。"""
    rrf: dict[int, float] = {}
    payloads: dict[int, dict[str, Any]] = {}
    for rank, hit in enumerate(dense, start=1):
        rrf[hit.id] = rrf.get(hit.id, 0.0) + 1.0 / (k + rank)
        payloads[hit.id] = hit.payload
    for rank, hit in enumerate(sparse, start=1):
        rrf[hit.id] = rrf.get(hit.id, 0.0) + 1.0 / (k + rank)
        payloads.setdefault(hit.id, hit.payload)
    ordered = sorted(rrf.items(), key=lambda item: item[1], reverse=True)
    return [
        KnowledgeHit(collection=collection, id=doc_id, score=score, payload=payloads.get(doc_id, {}))
        for doc_id, score in ordered
    ]


def _rerank_hits(
    query: str,
    hits: list[KnowledgeHit],
    reranker: Reranker,
    limit: int,
) -> list[KnowledgeHit]:
    if not hits:
        return []
    texts = [
        str(hit.payload.get('text') or hit.payload.get('content') or hit.payload.get('name') or '')
        for hit in hits
    ]
    try:
        scores = reranker.rerank(query, texts)
    except Exception:
        logger.warning('rerank failed, keep fusion order', exc_info=True)
        return hits[:limit]
    paired = sorted(
        zip(hits, scores),
        key=lambda item: item[1],
        reverse=True,
    )
    return [
        KnowledgeHit(
            collection=hit.collection,
            id=hit.id,
            score=float(score),
            payload=hit.payload,
        )
        for hit, score in paired[:limit]
    ]


def hybrid_search(
    collection: CollectionName,
    query: str,
    *,
    industry: str | None = None,
    room_size: str | None = None,
    budget_level: str | None = None,
    category: str | None = None,
    scene: str | None = None,
    live_type: str | None = None,
    limit: int = 8,
    store: VectorStore | None = None,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
    config: KnowledgeConfig | None = None,
) -> SearchResponse:
    """hybrid top-N → rerank → top-limit。

    Embedding 失败时 BM25-only；store 不可用时 degraded + 空 hits。
    """
    if collection not in COLLECTIONS:
        return SearchResponse(hits=[], degraded=True, reason=f'unknown_collection:{collection}')

    cfg = config or get_config()
    flt = build_filter(
        industry=industry,
        room_size=room_size,
        budget_level=budget_level,
        category=category,
        scene=scene,
        live_type=live_type,
    )
    candidate = max(limit, cfg.candidate_limit)
    active_store = store
    if active_store is None:
        try:
            active_store = get_store(cfg)
        except Exception as exc:
            logger.warning('get_store failed: %s', exc)
            return SearchResponse(hits=[], degraded=True, reason=f'store_unavailable:{exc}')

    degraded = False
    reason: str | None = None

    dense_hits: list[RawHit] = []
    active_embedder = embedder
    if active_embedder is None:
        try:
            active_embedder = get_embedder(cfg)
        except Exception as exc:
            logger.warning('get_embedder failed: %s', exc)
            active_embedder = None

    if active_embedder is not None:
        try:
            vectors = active_embedder.embed([query])
            dense_hits = active_store.search_dense(collection, vectors[0], flt, candidate)
        except EmbeddingError as exc:
            degraded = True
            reason = 'embedding_failed_bm25_only'
            logger.warning('embedding failed, bm25 only: %s', exc)
        except StoreUnavailable as exc:
            return SearchResponse(hits=[], degraded=True, reason=f'store_unavailable:{exc}')
        except Exception as exc:
            degraded = True
            reason = 'embedding_failed_bm25_only'
            logger.warning('dense search failed: %s', exc)

    try:
        sparse_hits = active_store.search_sparse(collection, query, flt, candidate)
    except StoreUnavailable as exc:
        return SearchResponse(hits=[], degraded=True, reason=f'store_unavailable:{exc}')
    except Exception as exc:
        logger.warning('sparse search failed: %s', exc)
        return SearchResponse(hits=[], degraded=True, reason=f'sparse_search_error:{exc}')

    if cfg.fusion == 'rrf':
        fused = fuse_rrf(dense_hits, sparse_hits, collection=collection, k=cfg.embedding_dim and 60 or 60)
    else:
        fused = fuse_weighted(
            dense_hits,
            sparse_hits,
            collection=collection,
            dense_weight=cfg.dense_weight,
            sparse_weight=cfg.sparse_weight,
        )

    active_reranker = reranker
    if active_reranker is None:
        try:
            active_reranker = get_reranker(cfg)
        except Exception as exc:
            logger.warning('get_reranker failed, identity: %s', exc)
            from knowledge.rerank import IdentityReranker

            active_reranker = IdentityReranker()

    ranked = _rerank_hits(query, fused, active_reranker, limit)
    if not ranked and not degraded:
        # 空结果不算 degraded（过滤过严），但 F2 会自行降级
        return SearchResponse(hits=[], degraded=False, reason=None)
    return SearchResponse(hits=ranked, degraded=degraded, reason=reason)
