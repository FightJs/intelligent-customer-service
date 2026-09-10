"""方案 Word 降级文档（WeasyPrint 不可用时）。"""
from __future__ import annotations

import io
from datetime import date

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from pipeline.normalize import industry_label


def _set_run_font(run, *, bold: bool = False, size: int = 10, color=None) -> None:
    run.font.name = '微软雅黑'
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    if color is not None:
        run.font.color.rgb = color


def _add_heading(doc: Document, text: str, level: int = 1) -> None:
    heading = doc.add_heading('', level=level)
    run = heading.add_run(text)
    _set_run_font(run, bold=True, size=14 if level <= 1 else 12)


def _add_kv_table(doc: Document, rows: list[tuple[str, str]]) -> None:
    table = doc.add_table(rows=len(rows), cols=2)
    table.style = 'Light Grid Accent 1'
    for index, (key, value) in enumerate(rows):
        table.rows[index].cells[0].text = key
        table.rows[index].cells[1].text = value


def generate_plan_word(
    plan: dict,
    brief: dict,
    *,
    incomplete: bool = False,
    knowledge_degraded: bool = False,
) -> bytes:
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = '微软雅黑'
    style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    title = doc.add_heading('', level=0)
    title_run = title.add_run(f'{brief.get("brand") or "直播间"} 搭建方案')
    _set_run_font(title_run, bold=True, size=18)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta_run = meta.add_run(
        f'{industry_label(brief.get("industry") or "")}'
        f'｜{brief.get("room_size") or ""}'
        f'｜生成日期 {date.today().strftime("%Y-%m-%d")}'
    )
    _set_run_font(meta_run, size=9, color=RGBColor(0x88, 0x88, 0x88))

    if incomplete:
        note = doc.add_paragraph()
        run = note.add_run('信息不完整：部分核心需求未填写，方案细节可能需要复核。')
        _set_run_font(run, size=10, color=RGBColor(0xB8, 0x6A, 0x00))
    if knowledge_degraded:
        note = doc.add_paragraph()
        run = note.add_run('未接入知识库：本方案基于通用模板生成。')
        _set_run_font(run, size=10, color=RGBColor(0xB8, 0x6A, 0x00))

    _add_heading(doc, '一、需求摘要', level=1)
    _add_kv_table(doc, [
        ('品牌', brief.get('brand') or '未填写'),
        ('行业', f'{industry_label(brief.get("industry") or "")} / {brief.get("subcategory") or "—"}'),
        ('面积', f'{brief.get("area_band") or "—"}（{brief.get("room_size") or "—"}）'),
        ('预算', f'总 {brief.get("budget_total") or "—"}｜设备 {brief.get("budget_equip") or "—"}'),
        ('主营商品', brief.get('product_main') or '—'),
        ('风格关键词', '、'.join(brief.get('product_keywords') or []) or '—'),
    ])
    if plan.get('summary'):
        p = doc.add_paragraph()
        run = p.add_run(str(plan['summary']))
        _set_run_font(run, bold=True)

    layout = plan.get('layout') or {}
    _add_heading(doc, '二、空间与布局', level=1)
    for zone in layout.get('zones') or []:
        p = doc.add_paragraph(style='List Bullet')
        run = p.add_run(f'{zone.get("name", "")}：{zone.get("notes", "")}')
        _set_run_font(run)
    _add_kv_table(doc, [
        ('布光', layout.get('lighting_plan') or '—'),
        ('机位', layout.get('camera_plan') or '—'),
        ('背景', layout.get('background_plan') or '—'),
    ])

    _add_heading(doc, '三、设备清单', level=1)
    equipment = plan.get('equipment_list') or []
    eq_table = doc.add_table(rows=1 + len(equipment), cols=5)
    eq_table.style = 'Light Grid Accent 1'
    for col, header in enumerate(['类别', '名称', '型号', '数量', '理由']):
        eq_table.rows[0].cells[col].text = header
    for row_index, item in enumerate(equipment, 1):
        eq_table.rows[row_index].cells[0].text = str(item.get('category') or '')
        eq_table.rows[row_index].cells[1].text = str(item.get('name') or '')
        eq_table.rows[row_index].cells[2].text = str(item.get('model') or '')
        eq_table.rows[row_index].cells[3].text = str(item.get('qty') or '')
        reason = str(item.get('reason') or '')
        if item.get('already_owned'):
            reason = f'（已有）{reason}'
        if item.get('is_custom'):
            reason = f'（定制）{reason}'
        eq_table.rows[row_index].cells[4].text = reason

    _add_heading(doc, '四、三档套餐', level=1)
    tiers = plan.get('package_tiers') or []
    tier_table = doc.add_table(rows=1 + len(tiers), cols=3)
    tier_table.style = 'Light Grid Accent 1'
    for col, header in enumerate(['档位', '金额区间', '包含内容']):
        tier_table.rows[0].cells[col].text = header
    for row_index, tier in enumerate(tiers, 1):
        tier_table.rows[row_index].cells[0].text = str(tier.get('tier') or '')
        tier_table.rows[row_index].cells[1].text = str(tier.get('total_range') or '')
        items = '；'.join(
            f'{item.get("name")}×{item.get("qty", 1)}'
            for item in (tier.get('items') or [])
        )
        tier_table.rows[row_index].cells[2].text = items or '—'

    _add_heading(doc, '五、搭建步骤', level=1)
    for step in plan.get('setup_steps') or []:
        p = doc.add_paragraph(style='List Number')
        run = p.add_run(str(step))
        _set_run_font(run)

    _add_heading(doc, '六、风险与提示', level=1)
    risks = plan.get('risks') or []
    if risks:
        for risk in risks:
            p = doc.add_paragraph(style='List Bullet')
            run = p.add_run(str(risk))
            _set_run_font(run)
    else:
        doc.add_paragraph('暂无额外风险提示。')

    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run('价格为区间参考，非成交报价。')
    _set_run_font(run, size=8, color=RGBColor(0xAA, 0xAA, 0xAA))

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
