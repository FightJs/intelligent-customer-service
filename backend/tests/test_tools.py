"""tools.py 执行函数测试。"""
import pytest
from survey.state import create_initial_state
from agent.tools import execute_tool, ToolEvent, TOOL_DEFS, apply_updates
from agent.flow import is_field_visible


def test_fill_fields_updates_state():
    state = create_initial_state()
    result = execute_tool('fill_fields', {
        'updates': [
            {'section_id': 'customer', 'field_id': 'brand', 'value': '云裳'},
            {'section_id': 'customer', 'field_id': 'phone', 'value': '138'},
        ]
    }, state)
    assert state.sections['customer'].fields['brand'].value == '云裳'
    assert state.sections['customer'].fields['phone'].value == '138'
    assert '云裳' in result

def test_fill_fields_handles_prefixed_field_id():
    state = create_initial_state()
    execute_tool('fill_fields', {
        'updates': [{'section_id': 'customer', 'field_id': 'customer.brand', 'value': '云裳'}]
    }, state)
    assert state.sections['customer'].fields['brand'].value == '云裳'

def test_fill_fields_choice_single():
    state = create_initial_state()
    execute_tool('fill_fields', {
        'updates': [{'section_id': 'industry', 'field_id': 'category', 'value': 'women'}]
    }, state)
    assert state.sections['industry'].fields['category'].value == 'women'

def test_skip_section():
    state = create_initial_state()
    execute_tool('skip_section', {'section_id': 'status', 'reason': '没有直播间'}, state)
    assert state.sections['status'].status == 'skipped'

def test_get_progress_returns_next_field():
    state = create_initial_state()
    result = execute_tool('get_progress', {}, state)
    assert 'brand' in result
    assert 'customer' in result

def test_set_current_section():
    state = create_initial_state()
    execute_tool('set_current_section', {'section_id': 'venue'}, state)
    assert state.current_section_id == 'venue'


def test_unknown_tool_returns_error():
    state = create_initial_state()
    result = execute_tool('nonexistent', {}, state)
    assert 'error' in result.lower() or 'unknown' in result.lower()

def test_tool_defs_has_four_tools():
    names = [
        tool['name']
        for tool in TOOL_DEFS
    ]

    assert names == [
        'fill_fields',
        'skip_section',
        'get_progress',
        'set_current_section',
    ]


def test_fill_fields_returns_failure_details():
    """非法 section_id/field_id 时返回值应含失败明细（不再静默吞掉）。"""
    state = create_initial_state()
    result = execute_tool('fill_fields', {
        'updates': [
            {'section_id': 'customer', 'field_id': 'brand', 'value': '云裳'},
            {'section_id': 'nonexistent', 'field_id': 'x', 'value': 'y'},
            {'section_id': 'customer', 'field_id': 'nonfield', 'value': 'z'},
        ]
    }, state)
    # 成功的填了
    assert state.sections['customer'].fields['brand'].value == '云裳'
    # 失败的应有明细
    assert '失败' in result
    assert 'nonexistent' in result or '不存在' in result


def test_choice_validation_rejects_invalid_value():
    """choice 字段 value 不在 options 内时拒绝（返回失败，不写入脏数据）。"""
    state = create_initial_state()
    result = execute_tool('fill_fields', {
        'updates': [{'section_id': 'industry', 'field_id': 'category', 'value': 'invalid_value'}]
    }, state)
    # 字段未被污染
    assert state.sections['industry'].fields['category'].value is None
    # 失败明细提到非法值
    assert '失败' in result or 'options' in result


def test_choice_label_auto_mapped_to_value():
    """传中文 label（如"女装"）应自动反查为 value（women）。"""
    state = create_initial_state()
    execute_tool('fill_fields', {
        'updates': [{'section_id': 'industry', 'field_id': 'category', 'value': '女装'}]
    }, state)
    assert state.sections['industry'].fields['category'].value == 'women'


def test_apply_updates_helper_returns_counts():
    """apply_updates 公开 helper：批量 apply 并返回成功/失败统计。"""
    state = create_initial_state()
    count, failures = apply_updates(state, [
        {'section_id': 'customer', 'field_id': 'brand', 'value': '云裳'},
        {'section_id': 'bad', 'field_id': 'x', 'value': 'y'},
    ])
    assert count == 1
    assert len(failures) == 1
    assert state.sections['customer'].fields['brand'].value == '云裳'


def test_fill_fields_tool_describes_table_structure():
    fill_fields = next(
        tool for tool in TOOL_DEFS
        if tool['name'] == 'fill_fields'
    )

    assert 'table' in fill_fields['description']
    assert 'model' in fill_fields['description']


def test_fill_fields_table_writes_structured_rows():
    state = create_initial_state()

    result = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'equipment',
            'field_id': 'inventory',
            'value': [{
                'type': '相机',
                'model': 'Sony A7M4',
                'qty': 1,
                'note': '',
            }],
        }],
    }, state)

    assert state.sections['equipment'].fields['inventory'].value == [{
        'type': '相机',
        'model': 'Sony A7M4',
        'qty': '1',
        'note': '',
    }]
    assert '失败' not in result


def test_fill_fields_table_rejects_non_list():
    state = create_initial_state()

    result = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'equipment',
            'field_id': 'inventory',
            'value': 'Sony A7M4',
        }],
    }, state)

    assert state.sections['equipment'].fields['inventory'].value == []
    assert '失败' in result
    assert 'list' in result


def test_fill_fields_table_rejects_unknown_columns():
    state = create_initial_state()

    result = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'equipment',
            'field_id': 'inventory',
            'value': [{
                'brand': 'Sony',
            }],
        }],
    }, state)

    assert state.sections['equipment'].fields['inventory'].value == []
    assert '失败' in result
    assert '未知列' in result


def test_text_conflict_requires_confirmation():
    """text 已有不同值时不能静默覆盖。"""
    state = create_initial_state()

    state.sections['customer'].fields[
        'brand'
    ].value = '云裳'

    result = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'customer',
            'field_id': 'brand',
            'value': '新品牌',
        }],
    }, state)

    assert state.sections['customer'].fields[
        'brand'
    ].value == '云裳'

    assert '失败' in result
    assert '确认' in result


def test_text_conflict_updates_after_confirmation():
    """用户确认修改后允许更新 text 字段。"""
    state = create_initial_state()

    state.sections['customer'].fields[
        'brand'
    ].value = '云裳'

    result = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'customer',
            'field_id': 'brand',
            'value': '新品牌',
            'confirmed': True,
        }],
    }, state)

    assert state.sections['customer'].fields[
        'brand'
    ].value == '新品牌'

    assert '失败' not in result


def test_image_fields_merge_incrementally():
    """分多轮上传图片时保留旧图片并去重。"""
    state = create_initial_state()

    state.sections['venue'].fields[
        'venue_photo'
    ].value = ['room-1.jpg']

    result = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'venue',
            'field_id': 'venue_photo',
            'value': [
                'room-2.jpg',
                'room-1.jpg',
            ],
        }],
    }, state)

    assert state.sections['venue'].fields[
        'venue_photo'
    ].value == [
        'room-1.jpg',
        'room-2.jpg',
    ]

    assert '失败' not in result


def test_fill_fields_writes_host_height_dimension():
    state = create_initial_state()

    result = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'host',
            'field_id': 'height',
            'value': {
                '男主播': '175',
            },
        }],
    }, state)

    assert state.sections['host'].fields[
        'height'
    ].value == {
        '男主播': '175',
    }
    assert '失败' not in result
