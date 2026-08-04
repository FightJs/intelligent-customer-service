from store import db


def test_get_messages_returns_latest_in_chronological_order(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'test.db')
    db.init_db()

    session_id = db.create_session({})

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