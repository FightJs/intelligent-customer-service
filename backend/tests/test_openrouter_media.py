"""OpenRouter 图/视频客户端单测（mock httpx，不访问外网）。"""
from __future__ import annotations

import base64
from pathlib import Path

import pytest

from media.dashscope_image import ImageClientError
from media.dashscope_video import VideoClientError
from media.factory import get_image_client, get_video_client, media_provider
from media.openrouter_image import OpenRouterImageClient
from media.openrouter_video import OpenRouterVideoClient, map_resolution


class _Resp:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


async def test_openrouter_image_submit_download(tmp_path: Path, monkeypatch):
    png = b'\x89PNG\r\n\x1a\n' + b'0' * 200
    b64 = base64.b64encode(png).decode()

    async def _post(url, *, headers=None, json=None, timeout=None):
        assert url.endswith('/images')
        assert json['model'] == 'bytedance-seed/seedream-5-0-lite'
        assert json['seed'] == 7
        return _Resp(200, {'data': [{'b64_json': b64, 'media_type': 'image/png'}], 'usage': {'cost': 0.02}})

    client = OpenRouterImageClient(api_key='sk-or-test')
    monkeypatch.setattr(client, '_client', lambda: type('H', (), {'post': staticmethod(_post)})())
    task_id = await client.submit_t2i(
        model='bytedance-seed/seedream-5-0-lite',
        prompt='直播间',
        seed=7,
        size='1280*720',
    )
    result = await client.wait_task(task_id)
    assert result.image_urls[0].startswith('data:image/png;base64,')
    dest = tmp_path / 'a.png'
    await client.download(result.image_urls[0], dest)
    assert dest.read_bytes() == png


def test_openrouter_image_error_is_image_client_error():
    from media.openrouter_image import OpenRouterImageError

    assert issubclass(OpenRouterImageError, ImageClientError)


async def test_openrouter_video_submit_poll_download(tmp_path: Path, monkeypatch):
    img = tmp_path / 'front.png'
    img.write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * 100)

    calls = {'poll': 0}

    async def _post(url, *, headers=None, json=None, timeout=None):
        assert url.endswith('/videos')
        assert json['resolution'] == '720p'
        assert json['frame_images'][0]['frame_type'] == 'first_frame'
        return _Resp(202, {'id': 'job1', 'polling_url': 'https://openrouter.ai/api/v1/videos/job1', 'status': 'pending'})

    async def _get(url, *, headers=None, timeout=None):
        calls['poll'] += 1
        if calls['poll'] < 2:
            return _Resp(200, {'id': 'job1', 'status': 'in_progress'})
        return _Resp(
            200,
            {
                'id': 'job1',
                'status': 'completed',
                'unsigned_urls': ['https://openrouter.ai/api/v1/videos/job1/content?index=0'],
            },
        )

    class _StreamCM:
        def __init__(self, status_code=200):
            self.status_code = status_code

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def aiter_bytes(self):
            yield b'0' * 120_000

    class _H:
        async def post(self, url, **kw):
            return await _post(url, **kw)

        async def get(self, url, **kw):
            return await _get(url, **kw)

        def stream(self, method, url, **kw):
            return _StreamCM()

    client = OpenRouterVideoClient(api_key='sk-or-test', poll_interval_sec=0.01)
    monkeypatch.setattr(client, '_client', lambda: _H())

    task_id = await client.submit_i2v(
        model='alibaba/wan-3.0',
        prompt='orbit',
        image_path=img,
        duration_sec=8,
        resolution='720P',
    )
    assert task_id == 'job1'
    result = await client.wait_task(task_id, timeout_sec=5)
    assert result.video_url
    dest = tmp_path / 'out.mp4'
    await client.download(result.video_url, dest)
    assert dest.stat().st_size >= 100_000


def test_map_resolution():
    assert map_resolution('720P') == '720p'
    assert map_resolution('1080P') == '1080p'


def test_factory_switches_provider(monkeypatch):
    monkeypatch.setenv('MEDIA_PROVIDER', 'openrouter')
    monkeypatch.setenv('VIDEO_PROVIDER', 'openrouter')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'sk-or-x')
    assert media_provider() == 'openrouter'
    assert isinstance(get_image_client(), OpenRouterImageClient)
    assert isinstance(get_video_client(), OpenRouterVideoClient)

    monkeypatch.setenv('MEDIA_PROVIDER', 'dashscope')
    monkeypatch.setenv('VIDEO_PROVIDER', 'dashscope')
    from media.dashscope_image import DashScopeImageClient
    from media.dashscope_video import DashScopeVideoClient

    assert isinstance(get_image_client(), DashScopeImageClient)
    assert isinstance(get_video_client(), DashScopeVideoClient)

    monkeypatch.setenv('MEDIA_PROVIDER', 'openai_images')
    monkeypatch.setenv('VIDEO_PROVIDER', 'relay')
    monkeypatch.setenv('OPENAI_IMAGE_API_KEY', 'sk-x')
    monkeypatch.setenv('RELAY_VIDEO_API_KEY', 'sk-y')
    from media.openai_image import OpenAIImageClient
    from media.relay_video import RelayVideoClient

    assert isinstance(get_image_client(), OpenAIImageClient)
    assert isinstance(get_video_client(), RelayVideoClient)


def test_openrouter_video_error_is_video_client_error():
    from media.openrouter_video import OpenRouterVideoError

    assert issubclass(OpenRouterVideoError, VideoClientError)
