"""tools.py 执行函数测试。"""
import pytest
from survey.state import create_initial_state
from agent.tools import execute_tool, ToolEvent, TOOL_DEFS
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

def test_generate_deliverable_markdown():
    state = create_initial_state()
    state.sections['customer'].fields['brand'].value = '云裳'
    result = execute_tool('generate_deliverable', {'doc_type': 'markdown'}, state)
    assert 'markdown' in result.lower() or 'md' in result

def test_unknown_tool_returns_error():
    state = create_initial_state()
    result = execute_tool('nonexistent', {}, state)
    assert 'error' in result.lower() or 'unknown' in result.lower()

def test_tool_defs_has_five_tools():
    names = [t['name'] for t in TOOL_DEFS]
    assert names == ['fill_fields', 'skip_section', 'get_progress', 'set_current_section', 'generate_deliverable']
