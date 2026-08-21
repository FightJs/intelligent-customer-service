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
    session_id: str = '',
) -> StudioFormState:
    """从 schema 构造空的 form state（所有字段填默认空值）。"""
    sections: dict[str, SectionState] = {}
    for sec_def in SECTIONS:
        fields = {f.id: empty_value(f.type) for f in sec_def.fields}
        sections[sec_def.id] = SectionState(id=sec_def.id, status='pending', fields=fields)
    state = StudioFormState(
        mode=mode,
        required_field_ids=(
            list(QUICK_REQUIRED_FIELD_IDS)
            if mode == 'quick'
            else []
        ),
        sections=sections,
        current_section_id=SECTION_ORDER[0],
        current_field_id=SECTIONS[0].fields[0].id,
        completed=False,
    )
    state._session_id = session_id
    return state


def to_dict(state: StudioFormState) -> dict:
    """序列化（存 SQLite / 传给前端用，输出 camelCase）。"""
    return state.model_dump(by_alias=True)


def _text_value(section: SectionState | None, field_id: str) -> str:
    if section is None:
        return ''
    value = section.fields.get(field_id)
    if value is None or value.type != 'text':
        return ''
    return value.value.strip()


def _image_values(section: SectionState | None, field_id: str) -> list[str]:
    if section is None:
        return []
    value = section.fields.get(field_id)
    if value is None or value.type != 'image':
        return []
    return list(value.value)


def _append_labeled_text(current: str, items: list[tuple[str, str]]) -> str:
    additions = [f'{label}：{value}' for label, value in items if value]
    return '；'.join([part for part in [current.strip(), *additions] if part])


def _migrate_legacy_values(
    source: StudioFormState,
    target: StudioFormState,
) -> None:
    """把旧模板中有明确新归属的有效信息迁入最终模板。"""
    old_product = source.sections.get('product')
    brand_assets = target.sections['product'].fields['brand_assets']
    if brand_assets.type == 'image':
        brand_assets.value = list(dict.fromkeys([
            *brand_assets.value,
            *_image_values(old_product, 'logo'),
            *_image_values(old_product, 'sample_photo'),
        ]))

    style_ref = target.sections['product'].fields['style_ref']
    if style_ref.type == 'text':
        style_ref.value = _append_labeled_text(style_ref.value, [
            ('旧版商品材质特点', _text_value(old_product, 'material')),
            ('旧版品牌主色调', _text_value(old_product, 'theme_color')),
        ])

    old_host = source.sections.get('host')
    profile = target.sections['host'].fields['profile']
    if profile.type == 'text' and old_host is not None:
        height = old_host.fields.get('height')
        height_text = ''
        if height is not None and height.type == 'dimension':
            height_text = '、'.join(
                f'{name}{value}cm'
                for name, value in height.value.items()
                if value.strip()
            )
        body = old_host.fields.get('body')
        body_text = ''
        if body is not None and body.type == 'choice-single' and body.value:
            body_labels = {
                'thin': '偏瘦', 'standard': '标准',
                'strong': '偏壮', 'plus': '大码',
            }
            body_text = body_labels.get(body.value, body.value)
        profile.value = _append_labeled_text(profile.value, [
            ('旧版主播身高', height_text),
            ('旧版主播体型', body_text),
        ])

    old_goal = source.sections.get('goal')
    other = target.sections['goal'].fields['other']
    if other.type == 'text':
        other.value = _append_labeled_text(other.value, [
            ('旧版预期效果', _text_value(old_goal, 'expectation')),
        ])


def from_dict(data: dict, session_id: str = '') -> StudioFormState:
    """反序列化并把旧会话精确迁移到当前问卷结构。"""
    state = StudioFormState.model_validate(data)
    legacy_state = state.model_copy(deep=True)
    empty = create_initial_state(state.mode, session_id=session_id)
    normalized: dict[str, SectionState] = {}

    for section_def in SECTIONS:
        existing = state.sections.get(section_def.id)
        if existing is None:
            normalized[section_def.id] = empty.sections[section_def.id]
            continue

        fields = {}
        for field_def in section_def.fields:
            value = existing.fields.get(field_def.id)
            if value is None or value.type != field_def.type:
                value = empty.sections[section_def.id].fields[field_def.id]
            fields[field_def.id] = value

        existing.fields = fields
        if existing.status == 'skipped' and not section_def.skippable:
            existing.status = 'pending'
        normalized[section_def.id] = existing

    state.sections = normalized
    _migrate_legacy_values(legacy_state, state)
    if state.current_section_id not in normalized:
        state.current_section_id = SECTION_ORDER[0]
        state.current_field_id = SECTIONS[0].fields[0].id

    valid_skippable_keys = {
        f'{section.id}.{field.id}'
        for section in SECTIONS
        for field in section.fields
        if field.skippable or section.skippable
    }
    state.skipped_field_ids = [
        key for key in state.skipped_field_ids
        if key in valid_skippable_keys
    ]
    valid_image_keys = {
        f'{section.id}.{field.id}'
        for section in SECTIONS
        for field in section.fields
        if field.type == 'image'
    }
    state.image_invited_field_ids = [
        key for key in state.image_invited_field_ids
        if key in valid_image_keys
    ]
    state._session_id = session_id
    return state


__all__ = [
    'SECTIONS', 'SECTION_ORDER', 'SECTION_BY_ID', 'FIELD_BY_ID',
    'create_initial_state', 'to_dict', 'from_dict',
    'deepcopy',
]
