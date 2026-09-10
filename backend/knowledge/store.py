"""向量存储抽象：生产 Qdrant + 测试/开发内存实现。"""
from __future__ import annotations

import hashlib
import logging
import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from knowledge.config import KnowledgeConfig, get_config
from knowledge.embedding import Embedder
from knowledge.schema import COLLECTION_SPECS, CollectionSpec, get_collection_spec

logger = logging.getLogger(__name__)

_CJK_RE = re.compile(r'[一-鿿]')

# field -> 允许值列表（字段间 AND，值之间 OR）
StoreFilter = dict[str, list[str]]


class StoreUnavailable(RuntimeError):
    """向量库不可达 / 连接失败。"""


@dataclass
class RawHit:
    id: int
    score: float
    payload: dict[str, Any] = field(default_factory=dict)


class VectorStore(Protocol):
    def ensure_collections(self) -> None: ...

    def upsert(self, collection: str, rows: Sequence[dict[str, Any]]) -> None: ...

    def search_dense(
        self,
        collection: str,
        vector: Sequence[float],
        flt: StoreFilter | None,
        limit: int,
    ) -> list[RawHit]: ...

    def search_sparse(
        self,
        collection: str,
        query: str,
        flt: StoreFilter | None,
        limit: int,
    ) -> list[RawHit]: ...

    def close(self) -> None: ...


# ──────────────────────────────────────────────────────────────
# 过滤条件（结构化，双方言共用）
# ──────────────────────────────────────────────────────────────


def build_filter(
    *,
    industry: str | None = None,
    room_size: str | Sequence[str] | None = None,
    budget_level: str | Sequence[str] | None = None,
    category: str | None = None,
    scene: str | None = None,
    live_type: str | None = None,
) -> StoreFilter | None:
    """构建结构化过滤条件。

    industry 自动扩展为 `['<value>', 'all']`，对齐通用条目。
    """
    flt: StoreFilter = {}

    def _put(name: str, values: Sequence[str]) -> None:
        if values:
            flt[name] = list(values)

    if industry:
        _put('industry', sorted({industry, 'all'}))
    if room_size:
        vals = room_size if isinstance(room_size, (list, tuple, set)) else [room_size]
        _put('room_size', list(vals))
    if budget_level:
        vals = (
            budget_level
            if isinstance(budget_level, (list, tuple, set))
            else [budget_level]
        )
        _put('budget_level', list(vals))
    if category:
        _put('category', [category])
    if scene:
        _put('scene', [scene])
    if live_type:
        _put('live_type', [live_type])

    return flt or None


def _tokenize(text: str) -> list[str]:
    """中英混合粗切分：CJK 单字 + 英文单词。足够稀疏检索近似。"""
    tokens: list[str] = []
    for match in re.finditer(r'[一-鿿]+|[A-Za-z0-9]+', text.lower()):
        token = match.group()
        if _CJK_RE.search(token):
            tokens.extend(list(token))
        else:
            tokens.append(token)
    return tokens


def _stable_token_id(token: str) -> int:
    """跨进程稳定的正 int31，作为稀疏向量索引。"""
    digest = hashlib.md5(token.encode('utf-8')).digest()
    return int.from_bytes(digest[:4], 'big') & 0x7FFFFFFF


def _sparse_from_text(text: str) -> tuple[list[int], list[float]]:
    """文本 → 稀疏向量（TF）。空文本返回占位，避免 Qdrant 拒绝空向量。"""
    token_counts: dict[int, float] = {}
    for token in _tokenize(text):
        idx = _stable_token_id(token)
        token_counts[idx] = token_counts.get(idx, 0.0) + 1.0
    if not token_counts:
        return [0], [0.0]
    return list(token_counts.keys()), list(token_counts.values())


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(a[i] * a[i] for i in range(n))) or 1.0
    nb = math.sqrt(sum(b[i] * b[i] for i in range(n))) or 1.0
    return dot / (na * nb)


def _match_filter(payload: dict[str, Any], flt: StoreFilter | None) -> bool:
    if not flt:
        return True
    for name, values in flt.items():
        if payload.get(name) not in values:
            return False
    return True


def _row_text(row: dict[str, Any]) -> str:
    return str(row.get('text') or row.get('content') or '')


