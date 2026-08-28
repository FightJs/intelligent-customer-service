"""最终确认版调研模板的结构快照。"""
from survey.schema_def import (
    QUICK_REQUIRED_FIELD_IDS,
    SECTION_BY_ID,
    SECTION_ORDER,
    SECTIONS,
)


def test_final_questionnaire_section_order_and_removed_internal_section():
    assert SECTION_ORDER == [
        'customer', 'industry', 'status', 'venue', 'budget',
        'product', 'benchmark', 'host', 'equipment', 'goal',
    ]
    assert 'notes' not in SECTION_ORDER


def test_final_template_removed_obsolete_fields_and_added_benchmark():
    assert 'date' not in {field.id for field in SECTION_BY_ID['customer'].fields}
    assert 'account' not in {field.id for field in SECTION_BY_ID['status'].fields}
    assert not {'shape', 'wall_color', 'floor', 'power'} & {
        field.id for field in SECTION_BY_ID['venue'].fields
    }


def test_customer_identity_is_required_multi_choice_in_both_modes():
    identity = next(
        field
        for field in SECTION_BY_ID['customer'].fields
        if field.id == 'identity'
    )

    assert identity.type == 'choice-multi'
    assert identity.required
    assert not identity.skippable
    assert 'customer.identity' in QUICK_REQUIRED_FIELD_IDS
    assert [(option.value, option.label) for option in identity.options] == [
        ('owner', '主理人（老板）'),
        ('host', '主播'),
        ('operator', '运营'),
        ('other', '其他'),
    ]
    assert not {'skin', 'hair', 'photo', 'height'} & {
        field.id for field in SECTION_BY_ID['host'].fields
    }
    assert {field.id for field in SECTION_BY_ID['benchmark'].fields} == {
        'has_benchmark', 'account_name', 'platform', 'likes',
        'screenshot', 'reference_link', 'reference_mode', 'exact_copy',
    }


def test_skip_permissions_and_equipment_photo_match_confirmed_rules():
    industry = {field.id: field for field in SECTION_BY_ID['industry'].fields}
    assert industry['category'].skippable
    assert industry['subcategory'].skippable
    assert not industry['price_band'].skippable
    assert not SECTION_BY_ID['customer'].skippable
    assert SECTION_BY_ID['status'].skippable
    assert SECTION_BY_ID['benchmark'].skippable
    assert SECTION_BY_ID['host'].skippable
    assert SECTION_BY_ID['equipment'].skippable

    equipment = {field.id: field for field in SECTION_BY_ID['equipment'].fields}
    assert equipment['equipment_photo'].type == 'image'
    assert [column.id for column in equipment['inventory'].columns] == [
        'type', 'model', 'qty',
    ]


def test_every_active_question_has_approved_question_copy():
    assert all(
        field.question.strip()
        for section in SECTIONS
        for field in section.fields
        if field.ask_in_full
    )


def test_every_active_question_has_user_visible_filling_guidance():
    active_fields = [
        field
        for section in SECTIONS
        for field in section.fields
        if field.ask_in_full
    ]

    assert all(field.help_text.strip() for field in active_fields)
    assert all(
        field.help_text.startswith(('填写说明：', '填写示例：', '填写指引：'))
        for field in active_fields
    )
