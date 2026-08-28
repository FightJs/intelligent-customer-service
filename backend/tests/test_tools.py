"""tools.py 执行函数测试。"""
import pytest
from survey.state import create_initial_state
from agent.tools import execute_tool, ToolEvent, TOOL_DEFS, apply_updates
from agent.flow import is_field_visible
from tests.test_uploads import make_png_data_uri


def test_fill_fields_updates_state():
    state = create_initial_state()
    msg, ok = execute_tool('fill_fields', {
        'updates': [
            {'section_id': 'customer', 'field_id': 'brand', 'value': '云裳'},
            {'section_id': 'customer', 'field_id': 'phone', 'value': '138'},
        ]
    }, state)
    assert ok
    assert state.sections['customer'].fields['brand'].value == '云裳'
    assert state.sections['customer'].fields['phone'].value == '138'
    assert '云裳' in msg

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

def test_skip_section_rejects_future_module():
    state = create_initial_state(session_id='sess1')
    msg, ok = execute_tool(
        'skip_section',
        {'section_id': 'status', 'reason': '跳过'},
        state,
    )
    assert not ok
    assert '当前' in msg
    assert state.sections['status'].status != 'skipped'

def test_get_progress_returns_next_field():
    state = create_initial_state()
    msg, ok = execute_tool('get_progress', {}, state)
    assert ok
    assert 'brand' in msg
    assert 'customer' in msg

def test_set_current_section():
    state = create_initial_state()
    execute_tool('set_current_section', {'section_id': 'venue'}, state)
    assert state.current_section_id == 'venue'


def test_unknown_tool_returns_error():
    state = create_initial_state()
    msg, ok = execute_tool('nonexistent', {}, state)
    assert not ok
    assert 'error' in msg.lower() or 'unknown' in msg.lower()

def test_tool_defs_has_five_tools():
    names = [
        tool['name']
        for tool in TOOL_DEFS
    ]

    assert names == [
        'fill_fields',
        'skip_field',
        'skip_section',
        'get_progress',
        'set_current_section',
    ]


def test_fill_fields_returns_failure_details():
    """非法 section_id/field_id 时返回值应含失败明细（不再静默吞掉）。"""
    state = create_initial_state()
    msg, ok = execute_tool('fill_fields', {
        'updates': [
            {'section_id': 'customer', 'field_id': 'brand', 'value': '云裳'},
            {'section_id': 'nonexistent', 'field_id': 'x', 'value': 'y'},
            {'section_id': 'customer', 'field_id': 'nonfield', 'value': 'z'},
        ]
    }, state)
    assert not ok
    # 成功的填了
    assert state.sections['customer'].fields['brand'].value == '云裳'
    # 失败的应有明细
    assert '失败' in msg
    assert 'nonexistent' in msg or '不存在' in msg


def test_choice_validation_rejects_invalid_value():
    """choice 字段 value 不在 options 内时拒绝（返回失败，不写入脏数据）。"""
    state = create_initial_state()
    msg, ok = execute_tool('fill_fields', {
        'updates': [{'section_id': 'industry', 'field_id': 'category', 'value': 'invalid_value'}]
    }, state)
    assert not ok
    # 字段未被污染
    assert state.sections['industry'].fields['category'].value is None
    # 失败明细提到非法值
    assert '失败' in msg or 'options' in msg


def test_choice_label_auto_mapped_to_value():
    """传中文 label（如"女装"）应自动反查为 value（women）。"""
    state = create_initial_state()
    execute_tool('fill_fields', {
        'updates': [{'section_id': 'industry', 'field_id': 'category', 'value': '女装'}]
    }, state)
    assert state.sections['industry'].fields['category'].value == 'women'


@pytest.mark.parametrize(
    ('field_id', 'answer', 'expected'),
    [
        ('pain_points', '流量少', ['traffic']),
        ('pain_points', '流量少、转化率低', ['traffic', 'conversion']),
    ],
)
def test_choice_multi_accepts_single_or_delimited_label_string(
    field_id,
    answer,
    expected,
):
    state = create_initial_state()

    msg, ok = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'status',
            'field_id': field_id,
            'value': answer,
        }],
    }, state)

    assert ok
    assert state.sections['status'].fields[field_id].value == expected
    assert '失败' not in msg


def test_choice_multi_accepts_focus_label_and_preserves_custom_answer():
    state = create_initial_state()

    msg, ok = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'goal',
            'field_id': 'focus',
            'value': '商品质感',
        }],
    }, state)

    assert ok
    assert state.sections['goal'].fields['focus'].value == ['product-quality']

    msg, ok = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'goal',
            'field_id': 'focus',
            'value': '随便变好看',
        }],
    }, state)
    assert ok
    assert state.sections['goal'].fields['focus'].value == [
        'product-quality',
        '随便变好看',
    ]


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

    msg, ok = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'equipment',
            'field_id': 'inventory',
            'value': [{
                'type': '相机',
                'model': 'Sony A7M4',
                'qty': 1,
            }],
        }],
    }, state)

    assert state.sections['equipment'].fields['inventory'].value == [{
        'type': '相机',
        'model': 'Sony A7M4',
        'qty': '1',
    }]
    assert '失败' not in msg


