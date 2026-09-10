"""Admin 知识库上传接口测试（mock 入库，不连 Qdrant）。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.app import app
from knowledge import service as knowledge_service
from store import db


@pytest.fixture(scope='module')
def client(tmp_path_factory):
    original_path = db.DB_PATH
    db.DB_PATH = tmp_path_factory.mktemp('kb-db') / 'test.db'
    try:
        with TestClient(app) as c:
            yield c
    finally:
        db.DB_PATH = original_path
        # 清理测试上传目录
        root = knowledge_service.KNOWLEDGE_UPLOAD_ROOT
        if root.exists():
            for p in root.glob('*.pdf'):
                p.unlink(missing_ok=True)


@pytest.fixture()
def admin_token(client: TestClient) -> str:
    username = 'kb_admin'
    password = 'kb-pass-123'
    if db.get_user_by_username(username) is None:
        from agent.auth import hash_password

        db.create_user(username, hash_password(password), role='admin')
    resp = client.post('/api/auth/login', json={'username': username, 'password': password})
    assert resp.status_code == 200, resp.text
    return resp.json()['token']


def _auth(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def test_upload_requires_auth(client: TestClient):
    resp = client.post(
        '/api/admin/knowledge/upload',
        files={'file': ('a.pdf', b'%PDF-1.4', 'application/pdf')},
        data={'category': 'vertical'},
    )
    assert resp.status_code in (401, 403)


def test_upload_pdf_creates_pending_then_ready(client: TestClient, admin_token: str, tmp_path):
    with (
        patch.object(knowledge_service, 'run_pdf_ingest') as run,
        patch.object(
            knowledge_service,
            'extract_pdf_text',
            create=True,
        ),
    ):
        run.return_value = {
            'id': 1,
            'status': 'ready',
            'chunks': 3,
            'source': 'x#12345678',
            'note': '入库完成',
        }
        resp = client.post(
            '/api/admin/knowledge/upload',
            headers=_auth(admin_token),
            files={'file': ('女装布光.pdf', b'%PDF-1.4 x', 'application/pdf')},
            data={'category': 'vertical', 'industry': 'women', 'scene': '布光'},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body['filename'] == '女装布光.pdf'
    assert body['category'] == 'vertical'
    assert body['id'].startswith('kb_')
    doc_id = int(body['id'].split('_', 1)[1])
    rec = db.get_knowledge_doc(doc_id)
    assert rec is not None
    assert rec['status'] in ('pending', 'embedding', 'ready')
    assert rec['industry'] == 'women'


def test_upload_rejects_non_pdf(client: TestClient, admin_token: str):
    resp = client.post(
        '/api/admin/knowledge/upload',
        headers=_auth(admin_token),
        files={'file': ('a.txt', b'hello', 'text/plain')},
        data={'category': 'vertical'},
    )
    assert resp.status_code == 400


def test_list_docs(client: TestClient, admin_token: str):
    db.create_knowledge_doc(
        filename='已有文档.pdf',
        category='vertical',
        status='ready',
        note='ok',
    )
    resp = client.get('/api/admin/knowledge/docs', headers=_auth(admin_token))
    assert resp.status_code == 200
    items = resp.json()['items']
    assert any(i['filename'] == '已有文档.pdf' for i in items)


def test_retry_missing_doc(client: TestClient, admin_token: str):
    resp = client.post('/api/admin/knowledge/docs/999999/retry', headers=_auth(admin_token))
    assert resp.status_code == 404
