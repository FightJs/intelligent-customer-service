"""上传图片的落盘与解析。

图片 id 即相对路径：<session_id>/<img_id>.<ext>，
同时作为 ImageValue.value 的元素和 LLM 引用的标识。
"""
from __future__ import annotations

import base64
import binascii
import io
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

UPLOADS_ROOT = Path(__file__).resolve().parents[1] / 'data' / 'uploads'

MAX_EDGE = 1600                # 长边上限：控制 LLM token 与交付物体积
MAX_B64_LEN = 15 * 1024 * 1024  # base64 字符串长度上限（约 11MB 原图）

MIME_EXT = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/webp': 'webp',
    'image/gif': 'gif',
}

DATA_URI_RE = re.compile(r'^data:(?P<mime>[^;,]+);base64,(?P<data>.*)$', re.DOTALL)

_ID_RE = re.compile(r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+\.(png|jpg|webp|gif)$')
_SESSION_ID_RE = re.compile(r'^[a-zA-Z0-9_-]+$')


class UploadError(ValueError):
    """上传内容非法（格式/大小/数据损坏）。"""


@dataclass
class SavedImage:
    id: str      # '<session_id>/<img_id>.<ext>'
    path: Path
    mime: str


def is_data_uri(value: object) -> bool:
    return isinstance(value, str) and DATA_URI_RE.match(value) is not None


def save_upload(session_id: str, data_uri: str) -> SavedImage:
    """解析 data URI、缩放并落盘，返回 SavedImage。非法内容抛 UploadError。"""
    match = DATA_URI_RE.match(data_uri or '')
    if match is None:
        raise UploadError('不是合法的 data URI')

    mime = match.group('mime').lower()
    if mime not in MIME_EXT:
        raise UploadError(f'不支持的图片类型: {mime}')

    b64 = match.group('data')
    if len(b64) > MAX_B64_LEN:
        raise UploadError('图片超过大小上限')

    try:
        raw = base64.b64decode(b64)
        image = Image.open(io.BytesIO(raw))
        image.load()
    except (binascii.Error, OSError) as exc:
        raise UploadError(f'图片数据损坏: {exc}') from exc

    if max(image.size) > MAX_EDGE:
        image.thumbnail((MAX_EDGE, MAX_EDGE))

    session_dir = UPLOADS_ROOT / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    ext = MIME_EXT[mime]
    path = session_dir / f'{uuid.uuid4().hex[:12]}.{ext}'
    # 统一按原格式保存；动图 GIF 只保留首帧
    save_format = 'JPEG' if ext == 'jpg' else ext.upper()
    if save_format == 'JPEG' and image.mode in ('RGBA', 'P', 'LA'):
        image = image.convert('RGB')
    image.save(path, format=save_format)

    return SavedImage(id=f'{session_id}/{path.name}', path=path, mime=mime)


def resolve_image(image_id: str) -> Path | None:
    """把 ImageValue.value 里的 id 解析回磁盘路径；非法或不存在返回 None。"""
    if not isinstance(image_id, str) or _ID_RE.match(image_id) is None:
        return None
    path = UPLOADS_ROOT / image_id
    if not path.is_file():
        return None
    # 防路径穿越（正则已限制，双保险）
    if path.resolve().parent.parent != UPLOADS_ROOT.resolve():
        return None
    return path


def image_to_data_uri(path: Path) -> str:
    """读取落盘图片转回 data URI（markdown 交付物内嵌用）。"""
    ext = path.suffix.lstrip('.').lower()
    mime = {v: k for k, v in MIME_EXT.items()}[ext]
    data = base64.b64encode(path.read_bytes()).decode('ascii')
    return f'data:{mime};base64,{data}'


def delete_session_uploads(session_ids: list[str]) -> int:
    """删除指定会话的全部落盘图片，返回删除的会话目录数量。

    只接受单段安全 session_id，并验证目标目录直属 UPLOADS_ROOT，
    防止路径穿越或误删上传根目录。
    """
    root = UPLOADS_ROOT.resolve()
    deleted = 0

    for session_id in dict.fromkeys(session_ids):
        if _SESSION_ID_RE.fullmatch(session_id) is None:
            continue

        session_dir = (UPLOADS_ROOT / session_id).resolve()
        if session_dir.parent != root or not session_dir.is_dir():
            continue

        shutil.rmtree(session_dir)
        deleted += 1

    return deleted