class InMemoryVectorStore:
    """开发/测试用存储：支持同样过滤条件，稀疏检索用 token 重合度近似。"""

    def __init__(self, embedder: Embedder | None = None) -> None:
        self._data: dict[str, dict[int, dict[str, Any]]] = {name: {} for name in COLLECTION_SPECS}
        self._embedder = embedder

    def ensure_collections(self) -> None:
        for name in COLLECTION_SPECS:
            self._data.setdefault(name, {})

    def upsert(self, collection: str, rows: Sequence[dict[str, Any]]) -> None:
        spec = get_collection_spec(collection)
        bucket = self._data.setdefault(collection, {})
        for row in rows:
            self._validate_row(spec, row)
            bucket[int(row['id'])] = dict(row)

    def _validate_row(self, spec: CollectionSpec, row: dict[str, Any]) -> None:
        allowed = set(spec.field_names())
        missing = [f.name for f in spec.fields if f.name not in row and f.name != 'sparse']
        if missing:
            raise ValueError(f'{spec.name} row missing fields: {missing}')
        extra = set(row) - allowed - {'sparse'}
        if extra:
            raise ValueError(f'{spec.name} row has unknown fields: {sorted(extra)}')

    def search_dense(
        self,
        collection: str,
        vector: Sequence[float],
        flt: StoreFilter | None,
        limit: int,
    ) -> list[RawHit]:
        scored: list[RawHit] = []
        for row in self._data.get(collection, {}).values():
            if not _match_filter(row, flt):
                continue
            dense = row.get('dense')
            if not dense:
                continue
            scored.append(
                RawHit(id=int(row['id']), score=_cosine(vector, dense), payload=dict(row))
            )
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:limit]

    def search_sparse(
        self,
        collection: str,
        query: str,
        flt: StoreFilter | None,
        limit: int,
    ) -> list[RawHit]:
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        q_set = set(q_tokens)
        scored: list[RawHit] = []
        for row in self._data.get(collection, {}).values():
            if not _match_filter(row, flt):
                continue
            text = _row_text(row)
            t_tokens = _tokenize(text)
            if not t_tokens:
                continue
            overlap = len(q_set & set(t_tokens))
            if overlap <= 0:
                continue
            score = overlap / math.sqrt(len(t_tokens) + 1.0)
            scored.append(RawHit(id=int(row['id']), score=score, payload=dict(row)))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:limit]

    def close(self) -> None:
        return None

    def dump(self, collection: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self._data.get(collection, {}).values()]


