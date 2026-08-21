"""调研问答状态机。

分别处理问卷推进、核心提交完整性和跳过权限，避免把“选填”误解为“不问”。
"""
from __future__ import annotations

from survey.models import StudioFormState, SectionState, FieldValue
from survey.schema_def import (
    SECTION_ORDER,
    SECTION_BY_ID,
    SectionDef,
    FieldDef,
    VisibleIf,
)


def field_key(section_id: str, field_id: str) -> str:
    return f'{section_id}.{field_id}'


def _condition_value(
    state: StudioFormState,
    owner_section_id: str,
    condition: VisibleIf,
) -> object | None:
    if '.' in condition.field_id:
        section_id, dependency_id = condition.field_id.split('.', 1)
    else:
        section_id, dependency_id = owner_section_id, condition.field_id

    section = state.sections.get(section_id)
    if section is None:
        return None
    dependency = section.fields.get(dependency_id)
    return getattr(dependency, 'value', None)


def _condition_matches(value: object | None, condition: VisibleIf) -> bool:
    if value is None:
        return False
    if condition.op == 'eq':
        return value == condition.value
    return value != condition.value


def is_section_visible(state: StudioFormState, section: SectionDef) -> bool:
    if section.visible_if is None:
        return True
    value = _condition_value(state, section.id, section.visible_if)
    return _condition_matches(value, section.visible_if)


def is_field_visible(field: FieldDef, section: SectionState) -> bool:
    """判断同章节条件字段是否可见，保留原公开签名。"""
    if field.visible_if is None:
        return True
    dependency = section.fields.get(field.visible_if.field_id)
    value = getattr(dependency, 'value', None)
    return _condition_matches(value, field.visible_if)


def value_is_empty(value: FieldValue) -> bool:
    if value.type == 'text':
        return value.value.strip() == ''
    if value.type == 'choice-single':
        return value.value is None
    if value.type == 'choice-multi':
        return len(value.value) == 0
    if value.type == 'dimension':
        return all(number.strip() == '' for number in value.value.values())
    if value.type == 'image':
        return len(value.value) == 0
    if value.type == 'table':
        return len(value.value) == 0
    return True


def is_field_required(
    state: StudioFormState,
    section_id: str,
    field: FieldDef,
) -> bool:
    if state.mode == 'quick':
        return field_key(section_id, field.id) in state.required_field_ids
    return field.required


def is_field_skipped(
    state: StudioFormState,
    section_id: str,
    field_id: str,
) -> bool:
    return field_key(section_id, field_id) in state.skipped_field_ids


def question_field_resolved(
    state: StudioFormState,
    section_id: str,
    field: FieldDef,
) -> bool:
    key = field_key(section_id, field.id)
    if key in state.skipped_field_ids:
        return True
    return not value_is_empty(state.sections[section_id].fields[field.id])


def value_to_text(value: FieldValue, field: FieldDef) -> str:
    if value_is_empty(value):
        return ''
    if value.type == 'text':
        return value.value
    if value.type == 'choice-single':
        option = next(
            (item for item in (field.options or []) if item.value == value.value),
            None,
        )
        return option.label if option else str(value.value)
    if value.type == 'choice-multi':
        labels = []
        for item in value.value:
            option = next(
                (candidate for candidate in (field.options or []) if candidate.value == item),
                None,
            )
            labels.append(option.label if option else item)
        return '、'.join(labels)
    if value.type == 'dimension':
        parts = [f'{key}{number}' for key, number in value.value.items() if number.strip()]
        return f'{"×".join(parts)}{field.unit or ""}'
    if value.type == 'image':
        return f'{len(value.value)}张图'
    if value.type == 'table':
        return f'{len(value.value)}行'
    return ''


def visible_fields(state: StudioFormState) -> list[tuple[str, FieldDef]]:
    result: list[tuple[str, FieldDef]] = []
    for section_id in SECTION_ORDER:
        definition = SECTION_BY_ID[section_id]
        section = state.sections[section_id]
        if (
            (section.status == 'skipped' and definition.skippable)
            or not is_section_visible(state, definition)
        ):
            continue
        for field in definition.fields:
            if is_field_visible(field, section):
                result.append((section_id, field))
    return result


