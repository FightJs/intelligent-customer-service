"""PlanDraft 硬校验（F2）+ F5 交叉校验。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from knowledge.mapping import parse_budget_wan
from pipeline.budget import budget_tolerance, parse_money_range, tier_within_budget
from pipeline.models import (
    EquipmentItem,
    PlanDocumentOutput,
    PlanDraft,
    PreviewImagesOutput,
    PreviewVideoOutput,
    RequirementBrief,
)

TIER_NAMES = ('性价比', '进阶', '高配')
IMAGE_ANGLE_LABELS = {
    'front': '正面主视角',
    'left': '左侧 120°',
    'rear': '背面/右侧 240°',
}


def _range_mid(bounds: tuple[float, float]) -> float:
    return (bounds[0] + bounds[1]) / 2.0


def validate_plan(
    draft: PlanDraft,
    brief: RequirementBrief,
) -> tuple[list[str], list[str]]:
    """返回 (warnings, hard_errors)。hard_errors 非空 → skill failed。"""
    warnings: list[str] = []
    errors: list[str] = []

    if not draft.summary.strip():
        errors.append('summary 为空')
    if not draft.layout.zones and not draft.layout.lighting_plan.strip():
        errors.append('layout 为空')
    if len(draft.setup_steps) < 3:
        errors.append(f'setup_steps 不足 3 条（当前 {len(draft.setup_steps)}）')

    cleaned_equipment = []
    for item in draft.equipment_list:
        if item.knowledge_id is None and not item.is_custom:
            warnings.append(f'设备「{item.name}」缺少 knowledge_id 且未标注 is_custom，已剔除')
            continue
        cleaned_equipment.append(item)
    draft.equipment_list = cleaned_equipment

    if len(draft.package_tiers) < 2:
        warnings.append('套餐档位不足，已按预算补全至两档及以上')
        draft.package_tiers = _ensure_min_tiers(draft, brief)

    tier_names = [tier.tier for tier in draft.package_tiers]
    for expected in TIER_NAMES:
        if expected not in tier_names and len(draft.package_tiers) >= 3:
            warnings.append(f'缺少套餐档位「{expected}」')

    budget_bounds = parse_budget_wan(brief.budget_total)
    flex = brief.budget_flex
    tolerance = 0.25 if flex == 'flexible' else 0.10
    if budget_bounds:
        budget_mid = _range_mid(budget_bounds)
        low = budget_mid * (1 - tolerance)
        high = budget_mid * (1 + tolerance)
        for tier in draft.package_tiers:
            tier_bounds = parse_budget_wan(tier.total_range)
            if tier_bounds is None:
                warnings.append(f'套餐「{tier.tier}」金额区间无法解析：{tier.total_range}')
                continue
            tier_mid = _range_mid(tier_bounds)
            if tier_mid < low or tier_mid > high:
                warnings.append(
                    f'套餐「{tier.tier}」金额 {tier.total_range} '
                    f'与总预算 {brief.budget_total} 偏差超过 {int(tolerance * 100)}%'
                )

    if not draft.scene_card.style_keywords and brief.product_keywords:
        draft.scene_card.style_keywords = list(brief.product_keywords)
    if not draft.scene_card.product_category:
        draft.scene_card.product_category = brief.product_main or brief.subcategory
    if not draft.scene_card.room_size_band:
        draft.scene_card.room_size_band = brief.room_size

    return warnings, errors


def _ensure_min_tiers(draft: PlanDraft, brief: RequirementBrief) -> list:
    """预算极低时允许两档；否则补三档骨架。"""
    from pipeline.models import PackageTier

    existing = list(draft.package_tiers)
    if len(existing) >= 2:
        return existing
    budget_bounds = parse_budget_wan(brief.budget_total) or (1.0, 2.0)
    mid = _range_mid(budget_bounds)
    low_range = f'{mid * 0.6:.1f}-{mid * 0.8:.1f}w'
    high_range = f'{mid * 0.9:.1f}-{mid * 1.1:.1f}w'
    if not existing:
        existing.append(PackageTier(tier='性价比', total_range=low_range, items=[]))
    existing.append(PackageTier(tier='进阶', total_range=high_range, items=[]))
    return existing


# ──────────────────────────────────────────────────────────────
# F5 交叉校验
# ──────────────────────────────────────────────────────────────

@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: str = 'warning'  # warning | error


@dataclass
class ValidationResult:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    equipment_list: list[dict[str, Any]] = field(default_factory=list)
    removed_equipment: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_error(self) -> bool:
        return bool(self.errors)

    @property
    def warning_messages(self) -> list[str]:
        return [w.message for w in self.warnings]

    def add_gap(self, gap: str) -> None:
        if gap not in self.gaps:
            self.gaps.append(gap)

    def add_warning(self, code: str, message: str) -> None:
        self.warnings.append(ValidationIssue(code=code, message=message))


def _form_completeness(form_state: dict[str, Any]) -> float:
    if not form_state:
        return 0.0
    try:
        from pipeline.normalize import normalize_form_state

        return normalize_form_state(form_state).completeness
    except Exception:
        return 0.5


def extract_form_field(form_state: dict[str, Any] | None, dotted_key: str) -> Any:
    """从 form_state 取 `section.field` 文本值（仅支持 text/choice-single）。"""
    if not form_state or '.' not in dotted_key:
        return None
    section_id, field_id = dotted_key.split('.', 1)
    section = (form_state.get('sections') or {}).get(section_id) or {}
    fields = section.get('fields') or {}
    field = fields.get(field_id) or {}
    value = field.get('value')
    if isinstance(value, str):
        return value.strip()
    return value


def run_validation(
    *,
    plan_output: PlanDocumentOutput,
    plan: PlanDraft,
    images_output: PreviewImagesOutput,
    video_output: PreviewVideoOutput,
    form_state: dict[str, Any] | None = None,
    known_knowledge_ids: set[int] | None = None,
) -> ValidationResult:
    """F5 硬规则交叉校验。"""
    result = ValidationResult()

    # R7: 需求不完整 —— F5 轻量检查：品牌缺失或几乎空表
    if form_state is not None:
        brand = extract_form_field(form_state, 'customer.brand')
        sections = (form_state.get('sections') or {}) if isinstance(form_state, dict) else {}
        filled_fields = 0
        for section in sections.values():
            for field in (section.get('fields') or {}).values():
                value = field.get('value')
                if isinstance(value, str) and value.strip():
                    filled_fields += 1
                elif isinstance(value, (list, dict)) and value:
                    filled_fields += 1
        if not brand or filled_fields < 3:
            result.add_gap('form_incomplete')
            result.add_warning(
                'form_incomplete',
                '调研表信息不完整，方案细节可能需要人工复核',
            )

    # R1: 设备可追溯
    cleaned: list[EquipmentItem] = []
    for item in plan.equipment_list:
        if item.knowledge_id is None and not item.is_custom:
            result.removed_equipment.append(item.model_dump())
            result.add_warning(
                'equipment_untraced',
                f'设备「{item.name}」缺少 knowledge_id 且非定制，已剔除',
            )
            continue
        if (
            known_knowledge_ids is not None
            and item.knowledge_id is not None
            and item.knowledge_id not in known_knowledge_ids
        ):
            result.add_warning(
                'equipment_unknown_id',
                f'设备「{item.name}」knowledge_id={item.knowledge_id} 在知识库不存在',
            )
        cleaned.append(item)
    plan.equipment_list = cleaned
    result.equipment_list = [item.model_dump() for item in cleaned]

    # R2: 主推套餐与预算自洽（只校验「进阶」或中间档，低档性价比允许更低）
    budget_text = ''
    flex = ''
    if plan_output.requirement_brief:
        budget_text = plan_output.requirement_brief.get('budget_total') or ''
        flex = plan_output.requirement_brief.get('budget_flex') or ''
    if not budget_text and plan.meta:
        budget_text = str(plan.meta.get('budget_total') or '')
    budget_range = parse_money_range(budget_text) if budget_text else None
    tolerance = budget_tolerance(flex)
    if budget_range and plan.package_tiers:
        primary = next(
            (t for t in plan.package_tiers if t.tier == '进阶'),
            plan.package_tiers[len(plan.package_tiers) // 2],
        )
        tier_range = parse_money_range(primary.total_range)
        if tier_range is None:
            result.add_warning(
                'budget_parse_failed',
                f'套餐「{primary.tier}」金额区间无法解析：{primary.total_range}',
            )
        elif not tier_within_budget(tier_range, budget_range, tolerance):
            result.add_warning(
                'budget_mismatch',
                f'套餐「{primary.tier}」金额 {primary.total_range} 与预算 {budget_text} 偏差超过允许范围',
            )

    # 媒体缺口
    if images_output.status != 'succeeded':
        result.add_gap('images_failed')
    elif images_output.status == 'partial':
        result.add_gap('images_partial')
    if video_output.status != 'succeeded':
        result.add_gap('video_failed')

    return result