class QdrantVectorStore:
    """qdrant-client 实现：支持 http(s) 服务端与本地嵌入路径。懒加载。"""

    def __init__(
        self,
        uri: str,
        api_key: str = '',
        dense_name: str = 'dense',
        sparse_name: str = 'sparse',
    ) -> None:
        self.uri = uri
        self.api_key = api_key
        self.dense_name = dense_name
        self.sparse_name = sparse_name
        self._client: Any = None

    def _connect(self):
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:
            raise StoreUnavailable(
                'qdrant-client is not installed; pip install ics-backend[qdrant]'
            ) from exc
        try:
            if self.uri.startswith('http://') or self.uri.startswith('https://'):
                self._client = QdrantClient(
                    url=self.uri,
                    api_key=self.api_key or None,
                    timeout=10.0,
                )
            else:
                self._client = QdrantClient(path=self.uri, timeout=10.0)
        except Exception as exc:
            raise StoreUnavailable(f'qdrant connect failed: {exc}') from exc
        return self._client

    def ensure_collections(self) -> None:
        from qdrant_client import models

        client = self._connect()
        for spec in COLLECTION_SPECS.values():
            try:
                exists = client.collection_exists(spec.name)
            except Exception as exc:
                raise StoreUnavailable(f'qdrant collection_exists failed: {exc}') from exc
            if exists:
                continue

            dim = next((f.dim for f in spec.fields if f.dtype == 'FLOAT_VECTOR'), None)
            if not dim:
                raise StoreUnavailable(f'{spec.name} has no dense vector field')
            try:
                client.create_collection(
                    collection_name=spec.name,
                    vectors_config={
                        self.dense_name: models.VectorParams(
                            size=dim,
                            distance=models.Distance.COSINE,
                        ),
                    },
                    sparse_vectors_config={
                        self.sparse_name: models.SparseVectorParams(),
                    },
                )
            except Exception as exc:
                raise StoreUnavailable(f'qdrant create_collection failed: {exc}') from exc

    def upsert(self, collection: str, rows: Sequence[dict[str, Any]]) -> None:
        if not rows:
            return
        from qdrant_client import models

        client = self._connect()
        points: list[models.PointStruct] = []
        for row in rows:
            dense = list(row.get('dense') or [])
            if not dense:
                raise StoreUnavailable(f'row {row.get("id")} missing dense vector')
            indices, values = _sparse_from_text(_row_text(row))
            payload = {
                k: v for k, v in row.items() if k not in ('id', 'dense', 'sparse')
            }
            points.append(
                models.PointStruct(
                    id=int(row['id']),
                    vector={
                        self.dense_name: dense,
                        self.sparse_name: models.SparseVector(indices=indices, values=values),
                    },
                    payload=payload,
                )
            )
        try:
            client.upsert(collection_name=collection, points=points, wait=True)
        except Exception as exc:
            raise StoreUnavailable(f'qdrant upsert failed: {exc}') from exc

    def search_dense(
        self,
        collection: str,
        vector: Sequence[float],
        flt: StoreFilter | None,
        limit: int,
    ) -> list[RawHit]:
        client = self._connect()
        try:
            result = client.query_points(
                collection_name=collection,
                query=list(vector),
                using=self.dense_name,
                query_filter=self._to_filter(flt),
                limit=limit,
                with_payload=True,
            )
        except Exception as exc:
            raise StoreUnavailable(f'qdrant dense search failed: {exc}') from exc
        return self._to_hits(result.points)

    def search_sparse(
        self,
        collection: str,
        query: str,
        flt: StoreFilter | None,
        limit: int,
    ) -> list[RawHit]:
        from qdrant_client import models

        client = self._connect()
        indices, values = _sparse_from_text(query)
        if values == [0.0]:
            return []
        try:
            result = client.query_points(
                collection_name=collection,
                query=models.SparseVector(indices=indices, values=values),
                using=self.sparse_name,
                query_filter=self._to_filter(flt),
                limit=limit,
                with_payload=True,
            )
        except Exception as exc:
            raise StoreUnavailable(f'qdrant sparse search failed: {exc}') from exc
        return self._to_hits(result.points)

    @staticmethod
    def _to_filter(flt: StoreFilter | None):
        if not flt:
            return None
        from qdrant_client import models

        must: list[Any] = []
        for key, values in flt.items():
            if len(values) == 1:
                must.append(
                    models.FieldCondition(key=key, match=models.MatchValue(value=values[0]))
                )
            else:
                must.append(
                    models.FieldCondition(key=key, match=models.MatchAny(any=list(values)))
                )
        return models.Filter(must=must)

    @staticmethod
    def _to_hits(points: Sequence[Any]) -> list[RawHit]:
        hits: list[RawHit] = []
        for point in points:
            payload = dict(point.payload or {})
            hits.append(RawHit(id=int(point.id), score=float(point.score), payload=payload))
        return hits

    def close(self) -> None:
        if self._client is None:
            return
        try:
            self._client.close()
        except Exception:
            logger.warning('qdrant close failed', exc_info=True)
        self._client = None


_store_singleton: VectorStore | None = None


def get_store(config: KnowledgeConfig | None = None) -> VectorStore:
    """按 QDRANT_URI 返回存储实现。

    - `memory://` → InMemory（本地无服务 / 契约测试）
    - `./path` / 绝对路径 → Qdrant 本地嵌入文件库
    - `http(s)://...` → Qdrant 服务端
    """
    global _store_singleton
    if _store_singleton is not None:
        return _store_singleton
    cfg = config or get_config()
    uri = cfg.qdrant_uri
    if uri.startswith('memory://') or uri == ':memory:':
        _store_singleton = InMemoryVectorStore()
    else:
        _store_singleton = QdrantVectorStore(uri=uri, api_key=cfg.qdrant_api_key)
    return _store_singleton


def set_store(store: VectorStore | None) -> None:
    """测试注入。"""
    global _store_singleton
    _store_singleton = store


def now_ts() -> int:
    return int(time.time())
