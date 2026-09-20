"""微意图模块测试。"""
from unittest.mock import patch

from agent.micro_intent import (
    apply_deterministic_current_answer,
    apply_deterministic_price_range,
    apply_deterministic_reference_link,
    is_skip_intent,
    is_unknown_equipment_inventory,
    is_user_off_topic,
    looks_like_price_answer,
    match_choice_multi,
    match_choice_single,
    parse_yes_no,
    price_band_from_text,
    skip_unknown_equipment_inventory,
)
from survey.schema_def import SECTION_BY_ID
from survey.state import create_initial_state


def _field(section_id: str, field_id: str):
    return next(
        item for item in SECTION_BY_ID[section_id].fields
        if item.id == field_id
    )


def test_skip_and_yes_no_parsing():
    assert is_skip_intent('我说不需要补充了')
    assert is_skip_intent('暂时没有。')
    assert not is_skip_intent('没有直播间')
    assert parse_yes_no('有的') == 'yes'
    assert parse_yes_no('不需要') == 'no'
    assert parse_yes_no('我们主要做美妆') is None


def test_price_helpers():
    assert looks_like_price_answer('500～1000元')
    assert not looks_like_price_answer('价格还没想好')
    assert price_band_from_text('商品价格是500～1000元') == 'high'
    assert price_band_from_text('客单价80元') == 'low'


def test_choice_matching():
    has_room = _field('status', 'has_room')
    assert match_choice_single(has_room, '有') == 'yes'
    assert match_choice_single(has_room, '没有') == 'no'

    pain = _field('status', 'pain_points')
    matched = match_choice_multi(pain, '灯光不够亮，画面发灰')
    assert matched is None or isinstance(matched, list)
    assert match_choice_multi(pain, '想要优化') == ['想要优化']


def test_unknown_equipment_inventory():
    assert is_unknown_equipment_inventory('不知道具体型号。')
    assert not is_unknown_equipment_inventory('不知道型号，不过有一台索尼相机')


def test_natural_yes_answer_advances_yes_no_field():
    state = create_initial_state()
    field = _field('status', 'has_room')
    with patch('agent.micro_intent.flow.next_question_field', return_value=('status', field)):
        events = apply_deterministic_current_answer(state, '有')
    assert state.sections['status'].fields['has_room'].value == 'yes'
    assert [(event.kind, event.field_id) for event in events] == [('fill', 'has_room')]


def test_skip_optional_field():
    state = create_initial_state()
    field = _field('goal', 'other')
    with patch('agent.micro_intent.flow.next_question_field', return_value=('goal', field)):
        events = apply_deterministic_current_answer(state, '我说不需要补充了')
    assert 'goal.other' in state.skipped_field_ids
    assert events[0].kind == 'skip'


def test_reference_link_saved():
    state = create_initial_state()
    field = _field('benchmark', 'account_name')
    with patch('agent.micro_intent.flow.next_question_field', return_value=('benchmark', field)):
        events = apply_deterministic_reference_link(
            state,
            '参考这个直播间：https://example.com/live/123',
        )
    assert state.sections['benchmark'].fields['reference_link'].value == (
        'https://example.com/live/123'
    )
    assert events[0].field_id == 'reference_link'


def test_unknown_equipment_skips_to_photo():
    state = create_initial_state()
    inventory = _field('equipment', 'inventory')
    with patch('agent.micro_intent.flow.next_question_field', return_value=('equipment', inventory)):
        events = skip_unknown_equipment_inventory(state, '不知道具体型号。')
    assert events[0].kind == 'skip'
    assert 'equipment.inventory' in state.skipped_field_ids


def test_price_range_applies_when_current_is_price_band():
    state = create_initial_state()
    field = _field('industry', 'price_band')
    with patch('agent.micro_intent.flow.next_question_field', return_value=('industry', field)):
        events = apply_deterministic_price_range(state, '商品价格是500～1000元')
    assert state.sections['industry'].fields['price_band'].value == 'high'
    assert {event.field_id for event in events} == {'price_band', 'price_range_raw'}


def test_off_topic_advice_question_is_detected():
    state = create_initial_state()
    with patch(
        'agent.micro_intent.flow.next_question_field',
        return_value=('customer', _field('customer', 'brand')),
    ):
        assert is_user_off_topic('你们一般用什么灯比较合适？', state)
        assert is_user_off_topic('帮我推荐一套设备方案', state)
        assert is_user_off_topic('怎么收费的？', state)


def test_off_topic_does_not_flag_real_answers():
    state = create_initial_state()
    with patch(
        'agent.micro_intent.flow.next_question_field',
        return_value=('customer', _field('customer', 'brand')),
    ):
        assert not is_user_off_topic('我们品牌叫云裳', state)
        assert not is_user_off_topic('品牌是云裳，主要做女装', state)


def test_off_topic_empty_when_survey_done():
    state = create_initial_state()
    with patch('agent.micro_intent.flow.next_question_field', return_value=None):
        assert not is_user_off_topic('你们一般用什么灯？', state)
