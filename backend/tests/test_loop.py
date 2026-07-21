"""Agent loop 测试（mock anthropic 响应）。"""
from unittest.mock import patch, MagicMock
from survey.state import create_initial_state
from survey.models import TextValue
from agent.loop import run_agent, AgentResult, _build_system_prompt


def _mock_text_response(text: str):
    """构造一个 end_turn 的 mock response。"""
    resp = MagicMock()
    resp.stop_reason = 'end_turn'
    block = MagicMock()
    block.type = 'text'
    block.text = text
    resp.content = [block]
    return resp


def _mock_tool_response(tool_name: str, tool_input: dict, tool_use_id: str = 'tu_1'):
    """构造一个 tool_use 的 mock response。"""
    resp = MagicMock()
    resp.stop_reason = 'tool_use'
    block = MagicMock()
    block.type = 'tool_use'
    block.name = tool_name
    block.input = tool_input
    block.id = tool_use_id
    resp.content = [block]
    return resp


@patch('agent.loop.get_client')
def test_run_agent_text_only(mock_get_client):
    """模型直接回复文本，不调 tool。"""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_text_response('您好！品牌名是？')
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    result = run_agent(state, '你好')
    assert isinstance(result, AgentResult)
    assert result.reply == '您好！品牌名是？'
    assert result.tool_events == []


@patch('agent.loop.get_client')
def test_run_agent_fill_fields_then_reply(mock_get_client):
    """模型先调 fill_fields，再回复文本。"""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _mock_tool_response('fill_fields', {
            'updates': [{'section_id': 'customer', 'field_id': 'brand', 'value': '云裳'}]
        }),
        _mock_text_response('已记下云裳品牌。'),
    ]
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    result = run_agent(state, '品牌叫云裳')
    assert result.reply == '已记下云裳品牌。'
    assert len(result.tool_events) == 1
    assert result.tool_events[0].kind == 'fill'
    assert result.tool_events[0].field_id == 'brand'
    assert state.sections['customer'].fields['brand'].value == '云裳'


@patch('agent.loop.get_client')
def test_run_agent_max_iterations(mock_get_client):
    """超过最大循环次数时跳出，不无限循环。"""
    mock_client = MagicMock()
    # 一直返回 tool_use，永不 end_turn
    mock_client.messages.create.return_value = _mock_tool_response('get_progress', {})
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    result = run_agent(state, '你好')
    # 应该在 5 次后跳出，有 reply（兜底文本）
    assert isinstance(result.reply, str)
    assert mock_client.messages.create.call_count <= 6


@patch('agent.loop.get_client')
def test_run_agent_strips_leading_assistant_history(mock_get_client):
    """history 以 assistant（开场白）开头时，应丢弃使第一条为 user。"""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_text_response('好的')
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    run_agent(state, '你好', history=[
        {'role': 'assistant', 'content': '您好！我是顾问...'},
        {'role': 'user', 'content': '之前问过的问题'},
        {'role': 'assistant', 'content': '之前的回复'},
    ])
    # 检查传给 messages.create 的 messages 参数
    call_args = mock_client.messages.create.call_args
    sent_messages = call_args.kwargs['messages']
    assert sent_messages[0]['role'] == 'user', '第一条必须是 user role'


@patch('agent.loop.get_client')
def test_run_agent_tool_error_does_not_crash(mock_get_client):
    """tool 执行抛异常时，应返回错误信息给模型，不 500。"""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _mock_tool_response('skip_section', {'section_id': 'nonexistent_section'}),
        _mock_text_response('抱歉，出了点问题。'),
    ]
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    result = run_agent(state, '跳过某章节')
    # 不应抛异常，应有兜底回复
    assert isinstance(result.reply, str)


def test_system_prompt_includes_collected_values():
    """system prompt 应包含已采集字段的具体值（治"重复问"根因）。"""
    state = create_initial_state()
    # 空 state 应显示"暂无"
    prompt_empty = _build_system_prompt(state)
    assert '已采集' in prompt_empty

    # 填一个字段后，应在 prompt 中看到值
    state.sections['customer'].fields['brand'] = TextValue(type='text', value='云裳')
    prompt_filled = _build_system_prompt(state)
    assert '云裳' in prompt_filled
    assert 'customer.brand' in prompt_filled


def test_system_prompt_includes_collect_discipline():
    """system prompt 应包含采集纪律（禁止重复问）。"""
    state = create_initial_state()
    prompt = _build_system_prompt(state)
    assert '采集纪律' in prompt
    assert '禁止重复询问' in prompt
    assert '已采集' in prompt


@patch('agent.loop.get_client')
def test_run_agent_recomputes_section_status(mock_get_client):
    """run_agent 返回前应重算 section.status（治"全 pending"显示问题）。"""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_text_response('好的')
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    # 填完 customer 全部必填，模拟"已采集"
    for fid in ['brand', 'contact', 'phone', 'wechat', 'city', 'source', 'date']:
        state.sections['customer'].fields[fid] = TextValue(type='text', value='x')

    result = run_agent(state, 'test')
    # customer 章节应标记为 complete（而非 pending）
    assert result.state.sections['customer'].status == 'complete'


@patch('agent.loop.get_client')
def test_suggestions_empty_for_text_field(mock_get_client):
    """下一个未填字段是 text 类（无 options）时，suggestions 应为空。"""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_text_response('品牌名是？')
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    # 初始 state 第一个未填是 customer.brand（text）
    result = run_agent(state, '你好')
    assert result.suggestions == []


@patch('agent.loop.get_client')
def test_suggestions_populated_for_choice_field(mock_get_client):
    """下一个未填字段是 choice 类时，suggestions 应含 options 供前端渲染 chip。"""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_text_response('行业大类是？')
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    # 填完 customer 全部字段，让 next 落到 industry.category（choice-single）
    for fid in ['brand', 'contact', 'phone', 'wechat', 'city', 'source', 'date']:
        state.sections['customer'].fields[fid] = TextValue(type='text', value='x')

    result = run_agent(state, '下一步')
    assert len(result.suggestions) == 1
    s = result.suggestions[0]
    assert s['section_id'] == 'industry'
    assert s['field_id'] == 'category'
    assert len(s['options']) == 9
    assert {'value': 'women', 'label': '女装'} in s['options']
