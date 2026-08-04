from store import db


def test_get_messages_returns_latest_in_chronological_order(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'test.db')
    db.init_db()

    user_id = db.create_user('tester', 'hash_placeholder', role='user')
    session_id = db.create_session(user_id, {})

    for index in range(5):
        db.add_message(
            session_id,
            'user',
            f'message-{index}',
        )

    messages = db.get_messages(session_id, limit=3)

    assert [message['content'] for message in messages] == [
        'message-2',
        'message-3',
        'message-4',
    ]


def test_user_crud(tmp_path, monkeypatch):
    """用户增查：create + get_by_username + get_by_id + list。"""
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'test.db')
    db.init_db()

    uid = db.create_user('alice', 'hashed_pw', role='user')
    assert uid > 0

    by_name = db.get_user_by_username('alice')
    assert by_name is not None
    assert by_name['username'] == 'alice'
    assert by_name['role'] == 'user'
    assert by_name['password_hash'] == 'hashed_pw'

    by_id = db.get_user_by_id(uid)
    assert by_id['username'] == 'alice'

    users = db.list_users()
    assert any(u['username'] == 'alice' for u in users['items'])
    # list_users 不含 password_hash
    assert all('password_hash' not in u for u in users['items'])


def test_delivery_crud(tmp_path, monkeypatch):
    """交付物增查：create + list + get。"""
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'test.db')
    db.init_db()

    uid = db.create_user('bob', 'hashed_pw', role='user')
    sid = db.create_session(uid, {})

    did = db.create_delivery(sid, uid, '某品牌', '# 方案\n内容')
    assert did > 0

    result = db.list_deliveries()
    assert result['total'] == 1
    items = result['items']
    assert len(items) == 1
    assert items[0]['customer_name'] == '某品牌'
    assert items[0]['owner_username'] == 'bob'
    assert 'markdown' not in items[0]  # 列表不含正文

    detail = db.get_delivery(did)
    assert detail['markdown'] == '# 方案\n内容'

    # 按 user 筛选
    filtered = db.list_deliveries(user_id=uid)
    assert filtered['total'] == 1
    assert len(filtered['items']) == 1
    filtered_empty = db.list_deliveries(user_id=999)
    assert filtered_empty['total'] == 0


def test_session_user_binding(tmp_path, monkeypatch):
    """get_session 返回结构含 user_id 和 form_state。"""
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'test.db')
    db.init_db()

    uid = db.create_user('carol', 'hashed_pw', role='user')
    sid = db.create_session(uid, {'currentSectionId': 'customer'})

    rec = db.get_session(sid)
    assert rec is not None
    assert rec['user_id'] == uid
    assert rec['form_state'] == {'currentSectionId': 'customer'}


def test_list_users_search_sort_pagination(tmp_path, monkeypatch):
    """list_users 支持搜索/排序/分页，返回 {items, total, page, size}。"""
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'test.db')
    db.init_db()

    for name in ['alice', 'bob', 'alex', 'amy', 'brian']:
        db.create_user(name, 'x', role='user')

    # 搜索 a 开头的用户名（alice/alex/amy）
    res = db.list_users(search='al')
    assert res['total'] == 2
    assert {u['username'] for u in res['items']} == {'alice', 'alex'}

    # 按 username 倒序
    res = db.list_users(sort_by='username', order='desc', size=10)
    names = [u['username'] for u in res['items']]
    assert names == sorted(names, reverse=True)

    # 分页：每页 2 条，取第 2 页
    res = db.list_users(sort_by='id', order='asc', page=2, size=2)
    assert res['total'] == 5
    assert res['page'] == 2
    assert res['size'] == 2
    assert len(res['items']) == 2
    # 第 2 页应是 id 第 3、4 个用户
    assert res['items'][0]['id'] == 3

    # 非法 sort_by 回退 id，不报错
    res = db.list_users(sort_by='password_hash; DROP TABLE users--')
    assert res['total'] == 5


def test_list_deliveries_search_sort_pagination(tmp_path, monkeypatch):
    """list_deliveries 支持用户筛选/搜索/排序/分页。"""
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'test.db')
    db.init_db()

    uid_a = db.create_user('ownerA', 'x')
    uid_b = db.create_user('ownerB', 'x')
    sid = db.create_session(uid_a, {})
    # 3 条属于 ownerA，1 条属于 ownerB
    db.create_delivery(sid, uid_a, '客户甲', 'm1')
    db.create_delivery(sid, uid_a, '客户乙', 'm2')
    db.create_delivery(sid, uid_a, '客户丙', 'm3')
    sid_b = db.create_session(uid_b, {})
    db.create_delivery(sid_b, uid_b, '客户甲B', 'm4')

    # 按 customer_name 搜索「甲」
    res = db.list_deliveries(search='甲')
    assert res['total'] == 2

    # 按 owner_username 搜索 ownerB
    res = db.list_deliveries(search='ownerB')
    assert res['total'] == 1
    assert res['items'][0]['owner_username'] == 'ownerB'

    # 按 user_id 筛选 + 分页
    res = db.list_deliveries(user_id=uid_a, page=1, size=2, sort_by='id', order='asc')
    assert res['total'] == 3
    assert len(res['items']) == 2
    assert res['items'][0]['customer_name'] == '客户甲'

    # 第 2 页剩 1 条
    res = db.list_deliveries(user_id=uid_a, page=2, size=2, sort_by='id', order='asc')
    assert len(res['items']) == 1
    assert res['items'][0]['customer_name'] == '客户丙'