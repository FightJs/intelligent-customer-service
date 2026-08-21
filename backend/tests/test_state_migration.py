"""旧会话恢复到最终问卷结构的回归测试。"""
from survey.schema_def import SECTION_ORDER
from survey.state import create_initial_state, from_dict, to_dict


def test_old_state_is_hydrated_without_losing_compatible_values():
    payload = to_dict(create_initial_state())
    payload['sections']['customer']['fields']['brand']['value'] = '云裳'
    payload['sections']['customer']['fields']['date'] = {
        'type': 'text',
        'value': '2025-01-01',
    }
    payload['sections'].pop('benchmark')
    payload['sections']['notes'] = {
        'id': 'notes',
        'status': 'complete',
        'fields': {
            'internal': {'type': 'text', 'value': '旧客服备注'},
        },
    }
    payload['sections']['customer']['status'] = 'skipped'
    payload['sections']['product']['fields'].update({
        'material': {'type': 'text', 'value': '丝绸光泽'},
        'theme_color': {'type': 'text', 'value': '黛青色'},
        'logo': {'type': 'image', 'value': ['legacy/logo.png']},
        'sample_photo': {'type': 'image', 'value': ['legacy/sample.png']},
    })
    payload['sections']['host']['fields'].update({
        'height': {
            'type': 'dimension',
            'value': {'女主播': '165', '男主播': '178'},
        },
        'body': {'type': 'choice-single', 'value': 'standard'},
    })
    payload['sections']['goal']['fields']['expectation'] = {
        'type': 'text',
        'value': '提升停留时长',
    }
    payload['currentSectionId'] = 'notes'
    payload['currentFieldId'] = 'internal'
    payload['skippedFieldIds'] = ['customer.brand', 'status.has_room']
    payload.pop('equipmentImageInvited', None)
    payload.pop('imageInvitedFieldIds', None)

    state = from_dict(payload)

    assert list(state.sections) == SECTION_ORDER
    assert state.sections['customer'].fields['brand'].value == '云裳'
    assert 'date' not in state.sections['customer'].fields
    assert 'notes' not in state.sections
    assert 'benchmark' in state.sections
    assert 'equipment_photo' in state.sections['equipment'].fields
    assert state.sections['customer'].status == 'pending'
    assert state.current_section_id == 'customer'
    assert state.current_field_id == 'brand'
    assert state.skipped_field_ids == ['status.has_room']
    assert state.sections['product'].fields['brand_assets'].value == [
        'legacy/logo.png',
        'legacy/sample.png',
    ]
    style_ref = state.sections['product'].fields['style_ref'].value
    assert '丝绸光泽' in style_ref
    assert '黛青色' in style_ref
    profile = state.sections['host'].fields['profile'].value
    assert '女主播165cm' in profile
    assert '男主播178cm' in profile
    assert '标准' in profile
    assert '提升停留时长' in state.sections['goal'].fields['other'].value
