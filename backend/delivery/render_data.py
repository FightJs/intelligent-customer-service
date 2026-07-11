"""交付物渲染数据准备。

把 StudioFormState 转成文档渲染友好的扁平结构，
三种交付物（markdown/excel/word）共用。
"""
from __future__ import annotations

from agent.flow import value_to_text, value_is_empty, is_field_visible
from survey.models import StudioFormState
from survey.schema_def import SECTIONS, SECTION_BY_ID


def build_render_data(state: StudioFormState) -> dict:
    """构造渲染数据。

    返回：
    {
        'customer_name': str,           # 品牌名（文档标题用）
        'sections': [
            {
                'title': str,
                'fields': [{'label': str, 'value': str, 'filled': bool}, ...],
                'filled_count': int,
                'total_count': int,
            }
        ],
        'equipment_table': list[dict],  # 设备明细表行
        'progress': {'filled': int, 'total': int, 'pct': int},
    }
    """
    sections_data = []
    total_filled = 0
    total_count = 0

    for sec_def in SECTIONS:
        sec_state = state.sections[sec_def.id]
        if sec_state.status == 'skipped':
            sections_data.append({
                'title': sec_def.title,
                'fields': [],
                'filled_count': 0,
                'total_count': 0,
                'skipped': True,
            })
            continue

        fields_data = []
        sec_filled = 0
        sec_total = 0

        for f in sec_def.fields:
            if not is_field_visible(f, sec_state):
                continue
            v = sec_state.fields.get(f.id)
            if v is None:
                continue

            text = value_to_text(v, f)
            filled = not value_is_empty(v)
            fields_data.append({
                'label': f.label,
                'value': text if filled else '未填写',
                'filled': filled,
            })

            if f.required:
                sec_total += 1
                if filled:
                    sec_filled += 1

        total_filled += sec_filled
        total_count += sec_total
        sections_data.append({
            'title': sec_def.title,
            'fields': fields_data,
            'filled_count': sec_filled,
            'total_count': sec_total,
            'skipped': False,
        })

    # 设备明细表
    equipment_table = []
    equip_state = state.sections.get('equipment')
    if equip_state:
        inv = equip_state.fields.get('inventory')
        if inv and inv.type == 'table' and inv.value:
            equipment_table = inv.value

    # 品牌名
    customer_name = ''
    customer_sec = state.sections.get('customer')
    if customer_sec:
        brand = customer_sec.fields.get('brand')
        if brand and brand.type == 'text':
            customer_name = brand.value

    pct = round(total_filled / total_count * 100) if total_count > 0 else 0

    return {
        'customer_name': customer_name or '未填写',
        'sections': sections_data,
        'equipment_table': equipment_table,
        'progress': {'filled': total_filled, 'total': total_count, 'pct': pct},
    }
