"""导出 schema.json 供前端 codegen 消费。

用法：
    python -m backend.survey.export

输出：
    frontend/schema.json

内容：
    {
      "sections": [...],          # UI 元数据（含 visibleIf/columns）
      "sectionOrder": [...],      # 章节顺序
      "dataSchema": {...}         # StudioFormState 的 JSON Schema（数据结构）
    }
"""
from __future__ import annotations

import json
from pathlib import Path

from .models import StudioFormState
from .schema_def import SECTIONS, SECTION_ORDER

# 输出路径（frontend/schema.json）
REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / 'frontend' / 'schema.json'


def build_sections_json() -> list[dict]:
    """把 SECTIONS 转成前端可直接消费的 JSON（保留所有 UI 元数据）。"""
    result = []
    for s in SECTIONS:
        fields = []
        for f in s.fields:
            field_dict: dict = {
                'id': f.id,
                'label': f.label,
                'type': f.type,
                'required': f.required,
            }
            if f.options is not None:
                field_dict['options'] = [{'value': o.value, 'label': o.label} for o in f.options]
            if f.dims is not None:
                field_dict['dims'] = f.dims
            if f.unit:
                field_dict['unit'] = f.unit
            if f.placeholder:
                field_dict['placeholder'] = f.placeholder
            if f.columns is not None:
                field_dict['columns'] = [
                    {'id': c.id, 'label': c.label, 'placeholder': c.placeholder} for c in f.columns
                ]
            if f.visible_if is not None:
                field_dict['visibleIf'] = {
                    'fieldId': f.visible_if.field_id,
                    'op': f.visible_if.op,
                    'value': f.visible_if.value,
                }
            fields.append(field_dict)
        result.append({
            'id': s.id,
            'title': s.title,
            'hint': s.hint,
            'order': s.order,
            'fields': fields,
        })
    return result


def export() -> Path:
    payload = {
        'sections': build_sections_json(),
        'sectionOrder': SECTION_ORDER,
        'dataSchema': StudioFormState.model_json_schema(),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return OUTPUT_PATH


def main() -> None:
    path = export()
    sections = len(payload_sections := build_sections_json())
    fields = sum(len(s['fields']) for s in payload_sections)
    print(f'已导出: {path}')
    print(f'  章节: {sections}  字段: {fields}')


if __name__ == '__main__':
    main()
