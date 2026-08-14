"""store/uploads.py 测试。"""
import base64
import io

import pytest
from PIL import Image

import store.uploads as uploads
from store.uploads import (
    UploadError,
    image_to_data_uri,
    resolve_image,
    save_upload,
)


def make_png_data_uri(width: int = 10, height: int = 10) -> str:
    """生成一张合法的小 PNG data URI（跨测试文件共用）。"""
    img = Image.new('RGB', (width, height), (200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


@pytest.fixture
def uploads_root(tmp_path, monkeypatch):
    """把落盘根目录重定向到临时目录。"""
    monkeypatch.setattr(uploads, 'UPLOADS_ROOT', tmp_path)
    return tmp_path


def test_save_upload_persists_and_resolves(uploads_root):
    saved = save_upload('sess1', make_png_data_uri())
    assert saved.id.startswith('sess1/')
    assert saved.path.is_file()
    assert resolve_image(saved.id) == saved.path


def test_save_upload_rejects_bad_mime(uploads_root):
    with pytest.raises(UploadError):
        save_upload('sess1', 'data:image/svg+xml;base64,PHN2Zy8+')


def test_save_upload_rejects_corrupt_data(uploads_root):
    with pytest.raises(UploadError):
        save_upload('sess1', 'data:image/png;base64,bm90LWEtcG5n')


def test_save_upload_rejects_oversize(uploads_root):
    with pytest.raises(UploadError):
        save_upload('sess1', 'data:image/png;base64,' + 'A' * (uploads.MAX_B64_LEN + 1))


def test_save_upload_resizes_long_edge(uploads_root):
    saved = save_upload('sess1', make_png_data_uri(width=2000, height=1000))
    with Image.open(saved.path) as img:
        assert max(img.size) == uploads.MAX_EDGE


def test_resolve_image_rejects_traversal_and_missing(uploads_root):
    assert resolve_image('../etc/x.png') is None
    assert resolve_image('sess1/missing.jpg') is None
    assert resolve_image('not-an-id') is None


def test_image_to_data_uri_roundtrip(uploads_root):
    saved = save_upload('sess1', make_png_data_uri())
    uri = image_to_data_uri(saved.path)
    assert uri.startswith('data:image/png;base64,')
