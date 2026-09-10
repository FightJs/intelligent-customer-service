"""Rerank 提供方。

- identity：保持融合序（本地/降级）
- dashscope：gte-rerank
- local：BGE reranker（可选依赖）
"""
from __future__ import annotations

import logging
from typing import Protocol, Sequence

import httpx

from knowledge.config import KnowledgeConfig, get_config

logger = logging.getLogger(__name__)


class RerankError(RuntimeError):
    pass


class Reranker(Protocol):
    def rerank(self, query: str, texts: Sequence[str]) -> list[float]:
        """返回与 texts 等长的相关性分数（越大越相关）。"""
        ...


class IdentityReranker:
    """不改序：按原位置递减打分。"""

    def rerank(self, query: str, texts: Sequence[str]) -> list[float]:
        n = len(texts)
        return [float(n - i) for i in range(n)]


class DashScopeReranker:
    def __init__(
        self,
        api_key: str,
        model: str = 'gte-rerank',
        base_url: str = 'https://dashscope.aliyuncs.com/api/v1',
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise RerankError('DASHSCOPE_API_KEY is empty')
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def rerank(self, query: str, texts: Sequence[str]) -> list[float]:
        if not texts:
            return []
        payload = {
            'model': self.model,
            'input': {'query': query, 'documents': list(texts)},
            'parameters': {'return_documents': False, 'top_n': len(texts)},
        }
        try:
            resp = httpx.post(
                f'{self.base_url}/services/aigc/text-rerank/text-rerank',
                json=payload,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'X-DashScope-DataInspection': 'enable',
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get('output', {}).get('results') or []
            # API 按 score 降序返回，带 index
            scores = [0.0] * len(texts)
            for item in results:
                idx = int(item['index'])
                scores[idx] = float(item.get('relevance_score', 0.0))
            return scores
        except Exception as exc:
            raise RerankError(f'dashscope rerank failed: {exc}') from exc


class LocalBgeReranker:
    def __init__(self, model_name: str = 'BAAI/bge-reranker-v2-m3') -> None:
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import CrossEncoder  # type: ignore
        except ImportError as exc:
            raise RerankError(
                'local rerank requires sentence-transformers: pip install sentence-transformers'
            ) from exc
        self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(self, query: str, texts: Sequence[str]) -> list[float]:
        if not texts:
            return []
        try:
            model = self._load()
            pairs = [(query, t) for t in texts]
            scores = model.predict(pairs)
            return [float(s) for s in scores]
        except RerankError:
            raise
        except Exception as exc:
            raise RerankError(f'local rerank failed: {exc}') from exc


def get_reranker(config: KnowledgeConfig | None = None) -> Reranker:
    cfg = config or get_config()
    provider = cfg.rerank_provider
    if provider == 'identity':
        return IdentityReranker()
    if provider == 'local':
        try:
            return LocalBgeReranker(model_name=cfg.rerank_model)
        except Exception:
            logger.warning('local reranker unavailable, falling back to identity')
            return IdentityReranker()
    if provider == 'dashscope':
        return DashScopeReranker(api_key=cfg.dashscope_api_key, model=cfg.rerank_model)
    raise RerankError(f'unknown RERANK_PROVIDER: {provider!r}')


__all__ = [
    'DashScopeReranker',
    'IdentityReranker',
    'LocalBgeReranker',
    'RerankError',
    'Reranker',
    'get_reranker',
]
