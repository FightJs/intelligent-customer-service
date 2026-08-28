"""问卷状态机：顺序、条件、完整性与跳过权限。"""
from agent.flow import (
    form_complete,
    is_field_visible,
    is_section_visible,
    next_question_field,
    next_unfilled_field,
    overall_progress,
    question_field_resolved,
    skip_field,
    skip_section,
    value_is_empty,
    visible_fields,
)
from survey.schema_def import SECTION_BY_ID
from survey.state import create_initial_state


def _advance_to_industry(state):
    customer = state.sections['customer'].fields
    customer['brand'].value = '云裳'
    customer['identity'].value = ['owner']
    customer['contact'].value = '张女士'
    customer['phone'].value = '13800000000'
    customer['source'].value = 'douyin'
    state.skipped_field_ids.extend(['customer.wechat', 'customer.city'])


def _advance_to_status(state):
    _advance_to_industry(state)
    state.skipped_field_ids.extend(['industry.category', 'industry.subcategory'])
    industry = state.sections['industry'].fields
    for field_id in ('price_band', 'positioning', 'target_age', 'target_gender', 'live_type'):
        industry[field_id].value = 'answered'


def _advance_to_question(state, section_id, field_id):
    """按真实问卷顺序回答或跳过，直到目标题成为当前题。"""
    for _ in range(100):
        current = next_question_field(state)
        assert current is not None
        current_section_id, field = current
        if (current_section_id, field.id) == (section_id, field_id):
            return
        if field.skippable:
            ok, message = skip_field(state, current_section_id, field.id)
            assert ok, message
            continue
        value = state.sections[current_section_id].fields[field.id]
        if value.type == 'text':
            value.value = '已回答'
        elif value.type == 'choice-single':
            value.value = field.options[0].value
        elif value.type == 'choice-multi':
            value.value = [field.options[0].value]
        elif value.type == 'dimension':
            value.value = {dimension: '1' for dimension in (field.dims or [])}
        else:
            raise AssertionError(f'测试辅助方法无法回答 {current_section_id}.{field.id}')
    raise AssertionError(f'未能推进到 {section_id}.{field_id}')


def test_empty_state_starts_from_brand():
    state = create_initial_state()
    assert next_unfilled_field(state)[1].id == 'brand'
    assert next_question_field(state)[1].id == 'brand'


def test_progress_advances_in_template_order():
    state = create_initial_state()
    state.sections['customer'].fields['brand'].value = '云裳'
    assert next_question_field(state)[1].id == 'identity'
    state.sections['customer'].fields['identity'].value = ['owner', 'host']
    assert next_question_field(state)[1].id == 'contact'


def test_conditional_status_fields_preserve_no_answer():
    state = create_initial_state()
    state.sections['status'].fields['has_room'].value = 'no'
    status_fields = [field.id for sid, field in visible_fields(state) if sid == 'status']
    assert status_fields == ['has_room']
    assert state.sections['status'].fields['has_room'].value == 'no'


def test_conditional_status_fields_shown_for_existing_room():
    state = create_initial_state()
    state.sections['status'].fields['has_room'].value = 'yes'
    status_fields = [field.id for sid, field in visible_fields(state) if sid == 'status']
    assert status_fields == [
        'has_room', 'room_photo', 'duration', 'viewers', 'gmv',
        'satisfaction', 'pain_points',
    ]


def test_existing_room_immediately_asks_for_room_or_comparison_image():
    state = create_initial_state()
    _advance_to_question(state, 'status', 'has_room')
    state.sections['status'].fields['has_room'].value = 'yes'

    current = next_question_field(state)

    assert (current[0], current[1].id) == ('status', 'room_photo')


def test_no_room_immediately_asks_for_favorite_style_reference():
    state = create_initial_state()
    _advance_to_question(state, 'status', 'has_room')
    state.sections['status'].fields['has_room'].value = 'no'

    current = next_question_field(state)

    assert (current[0], current[1].id) == ('product', 'style_ref')
    state.sections['product'].fields['style_ref'].value = '轻奢珠宝直播间'
    assert next_question_field(state)[1].id == 'style_ref_image'


def test_proactively_answered_room_status_does_not_skip_earlier_questions():
    state = create_initial_state()
    state.sections['status'].fields['has_room'].value = 'no'

    current = next_question_field(state)

    assert (current[0], current[1].id) == ('customer', 'brand')


def test_window_position_condition():
    state = create_initial_state()
    section = state.sections['venue']
    field = next(field for field in SECTION_BY_ID['venue'].fields if field.id == 'window_pos')
    assert not is_field_visible(field, section)
    section.fields['window'].value = 'none'
    assert not is_field_visible(field, section)
    section.fields['window'].value = 'coverable'
    assert is_field_visible(field, section)


