"""Dogzee / NewAPI 中转视频客户端。

该站把 e-video 挂在 OpenAI 兼容的 POST /v1/images/generations 上，
响应 data[0].url 为 mp4。同步返回，submit 时即拿到 URL。
"""
from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import Any

import httpx

from media.dashscope_video import VideoClientError

DEFAULT_TIMEOUT_SEC = 300.0


class RelayVideoError(VideoClientError):
    """兼容 F4 skill 对 VideoClientError 的捕获。"""


def load_image_data_uri(image_path: Path) -> str:
    if not image_path.is_file():
        raise RelayVideoError(f'首帧图不存在: {image_path}', retryable=False)
    mime, _ = mimetypes.guess_type(image_path.name)
    mime = mime or 'image/png'
    data = base64.b64encode(image_path.read_bytes()).decode('ascii')
    return f'data:{mime};base64,{data}'


class RelayVideoClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout_sec: float | None = None,
    ):
        self.api_key = (
            api_key
            if api_key is not None
            else (os.getenv('RELAY_VIDEO_API_KEY') or os.getenv('OPENAI_IMAGE_API_KEY') or '')
        )
        self.base_url = (
            base_url
            or os.getenv('RELAY_VIDEO_BASE_URL')
            or os.getenv('OPENAI_IMAGE_BASE_URL')
            or 'https://ergouzi.life/v1'
        ).rstrip('/')
        self._http = http_client
        self._owns_http = http_client is None
        self.timeout_sec = (
            timeout_sec
            if timeout_sec is not None
            else float(os.getenv('VIDEO_TIMEOUT_SEC', DEFAULT_TIMEOUT_SEC))
        )
        self._pending: dict[str, dict[str, Any]] = {}

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                trust_env=False,
                timeout=httpx.Timeout(self.timeout_sec, connect=10.0),
            )
        return self._http

    async def aclose(self) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()
            self._http = None

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RelayVideoError('缺少 RELAY_VIDEO_API_KEY', retryable=False)
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

    async def submit_i2v(
        self,
        *,
        model: str,
        prompt: str,
        image_path: Path,
        duration_sec: int,
        resolution: str,
    ) -> str:
        img_url = load_image_data_uri(image_path)
        payload = {
            'model': model,
            'prompt': prompt,
            'image': img_url,
            'n': 1,
        }
        # 部分实现会读 duration/resolution，透传无害
        if duration_sec:
            payload['duration'] = int(duration_sec)
        if resolution:
            # e-video 只接受 720p / 1080p
            payload['resolution'] = str(resolution).strip().lower()

        url = f'{self.base_url}/images/generations'
        try:
            resp = await self._client().post(url, headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            raise RelayVideoError(f'提交视频任务网络错误: {exc}') from exc

        try:
            body = resp.json()
        except ValueError:
            body = {'raw_text': resp.text}
        if resp.status_code >= 400:
            raise RelayVideoError(
                f'提交视频任务失败 HTTP {resp.status_code}: {body}',
                retryable=resp.status_code >= 500 or resp.status_code == 429,
            )

        data = body.get('data') or []
        if not data:
            raise RelayVideoError(f'视频响应缺少 data: {body!r:.200}')
        item = data[0] if isinstance(data[0], dict) else {}
        video_url = item.get('url') or (item.get('b64_json') and 'b64')
        if not video_url:
            raise RelayVideoError(f'视频响应无 url: {body!r:.200}')

        task_id = f'relay-vid-{id(body)}'
        self._pending[task_id] = {
            'video_url': video_url,
            'model': model,
            'duration_sec': duration_sec,
            'resolution': resolution,
            'raw': body,
        }
        return task_id

    async def wait_task(self, task_id: str, *, timeout_sec: float | None = None):
        pending = self._pending.pop(task_id, None)
        if pending is None:
            raise RelayVideoError(f'未知视频任务: {task_id}', retryable=False)

        class _R:
            status = 'SUCCEEDED'
            video_url = pending['video_url']
            message = None
            raw = pending

        return _R()

    async def download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if url == 'b64':
            raise RelayVideoError('响应为 b64 但未实现解码路径', retryable=False)
        try:
            async with self._client().stream('GET', url, follow_redirects=True) as resp:
                if resp.status_code >= 400:
                    raise RelayVideoError(f'下载视频失败 HTTP {resp.status_code}')
                tmp = dest.with_suffix(dest.suffix + '.part')
                with tmp.open('wb') as fh:
                    async for chunk in resp.aiter_bytes():
                        fh.write(chunk)
                tmp.replace(dest)
        except httpx.HTTPError as exc:
            raise RelayVideoError(f'下载视频网络错误: {exc}') from exc
        return dest
