"""API 端点测试（用 TestClient，mock 掉 LLM 调用）。

所有业务端点都需要认证。测试用 register 拿 token，请求带 Authorization: Bearer。
所有涉及 create_session 的测试一律 mock 掉 initial_greeting，避免触发真实 LLM 调用
（CI 环境无 LLM_API_KEY，会报 anthropic 认证错误）。
"""
from unittest.mock import patch

import httpx
import pytest
from anthropic import APIStatusError
from fastapi.testclient import TestClient

from api.app import app
from store import db


def _insufficient_balance_error() -> APIStatusError:
    response = httpx.Response(
        402,
        request=httpx.Request('POST', 'https://llm.example.test/v1/messages'),
    )
    return APIStatusError(
        'Insufficient Balance',
        response=response,
        body={'error': {'message': 'Insufficient Balance'}},
    )


@pytest.fixture(scope='module')
def client(tmp_path_factory):
    """使用临时数据库运行 API 测试。"""
    original_path = db.DB_PATH
    test_dir = tmp_path_factory.mktemp(
        'api-database',
    )
    db.DB_PATH = test_dir / 'test.db'

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        db.DB_PATH = original_path


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


def test_create_session_falls_back_when_llm_balance_is_insufficient(client, auth_headers):
    from agent.gather import initial_greeting

    with patch('api.app.initial_greeting', new=initial_greeting):
        with patch('agent.gather.get_client') as get_client:
            get_client.return_value.messages.create.side_effect = _insufficient_balance_error()
            with TestClient(app, raise_server_exceptions=False) as degraded_client:
                r = degraded_client.post('/api/session', headers=auth_headers)

    assert r.status_code == 200
    assert r.json()['greeting'] == '您好！我是直播间搭建顾问，请问您的品牌名是？'


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


def test_chat_returns_clear_503_when_llm_balance_is_insufficient(client, auth_headers):
    sid = client.post('/api/session', headers=auth_headers).json()['session_id']
    with patch('api.app.run_agent', side_effect=_insufficient_balance_error()):
        with TestClient(app, raise_server_exceptions=False) as degraded_client:
            r = degraded_client.post(
                '/api/chat',
                json={'session_id': sid, 'message': '你好'},
                headers=auth_headers,
            )

    assert r.status_code == 503
    assert r.json()['detail'] == 'LLM 服务余额不足，请联系管理员充值后重试。'


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


def test_generate_markdown_does_not_persist_delivery(
    client,
    auth_headers,
    admin_headers,
):
    """普通生成接口不能让订单提前出现在后台。"""
    session_id = client.post(
        '/api/session',
        headers=auth_headers,
    ).json()['session_id']

    generated = client.post(
        (
            '/api/generate/markdown'
            f'?session_id={session_id}'
        ),
        headers=auth_headers,
    )

    assert generated.status_code == 200

    result = client.get(
        '/api/admin/deliverables',
        headers=admin_headers,
    )

    assert result.status_code == 200
    assert not any(
        item['session_id'] == session_id
        for item in result.json()['items']
    )


