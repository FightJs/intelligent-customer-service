"""pytest 全局 fixture。

测试不依赖外部 db 文件，自己保证 schema 就绪。
"""
import pytest

from store import db


@pytest.fixture(scope='session', autouse=True)
def _init_db(tmp_path_factory):
    original_path = db.DB_PATH
    db.DB_PATH = tmp_path_factory.mktemp('session-db') / 'ics-test.db'
    db.init_db()
    yield
    db.DB_PATH = original_path
