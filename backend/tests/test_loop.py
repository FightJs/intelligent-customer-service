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


def _mock_empty_capture_response():
    """模拟当前用户消息没有可写入字段。"""
    return _mock_tool_response(
        'fill_fields',
        {
            'updates': [],
        },
        tool_use_id='capture_1',
    )


@patch('agent.loop.get_client')
def test_run_agent_text_only(mock_get_client):
    """没有字段可写时，先捕获空 updates，再回复文本。"""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _mock_empty_capture_response(),
        _mock_text_response(
            '您好！品牌名是？'
        ),
    ]
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    result = run_agent(state, '你好')

    assert isinstance(result, AgentResult)
    assert result.reply == '您好！品牌名是？'
    assert result.tool_events == []
    assert (
        mock_client.messages.create.call_count
        == 2
    )


@patch('agent.loop.get_client')
def test_run_agent_capture_without_tool_does_not_crash(
    mock_get_client,
):
    """捕获轮没有返回工具时，不应导致请求 500。"""
    mock_client = MagicMock()

    mock_client.messages.create.side_effect = [
        _mock_text_response(''),
        _mock_text_response(
            '您好！请问有什么可以帮您？'
        ),
    ]

    mock_get_client.return_value = mock_client

    state = create_initial_state()

    result = run_agent(
        state,
        '你好',
    )

    assert result.reply == (
        '您好！请问有什么可以帮您？'
    )

    assert result.tool_events == []

    assert (
        mock_client.messages.create.call_count
        == 2
    )


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
    assert (
        state.sections['customer']
        .fields['brand']
        .value
        == '云裳'
    )

    first_request = (
        mock_client.messages.create
        .call_args_list[0]
        .kwargs
    )

    assert first_request['tool_choice'] == {
        'type': 'tool',
        'name': 'fill_fields',
    }

    assert [
        tool['name']
        for tool in first_request['tools']
    ] == ['fill_fields']


@patch('agent.loop.get_client')
def test_run_agent_max_iterations(
    mock_get_client,
):
    """一直调用工具时，达到上限后结束循环。"""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = (
        _mock_empty_capture_response()
    )
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    result = run_agent(state, '你好')

    assert isinstance(result.reply, str)
    assert (
        mock_client.messages.create.call_count
        == 5
    )


@patch('agent.loop.get_client')
def test_run_agent_strips_leading_assistant_history(mock_get_client):
    """history 以 assistant（开场白）开头时，应丢弃使第一条为 user。"""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _mock_empty_capture_response(),
        _mock_text_response('好的'),
    ]
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
        _mock_empty_capture_response(),
        _mock_tool_response(
            'skip_section',
            {
                'section_id': 'nonexistent_section',
            },
        ),
        _mock_text_response(
            '抱歉，出了点问题。'
        ),
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
    """system prompt 应强调写入优先和必要确认。"""
    state = create_initial_state()
    prompt = _build_system_prompt(state)

    assert '采集纪律' in prompt
    assert '信息成功写入表单优先于减少重复' in prompt
    assert '允许再次确认' in prompt
    assert '已采集' in prompt


@patch('agent.loop.get_client')
def test_run_agent_recomputes_section_status(mock_get_client):
    """run_agent 返回前应重算 section.status（治"全 pending"显示问题）。"""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _mock_empty_capture_response(),
        _mock_text_response('好的'),
    ]
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
    mock_client.messages.create.side_effect = [
        _mock_empty_capture_response(),
        _mock_text_response('品牌名是？'),
    ]
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    # 初始 state 第一个未填是 customer.brand（text）
    result = run_agent(state, '你好')
    assert result.suggestions == []


@patch('agent.loop.get_client')
def test_suggestions_populated_for_choice_field(mock_get_client):
    """下一个未填字段是 choice 类时，suggestions 应含 options 供前端渲染 chip。"""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _mock_empty_capture_response(),
        _mock_text_response('行业大类是？'),
    ]
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