def test_equipment_module_visibility_does_not_break_question_order():
    state = create_initial_state()
    equipment = SECTION_BY_ID['equipment']
    assert not is_section_visible(state, equipment)

    state.sections['budget'].fields['has_existing'].value = 'yes'
    assert is_section_visible(state, equipment)
    assert next_question_field(state)[1].id == 'brand'
    assert overall_progress(state) == (1, 24)

    state.sections['budget'].fields['has_existing'].value = 'no'
    assert not is_section_visible(state, equipment)


def test_existing_equipment_immediately_asks_inventory_then_photo():
    state = create_initial_state()
    _advance_to_question(state, 'budget', 'has_existing')
    state.sections['budget'].fields['has_existing'].value = 'yes'

    current = next_question_field(state)
    assert (current[0], current[1].id) == ('equipment', 'inventory')

    state.sections['equipment'].fields['inventory'].value = [{
        'type': '相机', 'model': 'Sony A7M4', 'qty': '1',
    }]
    current = next_question_field(state)
    assert (current[0], current[1].id) == ('equipment', 'equipment_photo')


def test_no_existing_equipment_continues_normal_question_order():
    state = create_initial_state()
    _advance_to_question(state, 'budget', 'has_existing')
    state.sections['budget'].fields['has_existing'].value = 'no'

    current = next_question_field(state)

    assert (current[0], current[1].id) == ('product', 'main')


def test_progress_counts_match_final_template():
    assert overall_progress(create_initial_state()) == (0, 24)
    assert overall_progress(create_initial_state(mode='quick')) == (0, 13)


def test_identity_follows_brand_in_full_and_quick_modes():
    for mode in ('full', 'quick'):
        state = create_initial_state(mode=mode)
        state.sections['customer'].fields['brand'].value = '云裳'

        current = next_question_field(state)

        assert (current[0], current[1].id) == ('customer', 'identity')


def test_only_explicit_fields_and_modules_can_skip():
    state = create_initial_state()
    ok, message = skip_field(state, 'industry', 'category')
    assert not ok
    assert '当前' in message

    _advance_to_industry(state)
    ok, _ = skip_field(state, 'industry', 'category')
    assert ok
    assert 'industry.category' in state.skipped_field_ids

    ok, _ = skip_field(state, 'industry', 'subcategory')
    assert ok

    ok, message = skip_field(state, 'customer', 'brand')
    assert not ok
    assert '不能跳过' in message

    industry = state.sections['industry'].fields
    for field_id in ('price_band', 'positioning', 'target_age', 'target_gender', 'live_type'):
        industry[field_id].value = 'answered'
    ok, _ = skip_section(state, 'status')
    assert ok
    assert state.sections['status'].status == 'skipped'

    ok, message = skip_section(state, 'customer')
    assert not ok
    assert '核心模块' in message


def test_malicious_core_skipped_status_cannot_complete_form():
    state = create_initial_state()
    state.sections['customer'].status = 'skipped'
    assert not form_complete(state)
    assert any(sid == 'customer' for sid, _ in visible_fields(state))


def test_skipped_optional_section_has_no_visible_questions():
    state = create_initial_state()
    _advance_to_status(state)
    ok, _ = skip_section(state, 'status')
    assert ok
    assert not [field for sid, field in visible_fields(state) if sid == 'status']


def test_completed_state_has_no_next_question():
    state = create_initial_state()
    state.completed = True
    assert next_question_field(state) is None
    assert form_complete(state)


def test_value_is_empty_for_supported_types():
    from survey.models import DimensionValue, MultiChoiceValue, SingleChoiceValue, TextValue

    assert value_is_empty(TextValue(value=''))
    assert not value_is_empty(TextValue(value='x'))
    assert value_is_empty(SingleChoiceValue(value=None))
    assert not value_is_empty(SingleChoiceValue(value='yes'))
    assert value_is_empty(MultiChoiceValue(value=[]))
    assert not value_is_empty(MultiChoiceValue(value=['a']))
    assert value_is_empty(DimensionValue(value={'宽': '', '深': ''}))
    assert not value_is_empty(DimensionValue(value={'宽': '4', '深': ''}))


def test_text_and_image_questions_are_resolved_independently():
    state = create_initial_state()
    product = state.sections['product']
    style_text = next(
        field for field in SECTION_BY_ID['product'].fields
        if field.id == 'style_ref'
    )
    style_image = next(
        field for field in SECTION_BY_ID['product'].fields
        if field.id == 'style_ref_image'
    )

    product.fields['style_ref_image'].value = ['session/reference.png']

    assert not question_field_resolved(state, 'product', style_text)
    assert question_field_resolved(state, 'product', style_image)
