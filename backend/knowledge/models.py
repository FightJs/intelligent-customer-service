"""知识库公共模型与枚举。"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CollectionName = Literal['equipment_specs', 'setup_schemes', 'vertical_knowledge']

COLLECTION_EQUIPMENT: CollectionName = 'equipment_specs'
COLLECTION_SCHEMES: CollectionName = 'setup_schemes'
COLLECTION_VERTICAL: CollectionName = 'vertical_knowledge'
COLLECTIONS: tuple[CollectionName, ...] = (
    COLLECTION_EQUIPMENT,
    COLLECTION_SCHEMES,
    COLLECTION_VERTICAL,
)

INDUSTRIES = frozenset(
    {'women', 'men', 'shoes', 'beauty', 'food', 'jewelry', 'home', 'digital', 'baby', 'all', 'other'}
)
ROOM_SIZES = frozenset({'small', 'medium', 'large', 'xlarge'})
BUDGET_LEVELS = frozenset({'low', 'mid', 'high', 'ultra'})
PRICE_BANDS = BUDGET_LEVELS
LIVE_TYPES = frozenset({'influencer', 'brand', 'factory', 'ip', 'other'})
EQUIPMENT_CATEGORIES = frozenset(
    {'灯光', '相机', '镜头', '声卡', '支架', '背景', '采集卡', '其他'}
)


class KnowledgeHit(BaseModel):
    model_config = ConfigDict(extra='forbid')

    collection: str
    id: int
    score: float
    payload: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    hits: list[KnowledgeHit] = Field(default_factory=list)
    degraded: bool = False
    reason: str | None = None
