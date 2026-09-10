"""交付说明 README 生成。

规则优先、确定性输出；LLM 仅润色（可选注入，失败回退模板）。
禁止声称不存在的媒体（R6）——模板只引用真实存在的文件。
"""
from __future__ import annotations

from typing import Any, Callable

from pipeline.models import PlanDraft
from pipeline.validate import IMAGE_ANGLE_LABELS, ValidationResult

# LLM 协议：async 或 sync 均可由调用方包装；这里只要同步 callable
ReadmeLLM = Callable[[str], str]

_FORBIDDEN_CLAIM_PATTERNS = (
    '完整三机位',
    '三张完整',
    '三机位齐全',
    '预览视频已生成',
    '视频已生成',
)


def build_readme_context(
    *,
    brand: str,
    summary: str,
    plan: PlanDraft,
    equipment_list: list[dict[str, Any]],
    present_images: list[dict[str, str]],  # {angle, path}
    video_included: bool,
    validation: ValidationResult,
    has_plan_pdf: bool,
    has_equipment_xlsx: bool,
) -> dict[str, Any]:
    return {
        'brand': brand,
        'summary': summary,
        'package_tiers': [t.model_dump() for t in plan.package_tiers],
        'setup_steps': list(plan.setup_steps),
        'risks': list(plan.risks),
        'equipment_count': len(equipment_list),
        'equipment_list': list(equipment_list),
        'present_images': present_images,
        'missing_angles': [
            g.split(':', 1)[1]
            for g in validation.gaps
            if g.startswith('missing_angle:')
        ],
        'video_included': video_included,
        'has_plan_pdf': has_plan_pdf,
        'has_equipment_xlsx': has_equipment_xlsx,
        'warnings': validation.warning_messages,
        'gaps': list(validation.gaps),
        'removed_equipment': validation.removed_equipment,
    }


