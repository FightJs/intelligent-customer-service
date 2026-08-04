"""API 端点测试（用 TestClient，mock 掉 LLM 调用）。

所有业务端点都需要认证。测试用 register 拿 token，请求带 Authorization: Bearer。
所有涉及 create_session 的测试一律 mock 掉 initial_greeting，避免触发真实 LLM 调用
（CI 环境无 LLM_API_KEY，会报 anthropic 认证错误）。
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.app import app


@pytest.fixture(scope='module')
def client():
    """模块级 TestClient，用 with 触发 lifespan（init_db + admin 种子）。"""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _mock_greeting():
    """自动 mock initial_greeting，所有测试都不调真实 LLM 生成开场白。"""
    with patch('api.app.initial_greeting', return_value='hi'):
        yield


@pytest.fixture
def auth_headers(client):
    """注册一个测试用户，返回带 Authorization 头的 dict。每个测试独立用户名避免冲突。"""
    import secrets
    username = f'tester_{secrets.token_hex(4)}'
    r = client.post('/api/auth/register', json={'username': username, 'password': 'pass123456'})
    assert r.status_code == 200, r.text
    token = r.json()['token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def admin_headers(client):
    """用 env 配置的 admin 账号登录，返回 admin token 头。"""
    r = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin123456'})
    assert r.status_code == 200, r.text
    token = r.json()['token']
    return {'Authorization': f'Bearer {token}'}


# ── Auth 端点测试 ─────────────────────────────────────────────

def test_register_returns_token_and_user(client):
    import secrets
    username = f'newuser_{secrets.token_hex(4)}'
    r = client.post('/api/auth/register', json={'username': username, 'password': 'pass123456'})
    assert r.status_code == 200
    data = r.json()
    assert 'token' in data
    assert data['user']['username'] == username
    assert data['user']['role'] == 'user'


def test_register_duplicate_username_409(client):
    client.post('/api/auth/register', json={'username': 'dup', 'password': 'pass123456'})
    r = client.post('/api/auth/register', json={'username': 'dup', 'password': 'pass123456'})
    assert r.status_code == 409


def test_register_short_password_400(client):
    r = client.post('/api/auth/register', json={'username': 'short', 'password': '123'})
    assert r.status_code == 400


def test_login_success(client):
    client.post('/api/auth/register', json={'username': 'loginuser', 'password': 'pass123456'})
    r = client.post('/api/auth/login', json={'username': 'loginuser', 'password': 'pass123456'})
    assert r.status_code == 200
    assert 'token' in r.json()


def test_login_wrong_password_401(client):
    client.post('/api/auth/register', json={'username': 'loginuser2', 'password': 'pass123456'})
    r = client.post('/api/auth/login', json={'username': 'loginuser2', 'password': 'wrong'})
    assert r.status_code == 401


def test_login_nonexistent_user_401(client):
    r = client.post('/api/auth/login', json={'username': 'ghost', 'password': 'whatever'})
    assert r.status_code == 401


def test_me_with_token(client):
    import secrets
    username = f'meuser_{secrets.token_hex(4)}'
    r = client.post('/api/auth/register', json={'username': username, 'password': 'pass123456'})
    token = r.json()['token']
    r2 = client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert r2.status_code == 200
    assert r2.json()['username'] == username


def test_me_without_token_401(client):
    r = client.get('/api/auth/me')
    assert r.status_code == 401


def test_admin_seed_created(client):
    """启动时 admin 种子应自动创建（env 默认 admin/admin123456）。"""
    r = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin123456'})
    assert r.status_code == 200
    assert r.json()['user']['role'] == 'admin'


# ── 业务端点鉴权测试 ─────────────────────────────────────────

def test_create_session_without_token_401(client):
    r = client.post('/api/session')
    assert r.status_code == 401


def test_create_session_returns_greeting(client, auth_headers):
    r = client.post('/api/session', headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert 'session_id' in data
    assert data['greeting'] == 'hi'  # autouse fixture mock 的固定值
    fs = data['form_state']
    assert fs['currentSectionId'] == 'customer'
    assert len(fs['sections']) == 10


def test_get_session_recovers_state(client, auth_headers):
    sid = client.post('/api/session', headers=auth_headers).json()['session_id']
    r = client.get(f'/api/session/{sid}', headers=auth_headers)
    assert r.status_code == 200
    assert r.json()['session_id'] == sid


def test_get_missing_session_404(client, auth_headers):
    r = client.get('/api/session/nonexistent', headers=auth_headers)
    assert r.status_code == 404


def test_session_owner_isolation(client, auth_headers):
    """用户 A 创建的 session，用户 B 不能访问。"""
    sid = client.post('/api/session', headers=auth_headers).json()['session_id']
    # 注册另一个用户
    r = client.post('/api/auth/register', json={'username': 'other_user_' + sid[:4], 'password': 'pass123456'})
    other_headers = {'Authorization': f'Bearer {r.json()["token"]}'}
    r2 = client.get(f'/api/session/{sid}', headers=other_headers)
    assert r2.status_code == 403


def test_chat_returns_json_response(client, auth_headers):
    from agent.loop import AgentResult
    from agent.tools import ToolEvent
    from survey.state import create_initial_state
    sid = client.post('/api/session', headers=auth_headers).json()['session_id']

    mock_result = AgentResult(
        reply='收到云裳品牌',
        tool_events=[ToolEvent(kind='fill', section_id='customer', field_id='brand', value='云裳')],
        state=create_initial_state(),
        form_complete=False,
    )
    with patch('api.app.run_agent', return_value=mock_result):
        r = client.post('/api/chat', json={'session_id': sid, 'message': '云裳'}, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data['reply'] == '收到云裳品牌'
    assert len(data['tool_events']) == 1
    assert data['tool_events'][0]['field_id'] == 'brand'
    assert data['form_complete'] is False
    assert 'form_state' in data


def test_chat_missing_session_404(client, auth_headers):
    r = client.post('/api/chat', json={'session_id': 'nonexistent', 'message': 'hi'}, headers=auth_headers)
    assert r.status_code == 404


def test_generate_all_types(client, auth_headers):
    sid = client.post('/api/session', headers=auth_headers).json()['session_id']
    # markdown
    r = client.post(f'/api/generate/markdown?session_id={sid}', headers=auth_headers)
    assert r.status_code == 200
    assert 'text/markdown' in r.headers.get('content-type', '')
    assert 'attachment' in r.headers.get('content-disposition', '')
    assert len(r.content) > 0
    # excel
    r2 = client.post(f'/api/generate/excel?session_id={sid}', headers=auth_headers)
    assert r2.status_code == 200
    assert 'spreadsheet' in r2.headers.get('content-type', '')
    assert len(r2.content) > 0
    # word
    r3 = client.post(f'/api/generate/word?session_id={sid}', headers=auth_headers)
    assert r3.status_code == 200
    assert 'wordprocessingml' in r3.headers.get('content-type', '')
    assert len(r3.content) > 0


def test_generate_missing_session_404(client, auth_headers):
    r = client.post('/api/generate/markdown?session_id=nonexistent', headers=auth_headers)
    assert r.status_code == 404


def test_generate_markdown_persists_delivery(client, auth_headers, admin_headers):
    """生成 markdown 后，admin 能在交付物列表看到这条记录。"""
    sid = client.post('/api/session', headers=auth_headers).json()['session_id']
    client.post(f'/api/generate/markdown?session_id={sid}', headers=auth_headers)

    r = client.get('/api/admin/deliverables', headers=admin_headers)
    assert r.status_code == 200
    items = r.json()
    assert any(d['session_id'] == sid for d in items)


# ── Admin 端点测试 ────────────────────────────────────────────

def test_admin_endpoints_require_admin_role(client, auth_headers):
    """普通用户访问 admin 端点 → 403。"""
    r1 = client.get('/api/admin/users', headers=auth_headers)
    assert r1.status_code == 403
    r2 = client.get('/api/admin/deliverables', headers=auth_headers)
    assert r2.status_code == 403


def test_admin_users_list_includes_admin(client, admin_headers):
    r = client.get('/api/admin/users', headers=admin_headers)
    assert r.status_code == 200
    users = r.json()
    assert any(u['username'] == 'admin' and u['role'] == 'admin' for u in users)


def test_admin_deliverables_list(client, admin_headers):
    r = client.get('/api/admin/deliverables', headers=admin_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_admin_deliverables_filter_by_user(client, admin_headers, auth_headers):
    """按 user_id 筛选交付物。"""
    sid = client.post('/api/session', headers=auth_headers).json()['session_id']
    client.post(f'/api/generate/markdown?session_id={sid}', headers=auth_headers)
    user_id = client.get('/api/auth/me', headers=auth_headers).json()['id']

    r = client.get(f'/api/admin/deliverables?user_id={user_id}', headers=admin_headers)
    assert r.status_code == 200
    items = r.json()
    assert all(d['user_id'] == user_id for d in items)


def test_admin_get_deliverable_detail(client, admin_headers, auth_headers):
    """取单条交付物详情，含 markdown 正文。"""
    sid = client.post('/api/session', headers=auth_headers).json()['session_id']
    client.post(f'/api/generate/markdown?session_id={sid}', headers=auth_headers)
    list_item = client.get('/api/admin/deliverables', headers=admin_headers).json()[0]

    r = client.get(f"/api/admin/deliverables/{list_item['id']}", headers=admin_headers)
    assert r.status_code == 200
    detail = r.json()
    assert 'markdown' in detail
    assert len(detail['markdown']) > 0
