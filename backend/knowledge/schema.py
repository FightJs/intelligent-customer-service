"""Collection 字段定义（纯数据，不依赖 qdrant-client）。

`store.py` 按此映射到 Qdrant 的 named vectors / payload，
CI 单测无需安装 qdrant-client。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from knowledge.models import (
    COLLECTION_EQUIPMENT,
    COLLECTION_SCHEMES,
    COLLECTION_VERTICAL,
)

FieldType = Literal[
    'INT64',
    'VARCHAR',
    'JSON',
    'FLOAT_VECTOR',
    'SPARSE_FLOAT_VECTOR',
]


@dataclass(frozen=True)
class FieldSpec:
    name: str
    dtype: FieldType
    max_length: int | None = None
    dim: int | None = None
    nullable: bool = False
    description: str = ''


@dataclass(frozen=True)
class CollectionSpec:
    name: str
    fields: tuple[FieldSpec, ...]
    description: str = ''

    def field_names(self) -> list[str]:
        return [f.name for f in self.fields]

    def output_fields(self) -> list[str]:
        """检索返回的业务字段（排除向量）。"""
        return [
            f.name
            for f in self.fields
            if f.dtype not in ('FLOAT_VECTOR', 'SPARSE_FLOAT_VECTOR')
        ]

    def dense_dim(self) -> int | None:
        for f in self.fields:
            if f.dtype == 'FLOAT_VECTOR':
                return f.dim
        return None


def _common_audit_fields() -> tuple[FieldSpec, ...]:
    return (
        FieldSpec('source', 'VARCHAR', max_length=128, description='文件名+hash前8'),
        FieldSpec('updated_at', 'INT64', description='unix 秒'),
    )


EQUIPMENT_SPECS = CollectionSpec(
    name=COLLECTION_EQUIPMENT,
    description='设备参数',
    fields=(
        FieldSpec('id', 'INT64'),
        FieldSpec('name', 'VARCHAR', max_length=256),
        FieldSpec('category', 'VARCHAR', max_length=64),
        FieldSpec('brand', 'VARCHAR', max_length=64),
        FieldSpec('price_band', 'VARCHAR', max_length=16),
        FieldSpec('room_size', 'VARCHAR', max_length=16),
        FieldSpec('industry', 'VARCHAR', max_length=32),
        FieldSpec('specs', 'JSON'),
        FieldSpec('text', 'VARCHAR', max_length=4096),
        FieldSpec('dense', 'FLOAT_VECTOR', dim=1024),
        FieldSpec('sparse', 'SPARSE_FLOAT_VECTOR'),
        *_common_audit_fields(),
    ),
)

SETUP_SCHEMES = CollectionSpec(
    name=COLLECTION_SCHEMES,
    description='搭建方案',
    fields=(
        FieldSpec('id', 'INT64'),
        FieldSpec('scheme_name', 'VARCHAR', max_length=256),
        FieldSpec('industry', 'VARCHAR', max_length=32),
        FieldSpec('budget_level', 'VARCHAR', max_length=16),
        FieldSpec('room_size', 'VARCHAR', max_length=16),
        FieldSpec('live_type', 'VARCHAR', max_length=32),
        FieldSpec('equipment_ids', 'JSON'),
        FieldSpec('package_tiers', 'JSON'),
        FieldSpec('layout_notes', 'VARCHAR', max_length=2048),
        FieldSpec('text', 'VARCHAR', max_length=4096),
        FieldSpec('dense', 'FLOAT_VECTOR', dim=1024),
        FieldSpec('sparse', 'SPARSE_FLOAT_VECTOR'),
        *_common_audit_fields(),
    ),
)

VERTICAL_KNOWLEDGE = CollectionSpec(
    name=COLLECTION_VERTICAL,
    description='垂类知识',
    fields=(
        FieldSpec('id', 'INT64'),
        FieldSpec('industry', 'VARCHAR', max_length=32),
        FieldSpec('scene', 'VARCHAR', max_length=64),
        FieldSpec('content', 'VARCHAR', max_length=8192),
        FieldSpec('text', 'VARCHAR', max_length=4096),
        FieldSpec('dense', 'FLOAT_VECTOR', dim=1024),
        FieldSpec('sparse', 'SPARSE_FLOAT_VECTOR'),
        *_common_audit_fields(),
    ),
)

COLLECTION_SPECS: dict[str, CollectionSpec] = {
    EQUIPMENT_SPECS.name: EQUIPMENT_SPECS,
    SETUP_SCHEMES.name: SETUP_SCHEMES,
    VERTICAL_KNOWLEDGE.name: VERTICAL_KNOWLEDGE,
}


def get_collection_spec(name: str) -> CollectionSpec:
    try:
        return COLLECTION_SPECS[name]
    except KeyError:
        raise KeyError(f'unknown collection: {name!r}') from None