def question_fields(state: StudioFormState) -> list[tuple[str, FieldDef]]:
    if state.completed:
        return []
    fields = visible_fields(state)
    if state.mode == 'full':
        return [item for item in fields if item[1].ask_in_full]
    return [
        (section_id, field)
        for section_id, field in fields
        if field_key(section_id, field.id) in state.required_field_ids
    ]


def unfilled_question_fields(state: StudioFormState) -> list[tuple[str, FieldDef]]:
    fields = question_fields(state)
    result = []
    for section_id, field in fields:
        if not question_field_resolved(state, section_id, field):
            result.append((section_id, field))

    field_indexes = {
        field_key(section_id, field.id): index
        for index, (section_id, field) in enumerate(fields)
    }

    def trigger_reached(trigger_key: str) -> bool:
        trigger_index = field_indexes.get(trigger_key)
        if trigger_index is None:
            return False
        return not any(
            field_indexes[field_key(section_id, field.id)] < trigger_index
            for section_id, field in result
        )

    priority_keys: list[str] = []
    has_room = state.sections['status'].fields['has_room'].value
    if trigger_reached('status.has_room'):
        if has_room == 'yes':
            priority_keys.append('status.room_photo')
        elif has_room == 'no':
            priority_keys.extend([
                'product.style_ref',
                'product.style_ref_image',
            ])

    has_existing = state.sections['budget'].fields['has_existing'].value
    if trigger_reached('budget.has_existing') and has_existing == 'yes':
        priority_keys.extend([
            'equipment.inventory',
            'equipment.equipment_photo',
        ])

    priority = [
        item
        for key in priority_keys
        for item in result
        if field_key(item[0], item[1].id) == key
    ]
    priority_set = {
        field_key(section_id, field.id)
        for section_id, field in priority
    }
    return [
        *priority,
        *(
            item
            for item in result
            if field_key(item[0], item[1].id) not in priority_set
        ),
    ]


def next_question_field(state: StudioFormState) -> tuple[str, FieldDef] | None:
    fields = unfilled_question_fields(state)
    return fields[0] if fields else None


def next_question_batch(
    state: StudioFormState,
    n: int = 2,
) -> list[tuple[str, FieldDef]]:
    return unfilled_question_fields(state)[:n]


def unfilled_required_fields(state: StudioFormState) -> list[tuple[str, FieldDef]]:
    result = []
    for section_id in SECTION_ORDER:
        definition = SECTION_BY_ID[section_id]
        section = state.sections[section_id]
        if not is_section_visible(state, definition):
            continue
        for field in definition.fields:
            if not is_field_required(state, section_id, field):
                continue
            if not is_field_visible(field, section):
                continue
            if is_field_skipped(state, section_id, field.id):
                continue
            if value_is_empty(section.fields[field.id]):
                result.append((section_id, field))
    return result


def next_unfilled_field(state: StudioFormState) -> tuple[str, FieldDef] | None:
    """兼容旧调用：返回下一个未填核心必填字段。"""
    fields = unfilled_required_fields(state)
    return fields[0] if fields else None


def next_field_batch(
    state: StudioFormState,
    n: int = 3,
) -> list[tuple[str, FieldDef]]:
    return unfilled_required_fields(state)[:n]


def filled_required_count(
    state: StudioFormState,
    section_id: str,
) -> tuple[int, int]:
    definition = SECTION_BY_ID[section_id]
    section = state.sections[section_id]
    if not is_section_visible(state, definition):
        return 0, 0

    filled = 0
    total = 0
    for field in definition.fields:
        if not is_field_required(state, section_id, field):
            continue
        if not is_field_visible(field, section):
            continue
        total += 1
        if (
            is_field_skipped(state, section_id, field.id)
            or not value_is_empty(section.fields[field.id])
        ):
            filled += 1
    return filled, total


def overall_progress(state: StudioFormState) -> tuple[int, int]:
    filled = 0
    total = 0
    for section_id in SECTION_ORDER:
        section_filled, section_total = filled_required_count(state, section_id)
        filled += section_filled
        total += section_total
    return filled, total