def test_submit_order_rejects_incomplete_form(
    client,
    auth_headers,
):
    """必填信息未完成时不能发送订单。"""
    session_id = client.post(
        '/api/session',
        headers=auth_headers,
    ).json()['session_id']

    response = client.post(
        '/api/orders',
        json={
            'session_id': session_id,
        },
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert (
        response.json()['detail']
        == '必填信息尚未采集完成'
    )


def test_submit_order_persists_once(
    client,
    auth_headers,
    admin_headers,
):
    """订单发送后进入后台，重复发送不会新增记录。"""
    session_id = client.post(
        '/api/session',
        headers=auth_headers,
    ).json()['session_id']

    with patch(
        'api.app.form_complete',
        return_value=True,
    ):
        first = client.post(
            '/api/orders',
            json={
                'session_id': session_id,
            },
            headers=auth_headers,
        )

        second = client.post(
            '/api/orders',
            json={
                'session_id': session_id,
            },
            headers=auth_headers,
        )

    assert first.status_code == 200
    assert first.json()['sent'] is True
    assert (
        first.json()['message']
        == '订单发送成功'
    )

    assert second.status_code == 200
    assert (
        second.json()['delivery_id']
        == first.json()['delivery_id']
    )

    result = client.get(
        '/api/admin/deliverables',
        headers=admin_headers,
    )

    matching = [
        item
        for item in result.json()['items']
        if item['session_id'] == session_id
    ]

    assert len(matching) == 1


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
    body = r.json()
    assert {'items', 'total', 'page', 'size'} <= body.keys()
    assert any(u['username'] == 'admin' and u['role'] == 'admin' for u in body['items'])


def test_admin_users_search_sort_pagination(client, admin_headers):
    """users 端点支持 search/sort/order/page/size 参数。"""
    # 搜索 admin
    r = client.get('/api/admin/users?search=admin', headers=admin_headers)
    assert r.status_code == 200
    assert r.json()['total'] == 1

    # 分页：size=1
    r = client.get('/api/admin/users?size=1&page=1&sort_by=id&order=asc', headers=admin_headers)
    body = r.json()
    assert body['size'] == 1
    assert len(body['items']) == 1
    assert body['items'][0]['id'] == 1  # id 最小的

    # 排序：username desc
    r = client.get('/api/admin/users?sort_by=username&order=desc', headers=admin_headers)
    names = [u['username'] for u in r.json()['items']]
    assert names == sorted(names, reverse=True)


def test_admin_deliverables_list(client, admin_headers):
    r = client.get('/api/admin/deliverables', headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert {'items', 'total', 'page', 'size'} <= body.keys()


def test_admin_deliverables_search_and_filter(client, auth_headers, admin_headers):
    """deliveries 端点支持 search 与 user_id 筛选。"""
    sid = client.post('/api/session', headers=auth_headers).json()['session_id']
    with patch(
        'api.app.form_complete',
        return_value=True,
    ):
        response = client.post(
            '/api/orders',
            json={
                'session_id': sid,
            },
            headers=auth_headers,
        )

    assert response.status_code == 200

    # search 匹配 owner（admin 用户的交付物）
    r = client.get('/api/admin/deliverables', headers=admin_headers)
    owner = r.json()['items'][0]['owner_username']

    r = client.get(f'/api/admin/deliverables?search={owner}', headers=admin_headers)
    assert r.json()['total'] >= 1

    # user_id 筛选
    uid = r.json()['items'][0]['user_id']
    r = client.get(f'/api/admin/deliverables?user_id={uid}', headers=admin_headers)
    assert all(d['user_id'] == uid for d in r.json()['items'])


def test_admin_get_deliverable_detail(client, admin_headers, auth_headers):
    """取单条交付物详情，含 markdown 正文。"""
    sid = client.post('/api/session', headers=auth_headers).json()['session_id']
    with patch(
        'api.app.form_complete',
        return_value=True,
    ):
        response = client.post(
            '/api/orders',
            json={
                'session_id': sid,
            },
            headers=auth_headers,
        )

    assert response.status_code == 200
    list_item = client.get('/api/admin/deliverables', headers=admin_headers).json()['items'][0]

    r = client.get(f"/api/admin/deliverables/{list_item['id']}", headers=admin_headers)
    assert r.status_code == 200
    detail = r.json()
    assert 'markdown' in detail
    assert len(detail['markdown']) > 0


def test_admin_users_returns_global_admin_count(
    client,
    admin_headers,
):
    """admin_count 不受搜索和分页影响。"""
    import secrets

    username = (
        'count-user-'
        + secrets.token_hex(4)
    )

    created = client.post(
        '/api/admin/users',
        json={
            'username': username,
            'password': 'pass123456',
            'role': 'user',
        },
        headers=admin_headers,
    )

    assert created.status_code == 201

    response = client.get(
        (
            '/api/admin/users'
            f'?search={username}'
            '&page=1'
            '&size=1'
        ),
        headers=admin_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body['total'] == 1
    assert len(body['items']) == 1
    assert body['admin_count'] == db.count_admins()


def test_admin_can_create_user(
    client,
    admin_headers,
):
    """管理员可以创建用户，响应不返回密码哈希。"""
    import secrets

    username = (
        'created-user-'
        + secrets.token_hex(4)
    )

    response = client.post(
        '/api/admin/users',
        json={
            'username': username,
            'password': 'pass123456',
            'role': 'user',
        },
        headers=admin_headers,
    )

    assert response.status_code == 201

    body = response.json()

    assert body['username'] == username
    assert body['role'] == 'user'
    assert body['delivery_count'] == 0
    assert 'password_hash' not in body

    duplicate = client.post(
        '/api/admin/users',
        json={
            'username': username,
            'password': 'pass123456',
            'role': 'user',
        },
        headers=admin_headers,
    )

    assert duplicate.status_code == 409


def test_admin_get_user_includes_delivery_count(
    client,
    admin_headers,
):
    """用户详情包含交付物数量。"""
    import secrets

    username = (
        'detail-api-user-'
        + secrets.token_hex(4)
    )

    created = client.post(
        '/api/admin/users',
        json={
            'username': username,
            'password': 'pass123456',
            'role': 'user',
        },
        headers=admin_headers,
    )

    user_id = created.json()['id']
    session_id = db.create_session(
        user_id,
        {},
    )

    db.create_delivery(
        session_id,
        user_id,
        '客户一',
        '# 方案一',
    )
    db.create_delivery(
        session_id,
        user_id,
        '客户二',
        '# 方案二',
    )

    response = client.get(
        f'/api/admin/users/{user_id}',
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()['delivery_count'] == 2
    assert 'password_hash' not in response.json()


def test_admin_can_update_user(
    client,
    admin_headers,
):
    """管理员可以修改用户名和重置密码。"""
    import secrets

    old_username = (
        'old-api-user-'
        + secrets.token_hex(4)
    )
    new_username = (
        'new-api-user-'
        + secrets.token_hex(4)
    )

    created = client.post(
        '/api/admin/users',
        json={
            'username': old_username,
            'password': 'oldpass123',
            'role': 'user',
        },
        headers=admin_headers,
    )

    user_id = created.json()['id']

    response = client.patch(
        f'/api/admin/users/{user_id}',
        json={
            'username': new_username,
            'password': 'newpass123',
            'role': 'user',
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()['username'] == new_username
    assert 'password_hash' not in response.json()

    old_login = client.post(
        '/api/auth/login',
        json={
            'username': old_username,
            'password': 'oldpass123',
        },
    )
    assert old_login.status_code == 401

    new_login = client.post(
        '/api/auth/login',
        json={
            'username': new_username,
            'password': 'newpass123',
        },
    )
    assert new_login.status_code == 200


def test_admin_cannot_demote_last_admin(
    client,
    admin_headers,
):
    """系统最后一个管理员不能被降级。"""
    admin_user = db.get_user_by_username(
        'admin',
    )

    assert admin_user is not None
    assert db.count_admins() == 1

    response = client.patch(
        f"/api/admin/users/{admin_user['id']}",
        json={
            'role': 'user',
        },
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert (
        response.json()['detail']
        == '不能降级系统最后一个管理员'
    )


def test_admin_cannot_delete_self(
    client,
    admin_headers,
):
    """管理员不能删除当前登录的自己。"""
    admin_user = db.get_user_by_username(
        'admin',
    )

    assert admin_user is not None

    response = client.delete(
        f"/api/admin/users/{admin_user['id']}",
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert (
        response.json()['detail']
        == '不能删除当前登录的管理员'
    )


def test_admin_delete_user_removes_related_data(
    client,
    admin_headers,
):
    """通过 API 删除用户时同步删除关联数据。"""
    import secrets

    username = (
        'delete-api-user-'
        + secrets.token_hex(4)
    )

    created = client.post(
        '/api/admin/users',
        json={
            'username': username,
            'password': 'pass123456',
            'role': 'user',
        },
        headers=admin_headers,
    )

    user_id = created.json()['id']
    session_id = db.create_session(
        user_id,
        {},
    )

    db.add_message(
        session_id,
        'user',
        '测试消息',
    )
    delivery_id = db.create_delivery(
        session_id,
        user_id,
        '测试客户',
        '# 测试交付物',
    )

    response = client.delete(
        f'/api/admin/users/{user_id}',
        headers=admin_headers,
    )

    assert response.status_code == 204
    assert db.get_user_by_id(user_id) is None
    assert db.get_session(session_id) is None
    assert db.get_messages(session_id) == []
    assert db.get_delivery(delivery_id) is None


def test_admin_can_update_and_delete_delivery(
    client,
    admin_headers,
):
    """管理员可以修改和删除交付物。"""
    import secrets

    username = (
        'delivery-api-user-'
        + secrets.token_hex(4)
    )
    user_id = db.create_user(
        username,
        'hash',
        role='user',
    )
    session_id = db.create_session(
        user_id,
        {},
    )
    delivery_id = db.create_delivery(
        session_id,
        user_id,
        '修改前客户',
        '# 修改前内容',
    )

    updated = client.patch(
        (
            '/api/admin/deliverables/'
            f'{delivery_id}'
        ),
        json={
            'customer_name': '修改后客户',
            'markdown': '# 修改后内容',
        },
        headers=admin_headers,
    )

    assert updated.status_code == 200
    assert (
        updated.json()['customer_name']
        == '修改后客户'
    )
    assert (
        updated.json()['markdown']
        == '# 修改后内容'
    )

    deleted = client.delete(
        (
            '/api/admin/deliverables/'
            f'{delivery_id}'
        ),
        headers=admin_headers,
    )

    assert deleted.status_code == 204
    assert db.get_delivery(delivery_id) is None

    missing = client.delete(
        (
            '/api/admin/deliverables/'
            f'{delivery_id}'
        ),
        headers=admin_headers,
    )

    assert missing.status_code == 404


def test_normal_user_cannot_mutate_admin_resources(
    client,
    auth_headers,
):
    """普通用户不能调用后台管理写接口。"""
    create_response = client.post(
        '/api/admin/users',
        json={
            'username': 'forbidden-user',
            'password': 'pass123456',
            'role': 'user',
        },
        headers=auth_headers,
    )

    assert create_response.status_code == 403

    update_response = client.patch(
        '/api/admin/users/1',
        json={
            'username': 'forbidden-name',
        },
        headers=auth_headers,
    )

    assert update_response.status_code == 403

    delete_response = client.delete(
        '/api/admin/deliverables/999999',
        headers=auth_headers,
    )

    assert delete_response.status_code == 403


def test_admin_mutation_validation(
    client,
    admin_headers,
):
    """后台写接口拒绝无效参数。"""
    import secrets

    username = (
        'validation-user-'
        + secrets.token_hex(4)
    )

    short_password = client.post(
        '/api/admin/users',
        json={
            'username': username,
            'password': '123',
            'role': 'user',
        },
        headers=admin_headers,
    )

    assert short_password.status_code == 400

    created = client.post(
        '/api/admin/users',
        json={
            'username': username,
            'password': 'pass123456',
            'role': 'user',
        },
        headers=admin_headers,
    )

    user_id = created.json()['id']

    empty_update = client.patch(
        f'/api/admin/users/{user_id}',
        json={},
        headers=admin_headers,
    )

    assert empty_update.status_code == 400