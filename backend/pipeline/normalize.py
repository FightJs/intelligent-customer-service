"""form_state → RequirementBrief 规范化。"""
from __future__ import annotations

import re

from agent.flow import value_is_empty
from knowledge.mapping import map_room_size
from pipeline.models import ExistingEquipment, RequirementBrief
from survey.models import StudioFormState
from survey.state import from_dict

# F2 核心检索键：缺失且 allow_incomplete=False 时直接 failed
CORE_FIELD_KEYS = [
    'customer.brand',
    'industry.category',
    'venue.area',
    'budget.total',
    'budget.equipment',
    'product.main',
    'product.keywords',
    'goal.core',
]

_KEYWORD_SPLIT = re.compile(r'[,，、/;；\s]+')


def _text(state: StudioFormState, section_id: str, field_id: str) -> str:
    section = state.sections.get(section_id)
    if section is None:
        return ''
    value = section.fields.get(field_id)
    if value is None or value.type != 'text':
        return ''
    return value.value.strip()


def _single(state: StudioFormState, section_id: str, field_id: str) -> str:
    section = state.sections.get(section_id)
    if section is None:
        return ''
    value = section.fields.get(field_id)
    if value is None or value.type != 'choice-single':
        return ''
    return (value.value or '').strip()


def _multi(state: StudioFormState, section_id: str, field_id: str) -> list[str]:
    section = state.sections.get(section_id)
    if section is None:
        return []
    value = section.fields.get(field_id)
    if value is None or value.type != 'choice-multi':
        return []
    return [item.strip() for item in value.value if item.strip()]


def _table_rows(state: StudioFormState, section_id: str, field_id: str) -> list[dict]:
    section = state.sections.get(section_id)
    if section is None:
        return []
    value = section.fields.get(field_id)
    if value is None or value.type != 'table':
        return []
    rows = []
    for row in value.value:
        if any(str(cell or '').strip() for cell in row.values()):
            rows.append(row)
    return rows


def _split_keywords(raw: str) -> list[str]:
    if not raw:
        return []
    parts = [part.strip() for part in _KEYWORD_SPLIT.split(raw) if part.strip()]
    # 去重保序
    return list(dict.fromkeys(parts))


def _safe_room_size(area: str) -> str:
    if not area:
        return 'medium'
    try:
        return map_room_size(area)
    except ValueError:
        return 'medium'


def _existing_equipment(state: StudioFormState) -> list[ExistingEquipment]:
    if _single(state, 'budget', 'has_existing') != 'yes':
        return []
    items: list[ExistingEquipment] = []
    for row in _table_rows(state, 'equipment', 'inventory'):
        items.append(ExistingEquipment(
            type=str(row.get('type') or '').strip(),
            model=str(row.get('model') or '').strip(),
            qty=str(row.get('qty') or '').strip(),
        ))
    return [item for item in items if item.type or item.model]


def _field_filled(state: StudioFormState, key: str) -> bool:
    section_id, field_id = key.split('.', 1)
    section = state.sections.get(section_id)
    if section is None:
        return False
    field_value = section.fields.get(field_id)
    if field_value is None:
        return False
    return not value_is_empty(field_value)


def normalize_form_state(form_state: dict) -> RequirementBrief:
    """把序列化 form_state 规范为 RequirementBrief。原始区间原样保留。"""
    state = from_dict(form_state)

    missing = [key for key in CORE_FIELD_KEYS if not _field_filled(state, key)]
    filled = sum(1 for key in CORE_FIELD_KEYS if key not in missing)
    completeness = round(filled / len(CORE_FIELD_KEYS), 2) if CORE_FIELD_KEYS else 0.0

    return RequirementBrief(
        brand=_text(state, 'customer', 'brand'),
        industry=_single(state, 'industry', 'category') or 'other',
        subcategory=_text(state, 'industry', 'subcategory'),
        price_band=_single(state, 'industry', 'price_band'),
        positioning=_single(state, 'industry', 'positioning'),
        live_type=_single(state, 'industry', 'live_type'),
        room_size=_safe_room_size(_single(state, 'venue', 'area')),
        area_band=_single(state, 'venue', 'area'),
        budget_total=_single(state, 'budget', 'total'),
        budget_equip=_single(state, 'budget', 'equipment'),
        budget_decor=_single(state, 'budget', 'decor'),
        budget_flex=_single(state, 'budget', 'flex'),
        goal_core=_single(state, 'goal', 'core'),
        goal_focus=_multi(state, 'goal', 'focus'),
        product_main=_text(state, 'product', 'main'),
        product_keywords=_split_keywords(_text(state, 'product', 'keywords')),
        host_count=_single(state, 'host', 'count'),
        host_movement=_single(state, 'host', 'movement'),
        existing_equipment=_existing_equipment(state),
        window=_single(state, 'venue', 'window'),
        window_pos=_single(state, 'venue', 'window_pos'),
        renovation=_single(state, 'venue', 'renovation'),
        deadline=_single(state, 'goal', 'deadline'),
        need_3d=_single(state, 'goal', 'need_3d'),
        other_notes=_text(state, 'goal', 'other'),
        completeness=completeness,
        missing_core_fields=missing,
    )


def industry_label(industry: str) -> str:
    labels = {
        'women': '女装',
        'men': '男装',
        'beauty': '美妆',
        'food': '食品',
        'jewelry': '珠宝',
        'home': '家居',
        'digital': '数码',
        'baby': '母婴',
        'other': '其他',
    }
    return labels.get(industry, industry or '其他')