def overall_question_progress(state: StudioFormState) -> tuple[int, int]:
    fields = question_fields(state)
    resolved = 0
    for section_id, field in fields:
        if question_field_resolved(state, section_id, field):
            resolved += 1
    return resolved, len(fields)


def required_complete(state: StudioFormState) -> bool:
    return not unfilled_required_fields(state)


def form_complete(state: StudioFormState) -> bool:
    """问卷是否已逐题回答或合法跳过。"""
    return next_question_field(state) is None


def current_section_for_agent(state: StudioFormState) -> str:
    next_field = next_question_field(state)
    return next_field[0] if next_field else SECTION_ORDER[-1]


def sync_current_question(state: StudioFormState) -> None:
    next_field = next_question_field(state)
    if next_field is None:
        state.current_section_id = SECTION_ORDER[-1]
        state.current_field_id = ''
        return
    state.current_section_id = next_field[0]
    state.current_field_id = next_field[1].id


def skip_field(
    state: StudioFormState,
    section_id: str,
    field_id: str,
) -> tuple[bool, str]:
    definition = SECTION_BY_ID.get(section_id)
    if definition is None:
        return False, f'章节不存在: {section_id}'
    field = next((item for item in definition.fields if item.id == field_id), None)
    if field is None:
        return False, f'字段不存在: {section_id}.{field_id}'
    if not field.skippable:
        return False, f'“{field.label}”是必答题，不能跳过'
    current = next_question_field(state)
    if current is None or (current[0], current[1].id) != (section_id, field_id):
        return False, '只能跳过当前正在询问的问题'
    if not value_is_empty(state.sections[section_id].fields[field_id]):
        return False, f'“{field.label}”已经回答，无需跳过'

    key = field_key(section_id, field_id)
    if key not in state.skipped_field_ids:
        state.skipped_field_ids.append(key)
    sync_current_question(state)
    recompute_section_status(state)
    return True, f'已跳过“{field.label}”'


def skip_section(
    state: StudioFormState,
    section_id: str,
) -> tuple[bool, str]:
    definition = SECTION_BY_ID.get(section_id)
    if definition is None:
        return False, f'章节不存在: {section_id}'
    if not definition.skippable:
        return False, f'“{definition.title}”是核心模块，不能跳过'
    current = next_question_field(state)
    if current is None or current[0] != section_id:
        return False, '只能跳过当前正在询问的模块'

    section = state.sections[section_id]
    had_value = any(not value_is_empty(value) for value in section.fields.values())
    for field in definition.fields:
        if not is_field_visible(field, section):
            continue
        if value_is_empty(section.fields[field.id]):
            key = field_key(section_id, field.id)
            if key not in state.skipped_field_ids:
                state.skipped_field_ids.append(key)

    section.status = 'complete' if had_value else 'skipped'
    sync_current_question(state)
    recompute_section_status(state)
    return True, f'已跳过“{definition.title}”'


def section_progress(state: StudioFormState) -> list[dict]:
    result = []
    all_questions = question_fields(state)
    for section_id in SECTION_ORDER:
        definition = SECTION_BY_ID[section_id]
        section = state.sections[section_id]
        filled, total = filled_required_count(state, section_id)
        questions = [item for sid, item in all_questions if sid == section_id]
        resolved = sum(
            1
            for field in questions
            if question_field_resolved(state, section_id, field)
        )
        result.append({
            'section_id': section_id,
            'title': definition.title,
            'status': section.status,
            'filled': filled,
            'total': total,
            'resolved': resolved,
            'questions': len(questions),
            'complete': resolved >= len(questions) if questions else True,
        })
    return result


def recompute_section_status(state: StudioFormState) -> None:
    all_questions = question_fields(state)
    for section_id in SECTION_ORDER:
        definition = SECTION_BY_ID[section_id]
        section = state.sections[section_id]
        if section.status == 'skipped' and definition.skippable:
            continue
        if not is_section_visible(state, definition):
            section.status = 'pending'
            continue

        fields = [field for sid, field in all_questions if sid == section_id]
        resolved = [
            field
            for field in fields
            if question_field_resolved(state, section_id, field)
        ]
        if fields and len(resolved) == len(fields):
            section.status = 'complete'
        elif resolved or section_id == state.current_section_id:
            section.status = 'active'
        else:
            section.status = 'pending'