def test_fill_fields_table_accepts_single_row_object():
    state = create_initial_state()

    msg, ok = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'equipment',
            'field_id': 'inventory',
            'value': {'type': '相机', 'model': 'Sony A7M4', 'qty': 1},
        }],
    }, state)

    assert ok
    assert state.sections['equipment'].fields['inventory'].value == [{
        'type': '相机', 'model': 'Sony A7M4', 'qty': '1',
    }]
    assert '失败' not in msg


def test_fill_fields_table_rejects_unstructured_string():
    state = create_initial_state()

    msg, ok = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'equipment',
            'field_id': 'inventory',
            'value': 'Sony A7M4',
        }],
    }, state)

    assert not ok
    assert 'list 或 object' in msg


def test_fill_fields_table_rejects_unknown_columns():
    state = create_initial_state()

    msg, ok = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'equipment',
            'field_id': 'inventory',
            'value': [{
                'brand': 'Sony',
            }],
        }],
    }, state)

    assert state.sections['equipment'].fields['inventory'].value == []
    assert '失败' in msg
    assert '未知列' in msg


def test_text_conflict_requires_confirmation():
    """text 已有不同值时不能静默覆盖。"""
    state = create_initial_state()

    state.sections['customer'].fields[
        'brand'
    ].value = '云裳'

    msg, ok = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'customer',
            'field_id': 'brand',
            'value': '新品牌',
        }],
    }, state)

    assert state.sections['customer'].fields[
        'brand'
    ].value == '云裳'

    assert '失败' in msg
    assert '确认' in msg


def test_text_conflict_updates_after_confirmation():
    """用户确认修改后允许更新 text 字段。"""
    state = create_initial_state()

    state.sections['customer'].fields[
        'brand'
    ].value = '云裳'

    msg, ok = execute_tool('fill_fields', {
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

    assert '失败' not in msg


def test_image_fields_merge_incrementally(tmp_path, monkeypatch):
    """分多轮上传图片时保留旧图片并去重（id 必须是真实落盘的图片）。"""
    import store.uploads as uploads

    monkeypatch.setattr(uploads, 'UPLOADS_ROOT', tmp_path)

    img1 = uploads.save_upload('sess1', make_png_data_uri())
    img2 = uploads.save_upload('sess1', make_png_data_uri())

    state = create_initial_state(session_id='sess1')
    state.sections['venue'].fields['venue_photo'].value = [img1.id]

    msg, ok = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'venue',
            'field_id': 'venue_photo',
            'value': [img2.id, img1.id],
        }],
    }, state)

    assert ok
    assert state.sections['venue'].fields['venue_photo'].value == [img1.id, img2.id]
    assert '失败' not in msg


def test_image_field_accepts_single_image_id_string(tmp_path, monkeypatch):
    import store.uploads as uploads

    monkeypatch.setattr(uploads, 'UPLOADS_ROOT', tmp_path)
    image = uploads.save_upload('sess1', make_png_data_uri())
    state = create_initial_state(session_id='sess1')

    msg, ok = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'venue',
            'field_id': 'venue_photo',
            'value': image.id,
        }],
    }, state)

    assert ok
    assert state.sections['venue'].fields['venue_photo'].value == [image.id]
    assert '失败' not in msg


def test_apply_updates_reports_malformed_items_without_raising():
    state = create_initial_state()

    count, failures = apply_updates(state, [{}, 'bad'])

    assert count == 0
    assert len(failures) == 2
    assert all('updates[' in failure for failure in failures)


def test_image_fields_reject_hallucinated_id(tmp_path, monkeypatch):
    """LLM 编造的图片 id（未落盘）必须被拒绝。"""
    import store.uploads as uploads

    monkeypatch.setattr(uploads, 'UPLOADS_ROOT', tmp_path)

    state = create_initial_state(session_id='sess1')
    msg, ok = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'venue',
            'field_id': 'venue_photo',
            'value': ['sess1/notexists.jpg'],
        }],
    }, state)

    assert not ok
    assert '无效' in msg
    assert state.sections['venue'].fields['venue_photo'].value == []


def test_image_fields_reject_real_image_from_another_session(tmp_path, monkeypatch):
    """即使图片真实存在，也不能把其他会话的图片 id 写入当前问卷。"""
    import store.uploads as uploads

    monkeypatch.setattr(uploads, 'UPLOADS_ROOT', tmp_path)
    other_image = uploads.save_upload('sess2', make_png_data_uri())
    state = create_initial_state(session_id='sess1')

    msg, ok = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'venue',
            'field_id': 'venue_photo',
            'value': [other_image.id],
        }],
    }, state)

    assert not ok
    assert '不属于当前会话' in msg
    assert state.sections['venue'].fields['venue_photo'].value == []


def test_fill_fields_writes_host_profile_text():
    state = create_initial_state()

    msg, ok = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'host',
            'field_id': 'profile',
            'value': '男主播175cm，中等体型',
        }],
    }, state)

    assert state.sections['host'].fields[
        'profile'
    ].value == '男主播175cm，中等体型'
    assert '失败' not in msg


def test_fill_fields_writes_multiple_customer_identities_from_labels():
    state = create_initial_state()

    msg, ok = execute_tool('fill_fields', {
        'updates': [{
            'section_id': 'customer',
            'field_id': 'identity',
            'value': ['主理人（老板）', '主播'],
        }],
    }, state)

    assert ok
    assert state.sections['customer'].fields['identity'].value == [
        'owner', 'host',
    ]
    assert '失败' not in msg
