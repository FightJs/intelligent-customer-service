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
    assert any(u['username'] == 'alice' for u in users)
    # list_users 不含 password_hash
    assert all('password_hash' not in u for u in users)


def test_delivery_crud(tmp_path, monkeypatch):
    """交付物增查：create + list + get。"""
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'test.db')
    db.init_db()

    uid = db.create_user('bob', 'hashed_pw', role='user')
    sid = db.create_session(uid, {})

    did = db.create_delivery(sid, uid, '某品牌', '# 方案\n内容')
    assert did > 0

    items = db.list_deliveries()
    assert len(items) == 1
    assert items[0]['customer_name'] == '某品牌'
    assert items[0]['owner_username'] == 'bob'
    assert 'markdown' not in items[0]  # 列表不含正文

    detail = db.get_delivery(did)
    assert detail['markdown'] == '# 方案\n内容'

    # 按 user 筛选
    filtered = db.list_deliveries(user_id=uid)
    assert len(filtered) == 1
    filtered_empty = db.list_deliveries(user_id=999)
    assert len(filtered_empty) == 0


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