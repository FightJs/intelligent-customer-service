"""pytest 全局 fixture。

测试不依赖外部 db 文件，自己保证 schema 就绪。
"""
import pytest

from store import db


@pytest.fixture(scope='session', autouse=True)
def _init_db():
    db.init_db()
    yield
