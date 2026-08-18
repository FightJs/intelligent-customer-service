"""交付物渲染数据准备。

把 StudioFormState 转成文档渲染友好的扁平结构，
三种交付物（markdown/excel/word）共用。
"""
from __future__ import annotations

from agent.flow import value_to_text, value_is_empty, is_field_visible
from store.uploads import resolve_image
from survey.models import FieldValue, StudioFormState
from survey.schema_def import SECTIONS


def _render_value_is_empty(value: FieldValue) -> bool:
    """判断值是否没有可展示的内容。"""
    if value.type == 'text':
        return not value.value.strip()
    if value.type == 'choice-single':
        return not value.value or not value.value.strip()
    if value.type == 'choice-multi':
        return not any(item.strip() for item in value.value)
    if value.type == 'dimension':
        return not any(item.strip() for item in value.value.values())
    if value.type == 'image':
        return not any(item.strip() for item in value.value)
    if value.type == 'table':
        return not any(
            any(cell is not None and str(cell).strip() for cell in row.values())
            for row in value.value
        )
    return value_is_empty(value)


def _filled_table_rows(value) -> list[dict]:
    """移除设备表中完全空白的行，避免预览出现空记录。"""
    return [
        row
        for row in value.value
        if any(cell is not None and str(cell).strip() for cell in row.values())
    ]


def build_render_data(
    state: StudioFormState,
    *,
    filled_only: bool = False,
) -> dict:
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
            if filled_only:
                continue
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
            filled = not _render_value_is_empty(v)
            if filled_only and not filled:
                continue
            images = []
            if f.type == 'image' and filled:
                # 解析图片 id 为磁盘路径，缺失文件静默跳过
                images = [
                    path
                    for image_id in v.value
                    if (path := resolve_image(image_id)) is not None
                ]
            fields_data.append({
                'label': f.label,
                'value': text if filled else '未填写',
                'filled': filled,
                'images': images,
            })

            if f.required:
                sec_total += 1
                if filled:
                    sec_filled += 1

        total_filled += sec_filled
        total_count += sec_total
        if filled_only and not fields_data:
            continue

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
        if inv and inv.type == 'table':
            equipment_table = (
                _filled_table_rows(inv)
                if filled_only
                else inv.value
            )

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
