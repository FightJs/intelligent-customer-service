"""API 端点测试（用 TestClient，mock 掉 LLM 调用）。

session 和 chat 端点会调 LLM，测试里 mock 成固定回复，
避免依赖网络和真实 API 花费。
"""
from unittest.mock import patch
from dataclasses import dataclass

from fastapi.testclient import TestClient

from api.app import app
from agent.gather import ToolEvent, TurnResult
from survey.state import create_initial_state, to_dict

client = TestClient(app)


@patch('api.app.initial_greeting', return_value='您好，请问品牌名？')
def test_create_session_returns_greeting(mock_greeting):
    r = client.post('/api/session')
    assert r.status_code == 200
    data = r.json()
    assert 'session_id' in data
    assert data['greeting'] == '您好，请问品牌名？'
    fs = data['form_state']
    assert fs['currentSectionId'] == 'customer'
    assert len(fs['sections']) == 10


@patch('api.app.initial_greeting', return_value='hi')
def test_get_session_recovers_state(mock_greeting):
    sid = client.post('/api/session').json()['session_id']
    r = client.get(f'/api/session/{sid}')
    assert r.status_code == 200
    assert r.json()['session_id'] == sid


def test_get_missing_session_404():
    r = client.get('/api/session/nonexistent')
    assert r.status_code == 404


def _mock_run_turn_stream(user_msg, state=None):
    """模拟流式 agent：返回一个 fill 事件 + token + done。"""
    if state is None:
        state = create_initial_state()
    state.sections['customer'].fields['brand'].value = user_msg
    events = [ToolEvent(kind='fill', section_id='customer', field_id='brand', value=user_msg)]
    yield ('events', events)
    yield ('token', '收到')
    yield ('token', ' ✓')
    yield ('done', TurnResult(
        reply='收到 ✓',
        tool_events=events,
        state=state,
        form_complete=False,
    ))


@patch('api.app.initial_greeting', return_value='hi')
def test_chat_returns_tool_and_token_events(mock_greeting):
    sid = client.post('/api/session').json()['session_id']
    with patch('api.app.run_turn_stream',
               side_effect=lambda state, msg, history=None: _mock_run_turn_stream(msg, state)):
        with client.stream('POST', '/api/chat',
                           json={'session_id': sid, 'message': '云裳'}) as resp:
            assert resp.status_code == 200
            event_types = []
            tool_data = None
            done_data = None
            current_event = None
            for line in resp.iter_lines():
                if line.startswith('event:'):
                    current_event = line.split(':', 1)[1].strip()
                    event_types.append(current_event)
                elif line.startswith('data:') and current_event:
                    data_str = line.split(':', 1)[1].strip()
                    if current_event == 'tool':
                        import json
                        tool_data = json.loads(data_str)
                    elif current_event == 'done':
                        import json
                        done_data = json.loads(data_str)
    assert 'tool' in event_types
    assert 'token' in event_types
    assert event_types[-1] == 'done'
    assert tool_data is not None
    assert len(tool_data['events']) == 1
    assert done_data is not None
    assert 'form_state' in done_data


def test_chat_missing_session_404():
    r = client.post('/api/chat',
                    json={'session_id': 'nonexistent', 'message': 'hello'})
    assert r.status_code == 404


@patch('api.app.initial_greeting', return_value='hi')
def test_generate_all_types(mock_greeting):
    sid = client.post('/api/session').json()['session_id']
    for doc_type, suffix in [('markdown', 'md'), ('excel', 'xlsx'), ('word', 'docx')]:
        r = client.post(f'/api/generate/{doc_type}?session_id={sid}')
        assert r.status_code == 200
        assert r.json()['filename'].endswith(suffix)
