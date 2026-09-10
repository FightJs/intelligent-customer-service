"""知识库运行配置（环境变量）。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

EMBEDDING_DIM = 1024
HYBRID_CANDIDATES = 30
DENSE_WEIGHT_DEFAULT = 0.6
SPARSE_WEIGHT_DEFAULT = 0.4
RRF_K = 60


@dataclass(frozen=True)
class KnowledgeConfig:
    # memory:// | 本地路径（嵌入式）| http(s)://host:6333
    qdrant_uri: str = 'http://localhost:6333'
    qdrant_api_key: str = ''
    # dashscope | openrouter | local_bge | mock
    embedding_provider: str = 'dashscope'
    dashscope_api_key: str = ''
    openrouter_api_key: str = ''
    openrouter_base_url: str = 'https://openrouter.ai/api/v1'
    embedding_model: str = 'text-embedding-v3'
    rerank_provider: str = 'local'  # local | dashscope | identity
    rerank_model: str = 'bge-reranker-v2-m3'
    fusion: str = 'weighted'  # weighted | rrf
    dense_weight: float = DENSE_WEIGHT_DEFAULT
    sparse_weight: float = SPARSE_WEIGHT_DEFAULT
    candidate_limit: int = HYBRID_CANDIDATES
    embedding_dim: int = EMBEDDING_DIM


@lru_cache(maxsize=1)
def get_config() -> KnowledgeConfig:
    return KnowledgeConfig(
        qdrant_uri=os.getenv('QDRANT_URI', 'http://localhost:6333'),
        qdrant_api_key=os.getenv('QDRANT_API_KEY', ''),
        embedding_provider=os.getenv('EMBEDDING_PROVIDER', 'dashscope'),
        dashscope_api_key=os.getenv('DASHSCOPE_API_KEY', ''),
        openrouter_api_key=os.getenv('OPENROUTER_API_KEY', ''),
        openrouter_base_url=os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
        embedding_model=os.getenv('EMBEDDING_MODEL', 'text-embedding-v3'),
        rerank_provider=os.getenv('RERANK_PROVIDER', 'local'),
        rerank_model=os.getenv('RERANK_MODEL', 'bge-reranker-v2-m3'),
        fusion=os.getenv('KNOWLEDGE_FUSION', 'weighted'),
        dense_weight=float(os.getenv('KNOWLEDGE_DENSE_WEIGHT', str(DENSE_WEIGHT_DEFAULT))),
        sparse_weight=float(os.getenv('KNOWLEDGE_SPARSE_WEIGHT', str(SPARSE_WEIGHT_DEFAULT))),
        candidate_limit=int(os.getenv('KNOWLEDGE_CANDIDATE_LIMIT', str(HYBRID_CANDIDATES))),
        embedding_dim=EMBEDDING_DIM,
    )


def reset_config_cache() -> None:
    get_config.cache_clear()
