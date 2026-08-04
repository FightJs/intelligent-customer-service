"""对话流程状态机（纯逻辑，不依赖 LLM）。

职责：
- 管理 10 章节的推进顺序
- 根据 visibleIf 跳过条件不可见字段
- 校验必填字段是否完整
- 给 agent 提供上下文（当前章节、进度、下一个该问的字段）

与前端 scriptedFlow.ts 的 visibleSteps 逻辑一致（基于 visibleIf），
但这里是后端权威版，agent 每轮调用决定推进方向。
"""
from __future__ import annotations

from survey.models import StudioFormState, SectionState, FieldValue
from survey.schema_def import (
    SECTIONS, SECTION_ORDER, SECTION_BY_ID, FIELD_BY_ID,
    SectionDef, FieldDef,
)


def is_field_visible(field: FieldDef, section: SectionState) -> bool:
    """字段是否可见（visibleIf 条件满足才可见）。"""
    if field.visible_if is None:
        return True
    dep_field_id = field.visible_if.field_id
    dep_value_raw = section.fields.get(dep_field_id)
    if dep_value_raw is None:
        return True
    # 只处理 choice-single 依赖
    if not hasattr(dep_value_raw, 'value'):
        return True
    dep_value = dep_value_raw.value
    if dep_value is None:
        return False  # 依赖字段未填，隐藏字段
    if field.visible_if.op == 'eq':
        return dep_value == field.visible_if.value
    return dep_value != field.visible_if.value


def value_is_empty(v: FieldValue) -> bool:
    """字段值是否为空。"""
    if v.type == 'text':
        return v.value.strip() == ''
    if v.type == 'choice-single':
        return v.value is None
    if v.type == 'choice-multi':
        return len(v.value) == 0
    if v.type == 'dimension':
        return all(n.strip() == '' for n in v.value.values())
    if v.type == 'image':
        return len(v.value) == 0
    if v.type == 'table':
        return len(v.value) == 0
    return True


def is_field_required(
    state: StudioFormState,
    section_id: str,
    field: FieldDef,
) -> bool:
    """判断字段在当前表单状态下是否必填。"""
    if field.required:
        return True

    if (
        section_id == 'equipment'
        and field.id == 'inventory'
    ):
        has_existing = state.sections[
            'budget'
        ].fields['has_existing']

        return has_existing.value == 'yes'

    return False


def value_to_text(v: FieldValue, field: FieldDef) -> str:
    """字段值转可读文本（给 agent 和交付物用）。"""
    if value_is_empty(v):
        return ''
    if v.type == 'text':
        return v.value
    if v.type == 'choice-single':
        if v.value is None:
            return ''
        opt = next((o for o in (field.options or []) if o.value == v.value), None)
        return opt.label if opt else v.value
    if v.type == 'choice-multi':
        labels = []
        for val in v.value:
            opt = next((o for o in (field.options or []) if o.value == val), None)
            labels.append(opt.label if opt else val)
        return '、'.join(labels)
    if v.type == 'dimension':
        parts = [f'{k}{n}' for k, n in v.value.items() if n.strip()]
        unit = field.unit or ''
        return f'{"×".join(parts)}{unit}'
    if v.type == 'image':
        return f'{len(v.value)}张图'
    if v.type == 'table':
        return f'{len(v.value)}行'
    return ''


def visible_fields(state: StudioFormState) -> list[tuple[str, FieldDef]]:
    """返回所有可见字段 [(section_id, field_def), ...]，按章节顺序。"""
    result = []
    for sec_id in SECTION_ORDER:
        sec_def = SECTION_BY_ID[sec_id]
        sec_state = state.sections[sec_id]
        if sec_state.status == 'skipped':
            continue
        for f in sec_def.fields:
            if is_field_visible(f, sec_state):
                result.append((sec_id, f))
    return result


def filled_required_count(
    state: StudioFormState,
    section_id: str,
) -> tuple[int, int]:
    """计算章节必填字段的已填数和总数。"""
    section = SECTION_BY_ID[section_id]
    section_state = state.sections[section_id]

    filled = 0
    total = 0

    for field in section.fields:
        if not is_field_required(
            state,
            section_id,
            field,
        ):
            continue

        if not is_field_visible(
            field,
            section_state,
        ):
            continue

        total += 1

        value = section_state.fields.get(
            field.id
        )

        if (
            value is not None
            and not value_is_empty(value)
        ):
            filled += 1

    return filled, total


def next_unfilled_field(
    state: StudioFormState,
) -> tuple[str, FieldDef] | None:
    """找到下一个需要填写的字段。"""
    equipment_field = next(
        field
        for field in SECTION_BY_ID[
            'equipment'
        ].fields
        if field.id == 'inventory'
    )

    equipment_value = state.sections[
        'equipment'
    ].fields['inventory']

    if (
        is_field_required(
            state,
            'equipment',
            equipment_field,
        )
        and value_is_empty(equipment_value)
    ):
        return 'equipment', equipment_field

    for section_id, field in visible_fields(state):
        if not is_field_required(
            state,
            section_id,
            field,
        ):
            continue

        value = state.sections[
            section_id
        ].fields.get(field.id)

        if value is None or value_is_empty(value):
            return section_id, field

    return None


def section_progress(state: StudioFormState) -> list[dict]:
    """各章节进度摘要（给 agent 上下文用）。"""
    result = []
    for sec_id in SECTION_ORDER:
        sec_def = SECTION_BY_ID[sec_id]
        sec_state = state.sections[sec_id]
        filled, total = filled_required_count(state,sec_id,)
        result.append({
            'section_id': sec_id,
            'title': sec_def.title,
            'status': sec_state.status,
            'filled': filled,
            'total': total,
            'complete': filled >= total if total > 0 else True,
        })
    return result


def form_complete(state: StudioFormState) -> bool:
    """所有必填可见字段是否都填完。"""
    return next_unfilled_field(state) is None


def overall_progress(
    state: StudioFormState,
) -> tuple[int, int]:
    """全局已填必填数和必填总数。"""
    filled_total = 0
    count_total = 0

    for sec_id in SECTION_ORDER:
        filled, total = filled_required_count(
            state,
            sec_id,
        )

        filled_total += filled
        count_total += total

    return filled_total, count_total


def current_section_for_agent(state: StudioFormState) -> str:
    """当前 agent 应聚焦的章节 id（下一个未填必填字段所在章节）。"""
    nxt = next_unfilled_field(state)
    if nxt is None:
        return SECTION_ORDER[-1]
    return nxt[0]


def skip_section(state: StudioFormState, section_id: str) -> None:
    """标记章节为跳过（条件分支用，如没有直播间→跳过现状章）。"""
    if section_id in state.sections:
        state.sections[section_id].status = 'skipped'


def recompute_section_status(state: StudioFormState) -> None:
    """按必填字段填充情况重算所有章节的 status（原地修改）。

    - skipped 保持
    - 全部必填填完 → complete
    - 部分填或为当前章节 → active
    - 全空 → pending
    """
    for sec_id in SECTION_ORDER:
        sec_def = SECTION_BY_ID[sec_id]
        sec_state = state.sections[sec_id]
        if sec_state.status == 'skipped':
            continue
        filled, total = filled_required_count( state,sec_id,)
        if total > 0 and filled >= total:
            sec_state.status = 'complete'
        elif filled > 0 or sec_id == state.current_section_id:
            sec_state.status = 'active'
        else:
            sec_state.status = 'pending'
