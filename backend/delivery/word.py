"""Word 交付物生成（需求确认书）。

调研表格式，含客户签字栏。图片字段在章节表格下方内嵌原图 + 图注。
"""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from PIL import Image

from delivery.render_data import build_render_data
from survey.models import StudioFormState


def _set_cell_font(cell, text: str, bold: bool = False, size: int = 10) -> None:
    """设置单元格文本和字体。"""
    cell.text = text
    for para in cell.paragraphs:
        for run in para.runs:
            run.font.name = '微软雅黑'
            run.font.size = Pt(size)
            run.font.bold = bold
            run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')


def _image_source(path: Path):
    """python-docx 不支持 webp，转成 png 字节流；其余格式直接给路径。"""
    if path.suffix.lower() == '.webp':
        with Image.open(path) as img:
            buf = io.BytesIO()
            img.save(buf, format='PNG')
        buf.seek(0)
        return buf
    return str(path)


def generate_word(
    state: StudioFormState,
    *,
    filled_only: bool = False,
) -> bytes:
    """生成 Word 文档，返回字节流。"""
    data = build_render_data(state, filled_only=filled_only)
    doc = Document()

    # 默认字体
    style = doc.styles['Normal']
    style.font.name = '微软雅黑'
    style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    # 页边距
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    # ── 标题 ──
    title = doc.add_heading('', level=0)
    title_run = title.add_run(f'{data["customer_name"]} — 直播间搭建需求确认书')
    title_run.font.name = '微软雅黑'
    title_run.font.size = Pt(18)
    title_run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 日期 + 进度
    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    info_run = info.add_run(
        f'生成日期：{date.today().strftime("%Y-%m-%d")}    '
        f'必填信息采集进度：{data["progress"]["filled"]}/{data["progress"]["total"]}（{data["progress"]["pct"]}%）'
    )
    info_run.font.size = Pt(9)
    info_run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    doc.add_paragraph('')

    # ── 各章节表格 ──
    for sec in data['sections']:
        if sec.get('skipped'):
            heading = doc.add_heading(sec['title'], level=2)
            p = doc.add_paragraph()
            run = p.add_run('（本章节已跳过）')
            run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
            continue

        if not sec['fields']:
            continue

        doc.add_heading(sec['title'], level=2)

        table = doc.add_table(rows=1 + len(sec['fields']), cols=2)
        table.style = 'Light Grid Accent 1'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # 表头
        _set_cell_font(table.rows[0].cells[0], '字段', bold=True)
        _set_cell_font(table.rows[0].cells[1], '内容', bold=True)

        # 数据行
        for i, f in enumerate(sec['fields'], 1):
            _set_cell_font(table.rows[i].cells[0], f['label'])
            _set_cell_font(table.rows[i].cells[1], f['value'])

        # 列宽
        for row in table.rows:
            row.cells[0].width = Cm(4.5)
            row.cells[1].width = Cm(11)

        # 图片字段：表格下方内嵌原图 + 图注
        for f in sec['fields']:
            for path in f.get('images', []):
                caption = doc.add_paragraph()
                caption_run = caption.add_run(f'{f["label"]}：')
                caption_run.font.size = Pt(9)
                caption_run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
                doc.add_picture(_image_source(path), width=Cm(12))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph('')

    # ── 设备明细 ──
    if data['equipment_table']:
        doc.add_heading('附：现有设备明细', level=2)
        eq_table = doc.add_table(rows=1 + len(data['equipment_table']), cols=3)
        eq_table.style = 'Light Grid Accent 1'
        for col, h in enumerate(['设备类型', '品牌型号', '数量']):
            _set_cell_font(eq_table.rows[0].cells[col], h, bold=True)
        for i, row in enumerate(data['equipment_table'], 1):
            for col, key in enumerate(['type', 'model', 'qty']):
                _set_cell_font(eq_table.rows[i].cells[col], row.get(key, ''))
        doc.add_paragraph('')

    # ── 签字栏 ──
    doc.add_heading('确认与签字', level=2)
    sign_table = doc.add_table(rows=2, cols=2)
    sign_table.style = 'Light Grid Accent 1'
    _set_cell_font(sign_table.rows[0].cells[0], '客户签字')
    _set_cell_font(sign_table.rows[0].cells[1], '')
    _set_cell_font(sign_table.rows[1].cells[0], '客服签字')
    _set_cell_font(sign_table.rows[1].cells[1], '')
    for row in sign_table.rows:
        row.cells[0].width = Cm(4.5)
        row.cells[1].width = Cm(11)

    doc.add_paragraph('')
    footer = doc.add_paragraph()
    footer_run = footer.add_run('本确认书由智能客服系统自动生成，经双方签字后生效。')
    footer_run.font.size = Pt(8)
    footer_run.font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
