"""Embedding 提供方。

- dashscope：生产 text-embedding-v3（httpx，1024 维）
- local_bge：本地 BGE-M3（可选依赖）
- mock：测试/契约联调，确定性向量，不访问网络
"""
from __future__ import annotations

import hashlib
import logging
import math
import struct
from typing import Protocol, Sequence

import httpx

from knowledge.config import KnowledgeConfig, get_config

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    pass


class Embedder(Protocol):
    dim: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """批量向量化；失败必须抛 EmbeddingError，由调用方整批回滚。"""
        ...


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


class MockEmbedder:
    """测试用确定性 embedding：SHA256 → 伪随机浮点，再 L2 归一化。"""

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode('utf-8')).digest()
            seed = digest
            vec: list[float] = []
            counter = 0
            while len(vec) < self.dim:
                block = hashlib.sha256(seed + struct.pack('>I', counter)).digest()
                for i in range(0, len(block), 4):
                    if len(vec) >= self.dim:
                        break
                    raw = int.from_bytes(block[i : i + 4], 'big') / 0xFFFFFFFF
                    vec.append(raw * 2.0 - 1.0)
                counter += 1
            out.append(_l2_normalize(vec))
        return out


class DashScopeEmbedder:
    """阿里 text-embedding-v3。"""

    def __init__(
        self,
        api_key: str,
        model: str = 'text-embedding-v3',
        dim: int = 1024,
        base_url: str = 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise EmbeddingError('DASHSCOPE_API_KEY is empty')
        self.api_key = api_key
        self.model = model
        self.dim = dim
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {
            'model': self.model,
            'input': {'texts': list(texts)},
            'parameters': {'dimension': self.dim, 'text_type': 'query'},
        }
        try:
            resp = httpx.post(
                f'{self.base_url}/embeddings',
                json=payload,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get('output', {}).get('embeddings') or data.get('data')
            if not items:
                raise EmbeddingError(f'empty embeddings in response: {data!r:.200}')
            vectors = [item['embedding'] for item in items]
            if len(vectors) != len(texts):
                raise EmbeddingError(
                    f'embedding count mismatch: got {len(vectors)}, want {len(texts)}'
                )
            return vectors
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(f'dashscope embedding failed: {exc}') from exc


class LocalBgeEmbedder:
    """本地 BGE-M3（sentence-transformers / FlagEmbedding 均可）。"""

    def __init__(self, model_name: str = 'BAAI/bge-m3', dim: int = 1024) -> None:
        self.dim = dim
        self._model = None
        self.model_name = model_name

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:
            raise EmbeddingError(
                'local_bge requires sentence-transformers: pip install sentence-transformers'
            ) from exc
        self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            model = self._load()
            vectors = model.encode(list(texts), normalize_embeddings=True)
            return [list(map(float, v)) for v in vectors]
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(f'local bge embedding failed: {exc}') from exc


def get_embedder(config: KnowledgeConfig | None = None) -> Embedder:
    cfg = config or get_config()
    provider = cfg.embedding_provider
    if provider == 'mock':
        return MockEmbedder(dim=cfg.embedding_dim)
    if provider == 'local_bge':
        return LocalBgeEmbedder(dim=cfg.embedding_dim)
    if provider == 'dashscope':
        return DashScopeEmbedder(
            api_key=cfg.dashscope_api_key,
            model=cfg.embedding_model,
            dim=cfg.embedding_dim,
        )
    raise EmbeddingError(f'unknown EMBEDDING_PROVIDER: {provider!r}')
