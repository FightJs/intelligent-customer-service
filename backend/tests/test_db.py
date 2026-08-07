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


def test_list_users_returns_global_admin_count(
    tmp_path,
    monkeypatch,
):
    """管理员数量是全局统计，不受搜索和分页影响。"""
    monkeypatch.setattr(
        db,
        'DB_PATH',
        tmp_path / 'test.db',
    )
    db.init_db()

    db.create_user(
        'admin-one',
        'hash',
        role='admin',
    )
    db.create_user(
        'admin-two',
        'hash',
        role='admin',
    )
    db.create_user(
        'visible-user',
        'hash',
        role='user',
    )

    result = db.list_users(
        search='visible-user',
        page=1,
        size=1,
    )

    assert result['total'] == 1
    assert len(result['items']) == 1

    # 即使搜索结果只有普通用户，
    # 也应该返回数据库中全部管理员数量。
    assert result['admin_count'] == 2


def test_get_user_detail_includes_delivery_count(
    tmp_path,
    monkeypatch,
):
    """用户详情包含该用户的交付物总数。"""
    monkeypatch.setattr(
        db,
        'DB_PATH',
        tmp_path / 'test.db',
    )
    db.init_db()

    user_id = db.create_user(
        'detail-user',
        'hash',
        role='user',
    )
    session_id = db.create_session(
        user_id,
        {},
    )

    db.create_delivery(
        session_id,
        user_id,
        '客户甲',
        '# 方案一',
    )
    db.create_delivery(
        session_id,
        user_id,
        '客户乙',
        '# 方案二',
    )

    detail = db.get_user_detail(user_id)

    assert detail is not None
    assert detail['username'] == 'detail-user'
    assert detail['delivery_count'] == 2
    assert 'password_hash' not in detail


def test_update_user_updates_allowed_fields(
    tmp_path,
    monkeypatch,
):
    """管理员可以修改用户名、密码哈希和角色。"""
    monkeypatch.setattr(
        db,
        'DB_PATH',
        tmp_path / 'test.db',
    )
    db.init_db()

    user_id = db.create_user(
        'before-user',
        'old-hash',
        role='user',
    )

    updated = db.update_user(
        user_id,
        {
            'username': 'after-user',
            'password_hash': 'new-hash',
            'role': 'admin',
        },
    )

    assert updated is not None
    assert updated['username'] == 'after-user'
    assert updated['role'] == 'admin'
    assert 'password_hash' not in updated

    stored = db.get_user_by_id(user_id)

    assert stored is not None
    assert stored['password_hash'] == 'new-hash'


def test_delete_user_removes_related_data(
    tmp_path,
    monkeypatch,
):
    """删除用户时同步清理会话、消息和交付物。"""
    monkeypatch.setattr(
        db,
        'DB_PATH',
        tmp_path / 'test.db',
    )
    db.init_db()

    user_id = db.create_user(
        'delete-user',
        'hash',
        role='user',
    )
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

    deleted = db.delete_user(user_id)

    assert deleted is True
    assert db.get_user_by_id(user_id) is None
    assert db.get_session(session_id) is None
    assert db.get_messages(session_id) == []
    assert db.get_delivery(delivery_id) is None

    # 重复删除不存在的用户，应返回 False。
    assert db.delete_user(user_id) is False


def test_update_and_delete_delivery(
    tmp_path,
    monkeypatch,
):
    """管理员可以修改和删除交付物。"""
    monkeypatch.setattr(
        db,
        'DB_PATH',
        tmp_path / 'test.db',
    )
    db.init_db()

    user_id = db.create_user(
        'delivery-user',
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

    updated = db.update_delivery(
        delivery_id,
        {
            'customer_name': '修改后客户',
            'markdown': '# 修改后内容',
        },
    )

    assert updated is not None
    assert updated['customer_name'] == '修改后客户'
    assert updated['markdown'] == '# 修改后内容'

    deleted = db.delete_delivery(delivery_id)

    assert deleted is True
    assert db.get_delivery(delivery_id) is None

    # 重复删除不存在的交付物，应返回 False。
    assert db.delete_delivery(delivery_id) is False