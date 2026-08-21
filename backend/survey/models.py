"""调研表 v1 数据模型层（单一数据源 - 数据结构）。

这一层只描述「填好的表单数据长什么样」，不包含 UI 元数据（label/options 等）。
UI 元数据在 schema_def.py，运行时状态在 state.py。

字段值类型对应前端 FieldType：
- text          → TextValue
- choice-single → SingleChoiceValue
- choice-multi  → MultiChoiceValue
- dimension     → DimensionValue
- image         → ImageValue
- table         → TableValue（设备明细表，行数组）
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


# ──────────────────────────────────────────────────────────────
# 单字段值类型
# ──────────────────────────────────────────────────────────────

class TextValue(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['text'] = 'text'
    value: str = ''


class SingleChoiceValue(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['choice-single'] = 'choice-single'
    value: str | None = None


class MultiChoiceValue(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['choice-multi'] = 'choice-multi'
    value: list[str] = Field(default_factory=list)


class DimensionValue(BaseModel):
    """尺寸类字段，如 宽×深×高、女主播身高/男主播身高。"""
    model_config = ConfigDict(extra='forbid')
    type: Literal['dimension'] = 'dimension'
    value: dict[str, str] = Field(default_factory=dict)  # {宽:'4.5', 深:'5', 高:'3'}


class ImageValue(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['image'] = 'image'
    value: list[str] = Field(default_factory=list)  # 文件名/路径列表


class TableValue(BaseModel):
    """设备明细表，每行是 {列id: 值}。"""
    model_config = ConfigDict(extra='forbid')
    type: Literal['table'] = 'table'
    value: list[dict[str, str]] = Field(default_factory=list)


FieldValue = Annotated[
    Union[
        TextValue,
        SingleChoiceValue,
        MultiChoiceValue,
        DimensionValue,
        ImageValue,
        TableValue,
    ],
    Field(discriminator='type'),
]


# ──────────────────────────────────────────────────────────────
# 章节与表单状态
# ──────────────────────────────────────────────────────────────

class SectionState(BaseModel):
    """单个章节的运行时状态。"""
    model_config = ConfigDict(extra='forbid')
    id: str
    status: Literal['pending', 'active', 'complete', 'skipped'] = 'pending'
    fields: dict[str, FieldValue] = Field(default_factory=dict)


class StudioFormState(BaseModel):
    """完整表单状态，跨会话持久化的对象。

    序列化统一用 camelCase（与前端 TS 一致）：
    current_section_id → currentSectionId
    """
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    # 仅用于运行时校验图片归属，不进入 SQLite/前端 formState。
    _session_id: str = PrivateAttr(default='')

    mode: Literal['full', 'quick'] = 'full'

    required_field_ids: list[str] = Field(
        default_factory=list,
        alias='requiredFieldIds',
    )

    sections: dict[str, SectionState] = Field(default_factory=dict)
    current_section_id: str = Field(default='', alias='currentSectionId')
    current_field_id: str = Field(default='', alias='currentFieldId')
    skipped_field_ids: list[str] = Field(
        default_factory=list,
        alias='skippedFieldIds',
    )
    room_image_invited: bool = Field(
        default=False,
        alias='roomImageInvited',
    )
    reference_image_invited: bool = Field(
        default=False,
        alias='referenceImageInvited',
    )
    equipment_image_invited: bool = Field(
        default=False,
        alias='equipmentImageInvited',
    )
    image_invited_field_ids: list[str] = Field(
        default_factory=list,
        alias='imageInvitedFieldIds',
    )
    completed: bool = False


# ──────────────────────────────────────────────────────────────
# 快捷构造函数（schema_def 初始化空值时用）
# ──────────────────────────────────────────────────────────────

def empty_value(field_type: str) -> FieldValue:
    """按字段类型构造空值。"""
    mapping = {
        'text': TextValue,
        'choice-single': SingleChoiceValue,
        'choice-multi': MultiChoiceValue,
        'dimension': DimensionValue,
        'image': ImageValue,
        'table': TableValue,
    }
    cls = mapping.get(field_type)
    if cls is None:
        raise ValueError(f'未知 FieldType: {field_type}')
    return cls()  # type: ignore[return-value]
