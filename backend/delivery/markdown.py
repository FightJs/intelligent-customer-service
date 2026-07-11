"""Markdown 交付物生成（场景设计说明 + 需求清单）。"""
from __future__ import annotations

from jinja2 import Template

from delivery.render_data import build_render_data
from survey.models import StudioFormState

_TEMPLATE = Template("""\
# {{ customer_name }} — 直播间搭建需求方案

> 采集进度：{{ progress.filled }}/{{ progress.total }}（{{ progress.pct }}%）

---

{% for sec in sections %}
## {{ sec.title }}

{% if sec.skipped %}
*（本章节已跳过）*

{% elif sec.fields %}
{% for f in sec.fields %}
- **{{ f.label }}**：{{ f.value }}
{% endfor %}

{% else %}
*（暂无信息）*

{% endif %}
{% endfor %}

---

{% if equipment_table %}
## 附：现有设备明细

| 设备类型 | 品牌型号 | 数量 | 备注 |
|---------|---------|------|------|
{% for row in equipment_table %}
| {{ row.get('type', '') }} | {{ row.get('model', '') }} | {{ row.get('qty', '') }} | {{ row.get('note', '') }} |
{% endfor %}
{% else %}
## 附：现有设备明细

*（无现有设备记录）*
{% endif %}

---

*本文档由智能客服系统自动生成*
""")


def generate_markdown(state: StudioFormState) -> str:
    """生成 Markdown 文本。"""
    data = build_render_data(state)
    return _TEMPLATE.render(**data).strip() + '\n'
