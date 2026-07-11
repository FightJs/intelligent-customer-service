"""Excel 交付物生成（设备参数清单）。

两份数据：
1. 现有设备明细（来自调研表第八节，用户填的）
2. 推荐设备清单（根据预算和需求生成模板建议）
"""
from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from delivery.render_data import build_render_data
from survey.models import StudioFormState
from survey.schema_def import SECTION_BY_ID
from agent.flow import value_to_text

# 标题样式
_HEADER_FONT = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
_HEADER_FILL = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
_TITLE_FONT = Font(name='微软雅黑', size=14, bold=True)
_BODY_FONT = Font(name='微软雅黑', size=10)
_THIN_BORDER = Border(
    left=Side(style='thin'), right=Side(style='thin'),
    top=Side(style='thin'), bottom=Side(style='thin'),
)

# 按预算档位的推荐设备模板
_RECOMMEND_TEMPLATES = {
    '<1w': [
        ('相机', '手机/罗技 C920', '1-2', '入门级，手机或高清摄像头'),
        ('主灯', '南光 Fotodiox 60W', '2', '常亮灯'),
        ('辅灯', '柔光板反光', '1', '补光'),
        ('麦克风', '罗德 Wireless GO', '1', '无线领夹麦'),
    ],
    '1-3w': [
        ('相机', 'Sony ZV-E10', '1', '入门微单'),
        ('镜头', 'Sigma 16mm F1.4', '1', '广角定焦'),
        ('主灯', '神牛 SL150W', '2', 'LED 常亮灯'),
        ('辅灯', '神牛 FL-150G', '1', '柔光灯'),
        ('背景灯', '南光 P200C', '2', ' RGB 氛围灯'),
        ('麦克风', '罗德 Wireless GO II', '1', '双通道无线麦'),
    ],
    '3-5w': [
        ('相机', 'Sony A6700', '2', '中端微单，双机位'),
        ('镜头', 'Sigma 18-35mm F1.8', '1', '变焦广角'),
        ('主灯', '神牛 SL200W II', '2', '高功率 LED'),
        ('辅灯', '神牛 FL-150G', '2', '柔光'),
        ('背景灯', '南光 P200C', '2', 'RGB 氛围灯'),
        ('柔光设备', '1.5m 柔光箱', '2', '大型柔光'),
        ('麦克风', '大疆 DJI Mic 2', '1', '双通道无线麦'),
    ],
    '5-10w': [
        ('相机', 'Sony A7M4', '2', '全画幅，双机位'),
        ('镜头', 'Sony 24-70mm F2.8 GM', '1', '大师级变焦'),
        ('主灯', '爱图仕 300X', '2', '专业级 LED'),
        ('辅灯', '神牛 FL-150G', '2', '柔光'),
        ('背景灯', '爱图仕 MC Pro', '2', 'RGB 全彩'),
        ('柔光设备', '2m 柔光箱', '2', '超大柔光'),
        ('麦克风', '大疆 DJI Mic 2', '2', '双通道无线麦'),
    ],
}


def _style_header_row(ws, row_idx: int, col_count: int) -> None:
    for col in range(1, col_count + 1):
        cell = ws.cell(row=row_idx, column=col)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.border = _THIN_BORDER
        cell.alignment = Alignment(horizontal='center', vertical='center')


def _style_body_cell(cell) -> None:
    cell.font = _BODY_FONT
    cell.border = _THIN_BORDER
    cell.alignment = Alignment(vertical='center', wrap_text=True)


def generate_excel(state: StudioFormState) -> bytes:
    """生成 Excel 文件，返回字节流。"""
    data = build_render_data(state)
    wb = Workbook()

    # ── Sheet 1: 现有设备明细 ──
    ws1 = wb.active
    ws1.title = '现有设备'

    ws1.merge_cells('A1:D1')
    ws1['A1'] = f'{data["customer_name"]} — 现有设备明细'
    ws1['A1'].font = _TITLE_FONT
    ws1['A1'].alignment = Alignment(horizontal='center')

    headers = ['设备类型', '品牌型号', '数量', '备注']
    for col, h in enumerate(headers, 1):
        ws1.cell(row=3, column=col, value=h)
    _style_header_row(ws1, 3, 4)

    if data['equipment_table']:
        for row_idx, row in enumerate(data['equipment_table'], 4):
            for col, key in enumerate(['type', 'model', 'qty', 'note'], 1):
                cell = ws1.cell(row=row_idx, column=col, value=row.get(key, ''))
                _style_body_cell(cell)
    else:
        ws1.merge_cells('A4:D4')
        ws1['A4'] = '（无现有设备记录）'
        ws1['A4'].alignment = Alignment(horizontal='center')
        ws1['A4'].font = _BODY_FONT

    for col, width in enumerate([16, 28, 10, 30], 1):
        ws1.column_dimensions[chr(64 + col)].width = width

    # ── Sheet 2: 推荐设备清单 ──
    ws2 = wb.create_sheet('推荐设备')

    # 查预算档位
    budget_sec = state.sections.get('budget')
    budget_key = ''
    if budget_sec:
        total_field = budget_sec.fields.get('total')
        if total_field and total_field.type == 'choice-single' and total_field.value:
            budget_key = total_field.value

    recommend = _RECOMMEND_TEMPLATES.get(budget_key, _RECOMMEND_TEMPLATES['3-5w'])

    ws2.merge_cells('A1:D1')
    budget_label = SECTION_BY_ID['budget'].fields[0]  # total 字段
    total_opt = next((o for o in budget_label.options if o.value == budget_key), None)
    budget_text = total_opt.label if total_opt else '未指定'
    ws2['A1'] = f'{data["customer_name"]} — 推荐设备方案（预算：{budget_text}）'
    ws2['A1'].font = _TITLE_FONT
    ws2['A1'].alignment = Alignment(horizontal='center')

    for col, h in enumerate(headers, 1):
        ws2.cell(row=3, column=col, value=h)
    _style_header_row(ws2, 3, 4)

    for row_idx, (dtype, model, qty, note) in enumerate(recommend, 4):
        for col, val in enumerate([dtype, model, qty, note], 1):
            cell = ws2.cell(row=row_idx, column=col, value=val)
            _style_body_cell(cell)

    for col, width in enumerate([16, 28, 10, 30], 1):
        ws2.column_dimensions[chr(64 + col)].width = width

    # 输出字节流
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
