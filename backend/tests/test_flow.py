"""flow.py 状态机测试。"""
from survey.state import create_initial_state
from agent.flow import (
    next_unfilled_field, form_complete, overall_progress,
    visible_fields, is_field_visible, value_is_empty, skip_section,
)


def test_empty_state_first_field():
    state = create_initial_state()
    nxt = next_unfilled_field(state)
    assert nxt is not None
    sec_id, field = nxt
    assert sec_id == 'customer'
    assert field.id == 'brand'


def test_progress_advances_after_fill():
    state = create_initial_state()
    state.sections['customer'].fields['brand'].value = '云裳'
    nxt = next_unfilled_field(state)
    assert nxt is not None
    assert nxt[1].id == 'contact'  # brand 后是 contact


def test_conditional_fields_hidden_when_no_room():
    state = create_initial_state()
    state.sections['status'].fields['has_room'].value = 'no'
    visible = visible_fields(state)
    status_fields = [f.id for s, f in visible if s == 'status']
    assert status_fields == ['has_room']  # 只有 has_room 可见


def test_conditional_fields_shown_when_has_room():
    state = create_initial_state()
    state.sections['status'].fields['has_room'].value = 'yes'
    visible = visible_fields(state)
    status_fields = [f.id for s, f in visible if s == 'status']
    assert 'account' in status_fields
    assert 'pain_points' in status_fields
    assert len(status_fields) == 8


def test_window_pos_conditional():
    """window_pos 仅在 window != none 时可见。"""
    state = create_initial_state()
    # window 未填 → window_pos 不可见
    sec = state.sections['venue']
    field = next(f for f in __import__('survey.schema_def', fromlist=['SECTIONS']).SECTION_BY_ID['venue'].fields if f.id == 'window_pos')
    assert not is_field_visible(field, sec)
    # window=none → window_pos 不可见
    sec.fields['window'].value = 'none'
    assert not is_field_visible(field, sec)
    # window=coverable → window_pos 可见
    sec.fields['window'].value = 'coverable'
    assert is_field_visible(field, sec)


def test_overall_progress_counts():
    f, t = overall_progress(create_initial_state())
    assert t == 29  # 全局 29 必填
    assert f == 0


def test_form_complete_false_initially():
    assert not form_complete(create_initial_state())


def test_skip_section():
    state = create_initial_state()
    skip_section(state, 'status')
    assert state.sections['status'].status == 'skipped'
    visible = visible_fields(state)
    status_fields = [f.id for s, f in visible if s == 'status']
    assert status_fields == []  # 跳过的章节无可见字段


def test_value_is_empty():
    from survey.models import TextValue, SingleChoiceValue, MultiChoiceValue, DimensionValue
    assert value_is_empty(TextValue(value=''))
    assert not value_is_empty(TextValue(value='x'))
    assert value_is_empty(SingleChoiceValue(value=None))
    assert not value_is_empty(SingleChoiceValue(value='yes'))
    assert value_is_empty(MultiChoiceValue(value=[]))
    assert not value_is_empty(MultiChoiceValue(value=['a']))
    assert value_is_empty(DimensionValue(value={'宽': '', '深': ''}))
    assert not value_is_empty(DimensionValue(value={'宽': '4', '深': ''}))


def test_existing_equipment_requires_inventory_immediately():
    """用户确认有设备后，设备明细立即成为下一个必填字段。"""
    state = create_initial_state()

    state.sections['budget'].fields[
        'has_existing'
    ].value = 'yes'

    nxt = next_unfilled_field(state)

    assert nxt is not None
    assert nxt[0] == 'equipment'
    assert nxt[1].id == 'inventory'

    _, total = overall_progress(state)
    assert total == 30


def test_no_existing_equipment_does_not_require_inventory():
    """用户确认没有设备时，不要求填写设备明细。"""
    state = create_initial_state()

    state.sections['budget'].fields[
        'has_existing'
    ].value = 'no'

    nxt = next_unfilled_field(state)

    assert nxt is not None
    assert nxt[0] == 'customer'
    assert nxt[1].id == 'brand'

    _, total = overall_progress(state)
    assert total == 29


def test_inventory_completed_resumes_normal_flow():
    """设备明细填写后，恢复原来的字段采集顺序。"""
    state = create_initial_state()

    state.sections['budget'].fields[
        'has_existing'
    ].value = 'yes'

    state.sections['equipment'].fields[
        'inventory'
    ].value = [{
        'type': '相机',
        'model': 'Sony A7M4',
        'qty': '1',
        'note': '',
    }]

    nxt = next_unfilled_field(state)

    assert nxt is not None
    assert nxt[0] == 'customer'
    assert nxt[1].id == 'brand'
