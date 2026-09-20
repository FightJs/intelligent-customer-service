"""方案 PDF 渲染（jinja2 HTML → WeasyPrint）与 Word 降级。"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from delivery.plan_word import generate_plan_word
from pipeline.normalize import industry_label

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent / 'templates'


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=select_autoescape(['html', 'xml']),
    )


def render_plan_html(
    plan: dict,
    brief: dict,
    *,
    incomplete: bool = False,
    knowledge_degraded: bool = False,
) -> str:
    layout = plan.get('layout') or {}
    scene_card = plan.get('scene_card') or {}
    template = _env().get_template('plan.html')
    return template.render(
        title=f'{brief.get("brand") or "直播间"} 搭建方案',
        brand=brief.get('brand') or '',
        industry_label=industry_label(brief.get('industry') or ''),
        subcategory=brief.get('subcategory') or '',
        area_band=brief.get('area_band') or '',
        room_size=brief.get('room_size') or 'medium',
        budget_total=brief.get('budget_total') or '',
        budget_equip=brief.get('budget_equip') or '',
        budget_decor=brief.get('budget_decor') or '',
        price_band=brief.get('price_band') or '',
        positioning=brief.get('positioning') or '',
        live_type=brief.get('live_type') or '',
        goal_core=brief.get('goal_core') or '',
        goal_focus=brief.get('goal_focus') or [],
        product_main=brief.get('product_main') or '',
        product_keywords=brief.get('product_keywords') or [],
        host_count=brief.get('host_count') or '',
        host_movement=brief.get('host_movement') or '',
        window=brief.get('window') or '',
        window_pos=brief.get('window_pos') or '',
        renovation=brief.get('renovation') or '',
        existing_equipment=brief.get('existing_equipment') or [],
        generated_date=date.today().strftime('%Y-%m-%d'),
        incomplete=incomplete,
        knowledge_degraded=knowledge_degraded,
        summary=plan.get('summary') or '',
        layout={
            'zones': layout.get('zones') or [],
            'lighting_plan': layout.get('lighting_plan') or '',
            'camera_plan': layout.get('camera_plan') or '',
            'background_plan': layout.get('background_plan') or '',
        },
        equipment_list=plan.get('equipment_list') or [],
        package_tiers=plan.get('package_tiers') or [],
        setup_steps=plan.get('setup_steps') or [],
        risks=plan.get('risks') or [],
        layout_scale=(plan.get('meta') or {}).get('layout_scale') or '',
        must_buy_list=plan.get('must_buy_list') or [],
        rental_channels=plan.get('rental_channels') or [],
        vertical_notes=plan.get('vertical_notes') or [],
        scene_card={
            'style_keywords': scene_card.get('style_keywords') or [],
            'color_palette': scene_card.get('color_palette') or [],
            'color_temp': scene_card.get('color_temp') or '',
            'furniture': scene_card.get('furniture') or [],
            'lighting_fixtures': scene_card.get('lighting_fixtures') or [],
            'camera_angles': scene_card.get('camera_angles') or [],
            'forbidden': scene_card.get('forbidden') or [],
        },
        knowledge_refs=(plan.get('meta') or {}).get('knowledge_refs') or [],
    )


def weasyprint_available() -> bool:
    try:
        import weasyprint  # noqa: F401
        return True
    except Exception:
        return False


def render_plan_pdf(
    plan: dict,
    brief: dict,
    *,
    incomplete: bool = False,
    knowledge_degraded: bool = False,
) -> bytes:
    """渲染 PDF。WeasyPrint 不可用或失败时抛出异常，由调用方降级 Word。"""
    from weasyprint import HTML  # 延迟导入，避免缺系统库时拖垮模块

    html = render_plan_html(
        plan,
        brief,
        incomplete=incomplete,
        knowledge_degraded=knowledge_degraded,
    )
    return HTML(string=html, base_url=str(_TEMPLATE_DIR)).write_pdf()


def render_plan_document(
    plan: dict,
    brief: dict,
    *,
    incomplete: bool = False,
    knowledge_degraded: bool = False,
) -> tuple[bytes | None, bytes | None, list[str]]:
    """优先 PDF，失败降级 Word。返回 (pdf_bytes, word_bytes, warnings)。"""
    warnings: list[str] = []
    pdf_bytes: bytes | None = None
    word_bytes: bytes | None = None

    try:
        pdf_bytes = render_plan_pdf(
            plan,
            brief,
            incomplete=incomplete,
            knowledge_degraded=knowledge_degraded,
        )
    except Exception as exc:
        logger.warning('WeasyPrint render failed: %s', exc)
        warnings.append(f'PDF 渲染失败，已降级 Word：{exc}')

    if pdf_bytes is None:
        word_bytes = generate_plan_word(
            plan,
            brief,
            incomplete=incomplete,
            knowledge_degraded=knowledge_degraded,
        )
    return pdf_bytes, word_bytes, warnings
