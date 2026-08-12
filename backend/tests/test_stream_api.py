"""流式聊天 API 测试。"""
from __future__ import annotations

import re
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from agent.loop import AgentStreamDelta, AgentStreamResult, AgentStreamStatus
from agent.tools import ToolEvent
from api.app import app
from store import db


@pytest.fixture
def client(tmp_path):
    original_path = db.DB_PATH
    db.DB_PATH = tmp_path / 'stream-test.db'
    try:
        with patch('api.app.initial_greeting', return_value='hi'):
            with TestClient(app) as test_client:
                yield test_client
    finally:
        db.DB_PATH = original_path


@pytest.fixture
def auth_headers(client):
    response = client.post(
        '/api/auth/register',
        json={'username': 'stream_user', 'password': 'pass123456'},
    )
    return {'Authorization': f"Bearer {response.json()['token']}"}


def _session_id(client, headers):
    return client.post('/api/session', headers=headers).json()['session_id']


def test_stream_emits_ordered_events_persists_and_replays(client, auth_headers):
    session_id = _session_id(client, auth_headers)
    request_id = str(uuid4())

    async def fake_stream(state, message, history, images=None):
        yield AgentStreamStatus(phase='generating', message='正在生成回复')
        yield AgentStreamDelta('好的，')
        yield AgentStreamDelta('已记录。')
        event = ToolEvent(kind='fill', section_id='customer', field_id='brand', value='云裳')
        yield AgentStreamResult(
            reply='好的，已记录。',
            tool_events=[event],
            state=state,
            form_complete=False,
            suggestions=[],
        )

    payload = {
        'request_id': request_id,
        'session_id': session_id,
        'message': '品牌名是云裳',
    }
    with patch('api.app.run_agent_stream', fake_stream):
        response = client.post('/api/chat/stream', json=payload, headers=auth_headers)

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/event-stream')
    events = re.findall(r'^event: (.+)$', response.text, flags=re.MULTILINE)
    assert events == ['start', 'status', 'delta', 'delta', 'status', 'done']
    assert '"text":"好的，"' in response.text
    assert '"assistant_message_id":' in response.text
    assert len(db.get_messages(session_id)) == 2

    with patch('api.app.run_agent_stream') as stream:
        replay = client.post('/api/chat/stream', json=payload, headers=auth_headers)

    assert replay.status_code == 200
    assert replay.text.count('event: done') == 1
    assert stream.call_count == 0
    assert len(db.get_messages(session_id)) == 2


def test_stream_rejects_in_progress_request(client, auth_headers):
    session_id = _session_id(client, auth_headers)
    request_id = str(uuid4())
    user = db.get_user_by_username('stream_user')
    assert user is not None
    db.begin_chat_request(request_id, session_id, user['id'], '你好', None)

    response = client.post(
        '/api/chat/stream',
        json={'request_id': request_id, 'session_id': session_id, 'message': '你好'},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'request_in_progress'


def test_stream_validates_request_before_opening_sse(client, auth_headers):
    session_id = _session_id(client, auth_headers)
    response = client.post(
        '/api/chat/stream',
        json={'request_id': 'not-a-uuid', 'session_id': session_id, 'message': ' '},
        headers=auth_headers,
    )

    assert response.status_code == 422
