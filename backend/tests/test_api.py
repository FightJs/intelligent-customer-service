"""API 端点测试（用 TestClient，mock 掉 LLM 调用）。

session 和 chat 端点会调 LLM，测试里 mock 成固定回复，
避免依赖网络和真实 API 花费。
"""
from unittest.mock import patch
from dataclasses import dataclass

from fastapi.testclient import TestClient

from api.app import app
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


@patch('api.app.initial_greeting', return_value='hi')
def test_chat_returns_json_response(mock_greeting):
    from agent.loop import AgentResult
    from agent.tools import ToolEvent
    from survey.state import create_initial_state
    sid = client.post('/api/session').json()['session_id']

    mock_result = AgentResult(
        reply='收到云裳品牌',
        tool_events=[ToolEvent(kind='fill', section_id='customer', field_id='brand', value='云裳')],
        state=create_initial_state(),
        form_complete=False,
    )
    with patch('api.app.run_agent', return_value=mock_result):
        r = client.post('/api/chat', json={'session_id': sid, 'message': '云裳'})
    assert r.status_code == 200
    data = r.json()
    assert data['reply'] == '收到云裳品牌'
    assert len(data['tool_events']) == 1
    assert data['tool_events'][0]['field_id'] == 'brand'
    assert data['form_complete'] is False
    assert 'form_state' in data


def test_chat_missing_session_404():
    r = client.post('/api/chat', json={'session_id': 'nonexistent', 'message': 'hi'})
    assert r.status_code == 404


@patch('api.app.initial_greeting', return_value='hi')
def test_generate_all_types(mock_greeting):
    sid = client.post('/api/session').json()['session_id']
    # markdown
    r = client.post(f'/api/generate/markdown?session_id={sid}')
    assert r.status_code == 200
    assert 'text/markdown' in r.headers.get('content-type', '')
    assert 'attachment' in r.headers.get('content-disposition', '')
    assert len(r.content) > 0
    # excel
    r2 = client.post(f'/api/generate/excel?session_id={sid}')
    assert r2.status_code == 200
    assert 'spreadsheet' in r2.headers.get('content-type', '')
    assert len(r2.content) > 0
    # word
    r3 = client.post(f'/api/generate/word?session_id={sid}')
    assert r3.status_code == 200
    assert 'wordprocessingml' in r3.headers.get('content-type', '')
    assert len(r3.content) > 0


def test_generate_missing_session_404():
    r = client.post('/api/generate/markdown?session_id=nonexistent')
    assert r.status_code == 404
