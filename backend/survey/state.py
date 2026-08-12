"""Form state 工厂与操作（后端运行时用）。

从 schema_def 构造空的 StudioFormState，供 API 创建会话时初始化。
"""
from __future__ import annotations

from copy import deepcopy
from typing import Literal

from .models import StudioFormState, SectionState, empty_value
from .schema_def import (
    SECTIONS,
    SECTION_ORDER,
    SECTION_BY_ID,
    FIELD_BY_ID,
    QUICK_REQUIRED_FIELD_IDS,
)


def create_initial_state(
    mode: Literal['full', 'quick'] = 'full',
) -> StudioFormState:
    """从 schema 构造空的 form state（所有字段填默认空值）。"""
    sections: dict[str, SectionState] = {}
    for sec_def in SECTIONS:
        fields = {f.id: empty_value(f.type) for f in sec_def.fields}
        sections[sec_def.id] = SectionState(id=sec_def.id, status='pending', fields=fields)
    return StudioFormState(
        mode=mode,
        required_field_ids=(
            list(QUICK_REQUIRED_FIELD_IDS)
            if mode == 'quick'
            else []
        ),
        sections=sections,
        current_section_id=SECTION_ORDER[0],
        completed=False,
    )


def to_dict(state: StudioFormState) -> dict:
    """序列化（存 SQLite / 传给前端用，输出 camelCase）。"""
    return state.model_dump(by_alias=True)


def from_dict(data: dict) -> StudioFormState:
    """反序列化（兼容 camelCase 和 snake_case）。"""
    return StudioFormState.model_validate(data)


__all__ = [
    'SECTIONS', 'SECTION_ORDER', 'SECTION_BY_ID', 'FIELD_BY_ID',
    'create_initial_state', 'to_dict', 'from_dict',
    'deepcopy',
]