def _tier_lines(tiers: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for t in tiers:
        lines.append(f"- **{t.get('tier', '套餐')}**：{t.get('total_range') or '金额待确认'}")
        items = t.get('items') or []
        for item in items[:8]:
            name = item.get('name') or item.get('model') or ''
            qty = item.get('qty', 1)
            if name:
                lines.append(f"  - {name} × {qty}")
    return lines


def render_readme_template(ctx: dict[str, Any]) -> str:
    """确定性中文交付说明。仅描述真实存在的产物。"""
    brand = ctx['brand'] or '本方案'
    lines: list[str] = []
    lines.append(f'# {brand} · 直播间智能交付包')
    lines.append('')

    # R7 顶部显著标注
    if any(g == 'form_incomplete' for g in ctx['gaps']):
        lines.append('> **注意**：调研表部分核心字段未填写完整，方案精度可能受限，请以确认后的需求为准。')
        lines.append('')

    if ctx['summary']:
        lines.append(f"**方案定位**：{ctx['summary']}")
        lines.append('')

    lines.append('## 包内文件')
    lines.append('')
    lines.append('| 文件 | 说明 |')
    lines.append('|------|------|')
    lines.append('| `docs/plan.pdf` | 方案文档（设备清单 / 套餐 / 搭建规划） |' if ctx['has_plan_pdf'] else '| `docs/plan.pdf` | 未生成 |')
    lines.append('| `docs/plan.json` | 机器可读方案真相源 |')
    if ctx['has_equipment_xlsx']:
        lines.append('| `docs/equipment.xlsx` | 设备清单表格 |')
    if ctx['present_images']:
        lines.append('| `images/preview_*.png` | 多机位预览图 |')
    if ctx['video_included']:
        lines.append('| `video/preview.mp4` | 空间预览视频 |')
    lines.append('| `manifest.json` | 文件清单与完整性哈希 |')
    lines.append('')

    equipment_list = ctx['equipment_list']
    if equipment_list:
        lines.append('## 设备清单摘要')
        lines.append('')
        lines.append(f'共 **{len(equipment_list)}** 项（完整参数见 `docs/plan.json` 与 `docs/plan.pdf`）：')
        lines.append('')
        for item in equipment_list[:12]:
            name = item.get('name') or item.get('model') or '未命名'
            qty = item.get('qty', 1)
            cat = item.get('category') or ''
            custom = '（定制）' if item.get('is_custom') else ''
            lines.append(f'- {cat}：{name} × {qty}{custom}')
        if len(equipment_list) > 12:
            lines.append(f'- … 另有 {len(equipment_list) - 12} 项，详见方案文档')
        lines.append('')

    lines.append('## 如何看多机位预览图')
    lines.append('')
    if ctx['present_images']:
        lines.append('同一场景、不同机位的静帧，用于快速判断空间关系与氛围：')
        lines.append('')
        for img in ctx['present_images']:
            label = IMAGE_ANGLE_LABELS.get(img['angle'], img['angle'])
            lines.append(f"- **{label}**（`{img['path']}`）")
        if ctx['missing_angles']:
            miss = '、'.join(
                IMAGE_ANGLE_LABELS.get(a, a) for a in ctx['missing_angles']
            )
            lines.append('')
            lines.append(f"> 缺失机位：{miss}。缺失机位不影响方案主文件使用，如需补齐可联系顾问重跑预览。")
    else:
        lines.append('本包**不含预览图**（生成失败或未执行）。请优先阅读 `docs/plan.pdf` 中的空间与布局章节。')
    lines.append('')

    lines.append('## 预览视频')
    lines.append('')
    if ctx['video_included']:
        lines.append('见 `video/preview.mp4`，用于感受空间尺度、布光氛围与动线，时长约 5–15 秒。')
    else:
        lines.append('本包**不含预览视频**（生成失败或未执行）。可先结合多机位静帧与 PDF 方案理解空间；如需视频可单独申请重跑。')
    lines.append('')

    lines.append('## 如何选套餐')
    lines.append('')
    if ctx['package_tiers']:
        lines.append('按预算与效果目标选择一档，细节以 `docs/plan.pdf` 与 `docs/plan.json` 为准：')
        lines.append('')
        lines.extend(_tier_lines(ctx['package_tiers']))
        lines.append('')
        lines.append('选购建议：优先满足主灯与主机位成像；背景与氛围灯可在第二阶段加装。')
    else:
        lines.append('本包未包含多档套餐，请以设备清单与顾问沟通定制。')
    lines.append('')

    if ctx['setup_steps']:
        lines.append('## 搭建步骤摘要')
        lines.append('')
        for step in ctx['setup_steps'][:8]:
            lines.append(f'- {step}')
        lines.append('')

    if ctx['risks']:
        lines.append('## 风险与提示')
        lines.append('')
        for risk in ctx['risks']:
            lines.append(f'- {risk}')
        lines.append('')

    if ctx['removed_equipment']:
        lines.append('## 清单调整说明')
        lines.append('')
        lines.append('以下设备因知识库无法核验已从交付清单剔除，不影响其他推荐项：')
        lines.append('')
        for item in ctx['removed_equipment']:
            lines.append(f"- {item.get('name') or item.get('model') or '未命名设备'}")
        lines.append('')

    if ctx['warnings']:
        lines.append('## 交付备注')
        lines.append('')
        for w in ctx['warnings']:
            lines.append(f'- {w}')
        lines.append('')

    lines.append('## 下一步')
    lines.append('')
    lines.append('1. 查阅 `docs/plan.pdf`，确认设备清单与套餐。')
    if ctx['present_images']:
        lines.append('2. 对照多机位预览图，核对空间布局与氛围是否符合预期。')
    else:
        lines.append('2. 如需空间效果参考，可联系顾问补生成预览图。')
    if ctx['video_included']:
        lines.append('3. 观看预览视频，评估动线与展示角度。')
    else:
        lines.append('3. 视频未包含在本包中，可在下一轮迭代申请。')
    lines.append('4. 与顾问确认采购清单、到货周期与上门搭建排期。')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('*本说明由智能交付管线自动生成。设备型号、数量与价格区间以 `docs/plan.json` 为准，本文不构成正式报价。*')
    lines.append('')
    return '\n'.join(lines)


def _llm_prompt(ctx: dict[str, Any]) -> str:
    return (
        '你是直播间搭建顾问助手。请根据以下事实撰写中文交付说明 README（Markdown）。\n'
        '硬性约束：\n'
        '1. 不得增删设备型号、不得改数量或价格区间。\n'
        '2. 不得声称未生成的图片/视频；缺失必须如实说明。\n'
        '3. 不得写「完整三机位」等绝对化表述，除非 present_images 确实有 front/left/rear。\n'
        '4. 必须包含：包内文件、如何看图、如何选套餐、下一步建议。\n'
        f'事实 JSON：\n{ctx}\n'
    )


def sanitize_llm_readme(text: str, ctx: dict[str, Any]) -> str:
    """R6：剥离 LLM 可能编造的媒体声称。"""
    cleaned = text.strip() + '\n'
    video_ok = ctx['video_included']
    images_ok = len(ctx['present_images']) >= 3
    if not video_ok:
        for pat in (
            '预览视频已生成',
            '视频已生成',
            '请观看预览视频',
            '请观看 video/preview.mp4',
            '见 `video/preview.mp4`',
            '观看预览视频',
        ):
            cleaned = cleaned.replace(pat, '本包不含预览视频')
        cleaned = cleaned.replace('video/preview.mp4', '（未生成视频文件）')
    if not images_ok:
        for pat in _FORBIDDEN_CLAIM_PATTERNS:
            cleaned = cleaned.replace(pat, '多机位预览（部分机位）')
    return cleaned


def generate_readme(
    *,
    brand: str,
    summary: str,
    plan: PlanDraft,
    equipment_list: list[dict[str, Any]],
    present_images: list[dict[str, str]],
    video_included: bool,
    validation: ValidationResult,
    has_plan_pdf: bool,
    has_equipment_xlsx: bool,
    llm: ReadmeLLM | None = None,
) -> str:
    ctx = build_readme_context(
        brand=brand,
        summary=summary,
        plan=plan,
        equipment_list=equipment_list,
        present_images=present_images,
        video_included=video_included,
        validation=validation,
        has_plan_pdf=has_plan_pdf,
        has_equipment_xlsx=has_equipment_xlsx,
    )
    template = render_readme_template(ctx)
    if llm is None:
        return template
    try:
        enhanced = llm(_llm_prompt(ctx))
    except Exception:
        return template
    if not enhanced or not enhanced.strip():
        return template
    return sanitize_llm_readme(enhanced, ctx)