@patch('agent.loop.get_client')
def test_suggestions_filtered_when_reply_does_not_match_choice(
    mock_get_client,
):
    """最终回复未询问候选字段时，不返回快捷回答。"""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _mock_empty_capture_response(),
        _mock_text_response(
            '接下来请介绍一下您的主播团队。'
        ),
    ]
    mock_get_client.return_value = mock_client

    state = create_initial_state()

    for field_id in [
        'brand',
        'contact',
        'phone',
        'wechat',
        'city',
        'source',
        'date',
    ]:
        state.sections[
            'customer'
        ].fields[field_id] = TextValue(
            type='text',
            value='x',
        )

    result = run_agent(
        state,
        '下一步',
    )

    assert result.suggestions == []


@patch('agent.loop.get_client')
def test_suggestions_match_multiple_option_labels(
    mock_get_client,
):
    """回复提到多个候选项时返回快捷回答。"""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _mock_empty_capture_response(),
        _mock_text_response(
            '您主要做女装、美妆还是珠宝？'
        ),
    ]
    mock_get_client.return_value = mock_client

    state = create_initial_state()

    for field_id in [
        'brand',
        'contact',
        'phone',
        'wechat',
        'city',
        'source',
        'date',
    ]:
        state.sections[
            'customer'
        ].fields[field_id] = TextValue(
            type='text',
            value='x',
        )

    result = run_agent(
        state,
        '下一步',
    )

    assert len(result.suggestions) == 1
    assert (
        result.suggestions[0]['field_id']
        == 'category'
    )


@patch('agent.loop.get_client')
def test_run_agent_uses_summary_and_recent_messages(
    mock_get_client,
):
    """较早历史生成摘要，近期 12 条保留原文。"""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        # 第一次：生成较早历史摘要
        _mock_text_response(
            '客户早期确认品牌为云裳。'
        ),

        # 第二次：捕获当前用户消息
        _mock_empty_capture_response(),

        # 第三次：生成正式客服回复
        _mock_text_response('好的'),
    ]
    mock_get_client.return_value = mock_client

    history = []

    for index in range(8):
        history.extend([
            {
                'role': 'user',
                'content': f'user-{index}',
            },
            {
                'role': 'assistant',
                'content': f'assistant-{index}',
            },
        ])

    state = create_initial_state()

    result = run_agent(
        state,
        '当前消息',
        history=history,
    )

    assert result.reply == '好的'

    # 摘要 + 捕获 + 正式回复，共三次调用。
    assert (
        mock_client.messages.create.call_count
        == 3
    )

    # 第一次调用：摘要较早历史。
    summary_call = (
        mock_client.messages.create
        .call_args_list[0]
    )

    summary_source = (
        summary_call
        .kwargs['messages'][0]['content']
    )

    assert 'user-0' in summary_source
    assert 'assistant-1' in summary_source
    assert 'user-2' not in summary_source

    # 第二次调用：捕获当前消息。
    capture_call = (
        mock_client.messages.create
        .call_args_list[1]
    )

    capture_messages = (
        capture_call.kwargs['messages']
    )

    # MagicMock 保存的是同一个 messages 列表引用。
    # 捕获完成后又追加了 tool_use 和 tool_result 两条消息，
    # 因此只检查捕获请求原本包含的前 13 条。
    capture_input_messages = capture_messages[:13]

    # 最近 12 条历史 + 当前消息。
    assert len(capture_input_messages) == 13

    assert capture_input_messages[0] == {
    'role': 'user',
    'content': 'user-2',
    }

    assert capture_input_messages[-1] == {
    'role': 'user',
    'content': '当前消息',
    }

    assert capture_call.kwargs['tool_choice'] == {
        'type': 'tool',
        'name': 'fill_fields',
    }

    # 第三次调用：生成正式客服回复。
    reply_call = (
        mock_client.messages.create
        .call_args_list[2]
    )

    assert (
        '客户早期确认品牌为云裳。'
        in reply_call.kwargs['system']
    )


def test_system_prompt_includes_table_columns():
    state = create_initial_state()

    prompt = _build_system_prompt(state)

    assert 'equipment.inventory' in prompt
    assert 'type=设备类型' in prompt
    assert 'model=品牌型号' in prompt
    assert 'qty=数量' in prompt
    assert 'note=备注' in prompt


def test_system_prompt_requires_inventory_when_existing():
    """有现有设备时，提示词要求立即采集设备明细。"""
    state = create_initial_state()

    state.sections['budget'].fields[
        'has_existing'
    ].value = 'yes'

    prompt = _build_system_prompt(state)

    assert (
        '下一个该问：'
        '【八、现有设备情况】'
        '现有设备明细'
        in prompt
    )

    required_part = prompt.split(
        '当前需要推进的必填字段：',
        1,
    )[1].split(
        '用户主动提及时可记录的选填字段',
        1,
    )[0]

    assert 'equipment.inventory' in required_part


@patch('agent.loop.get_client')
def test_run_agent_tool_event_uses_stored_value(mock_get_client):
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _mock_tool_response('fill_fields', {
            'updates': [{
                'section_id': 'industry',
                'field_id': 'category',
                'value': '女装',
            }],
        }),
        _mock_text_response('已记录。'),
    ]
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    result = run_agent(state, '行业是女装')

    assert state.sections['industry'].fields['category'].value == 'women'
    assert result.tool_events[0].value == 'women'


def test_system_prompt_separates_required_and_optional_fields():
    state = create_initial_state()

    prompt = _build_system_prompt(state)

    required_part = prompt.split(
        '当前需要推进的必填字段：',
        1,
    )[1].split(
        '用户主动提及时可记录的选填字段',
        1,
    )[0]

    optional_part = prompt.split(
        '用户主动提及时可记录的选填字段',
        1,
    )[1].split(
        '当前进度',
        1,
    )[0]

    assert 'customer.brand' in required_part
    assert 'equipment.inventory' not in required_part
    assert 'equipment.inventory' in optional_part
    assert '禁止主动询问选填字段' in prompt


@patch('agent.loop.get_client')
def test_run_agent_uses_stable_llm_parameters(
    mock_get_client,
):
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _mock_empty_capture_response(),
        _mock_text_response('您好'),
    ]
    mock_get_client.return_value = mock_client

    state = create_initial_state()
    run_agent(state, '你好')

    capture_request = (
        mock_client.messages.create
        .call_args_list[0]
        .kwargs
    )

    reply_request = (
        mock_client.messages.create
        .call_args_list[1]
        .kwargs
    )

    assert capture_request['temperature'] == 0.3
    assert capture_request['thinking'] == {
        'type': 'disabled',
    }

    assert capture_request['tool_choice'] == {
        'type': 'tool',
        'name': 'fill_fields',
    }

    assert reply_request['temperature'] == 0.3
    assert reply_request['thinking'] == {
        'type': 'disabled',
    }

    assert reply_request['tool_choice'] == {
        'type': 'auto',
    }


def test_system_prompt_handles_no_more_information():
    state = create_initial_state()

    prompt = _build_system_prompt(state)

    assert '不用补充' in prompt
    assert '禁止再次询问' in prompt


@patch('agent.loop.get_client')
def test_run_agent_persists_field_before_reply(
    mock_get_client,
):
    """客服确认收到前，必须先把字段写入 state。"""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _mock_tool_response(
            'fill_fields',
            {
                'updates': [{
                    'section_id': 'industry',
                    'field_id': 'subcategory',
                    'value': '茶叶',
                }],
            },
        ),
        _mock_text_response(
            '好的，茶叶已经记录。'
        ),
    ]
    mock_get_client.return_value = mock_client

    state = create_initial_state()

    result = run_agent(
        state,
        '茶叶',
    )

    assert (
        state.sections['industry']
        .fields['subcategory']
        .value
        == '茶叶'
    )

    assert result.reply == '好的，茶叶已经记录。'

    first_request = (
        mock_client.messages.create
        .call_args_list[0]
        .kwargs
    )

    assert first_request['tool_choice'] == {
        'type': 'tool',
        'name': 'fill_fields',
    }

    assert [
        tool['name']
        for tool in first_request['tools']
    ] == ['fill_fields']