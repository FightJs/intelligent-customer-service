"""OpenRouter 图生视频客户端（异步：submit → poll → download）。

接口：POST /api/v1/videos，GET /api/v1/videos/{id}，GET .../content
与 DashScopeVideoClient 同一 VideoClient 协议。
"""
from __future__ import annotations

import asyncio
import base64
import mimetypes
import os
from pathlib import Path
from typing import Any

import httpx

from media.dashscope_video import VideoClientError

DEFAULT_BASE_URL = 'https://openrouter.ai/api/v1'
DEFAULT_POLL_INTERVAL_SEC = 10.0
DEFAULT_TIMEOUT_SEC = 300.0

TERMINAL_SUCCESS = {'completed'}
TERMINAL_FAILURE = {'failed', 'cancelled', 'expired'}


class OpenRouterVideoError(VideoClientError):
    """兼容 F4 skill 对 VideoClientError 的捕获。"""


def load_image_data_uri(image_path: Path) -> str:
    if not image_path.is_file():
        raise OpenRouterVideoError(f'首帧图不存在: {image_path}', retryable=False)
    mime, _ = mimetypes.guess_type(image_path.name)
    mime = mime or 'image/png'
    data = base64.b64encode(image_path.read_bytes()).decode('ascii')
    return f'data:{mime};base64,{data}'


def map_resolution(resolution: str) -> str:
    """720P → 720p，兼容 OpenRouter。"""
    return (resolution or '720P').strip().lower()


class OpenRouterVideoClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        poll_interval_sec: float | None = None,
        timeout_sec: float | None = None,
    ):
        self.api_key = api_key if api_key is not None else os.getenv('OPENROUTER_API_KEY', '')
        self.base_url = (base_url or os.getenv('OPENROUTER_BASE_URL') or DEFAULT_BASE_URL).rstrip('/')
        self._http = http_client
        self._owns_http = http_client is None
        self.poll_interval_sec = (
            poll_interval_sec
            if poll_interval_sec is not None
            else float(os.getenv('VIDEO_POLL_INTERVAL_SEC', DEFAULT_POLL_INTERVAL_SEC))
        )
        self.timeout_sec = (
            timeout_sec
            if timeout_sec is not None
            else float(os.getenv('VIDEO_TIMEOUT_SEC', DEFAULT_TIMEOUT_SEC))
        )

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                trust_env=False,
                timeout=httpx.Timeout(60.0, connect=10.0),
            )
        return self._http

    async def aclose(self) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()
            self._http = None

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise OpenRouterVideoError('缺少 OPENROUTER_API_KEY', retryable=False)
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-Title': 'intelligent-customer-service',
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
        payload: dict[str, Any] = {
            'model': model,
            'prompt': prompt,
            'duration': int(duration_sec),
            'resolution': map_resolution(resolution),
            'frame_images': [
                {
                    'type': 'image_url',
                    'image_url': {'url': img_url},
                    'frame_type': 'first_frame',
                }
            ],
        }
        url = f'{self.base_url}/videos'
        try:
            resp = await self._client().post(url, headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            raise OpenRouterVideoError(f'提交视频任务网络错误: {exc}') from exc

        try:
            body = resp.json()
        except ValueError:
            body = {'raw_text': resp.text}
        if resp.status_code >= 400:
            raise OpenRouterVideoError(
                f'提交视频任务失败 HTTP {resp.status_code}: {body}',
                retryable=resp.status_code >= 500 or resp.status_code == 429,
            )
        job_id = body.get('id')
        if not job_id:
            raise OpenRouterVideoError(f'提交响应缺少 job id: {body}')
        return str(job_id)

    async def wait_task(self, task_id: str, *, timeout_sec: float | None = None):
        budget = timeout_sec if timeout_sec is not None else self.timeout_sec
        url = f'{self.base_url}/videos/{task_id}'
        headers = {'Authorization': f'Bearer {self.api_key}'}
        deadline = asyncio.get_event_loop().time() + budget

        while True:
            try:
                resp = await self._client().get(url, headers=headers)
            except httpx.HTTPError as exc:
                raise OpenRouterVideoError(f'查询视频任务网络错误: {exc}') from exc

            try:
                body = resp.json()
            except ValueError:
                body = {'raw_text': resp.text}
            if resp.status_code >= 400:
                raise OpenRouterVideoError(
                    f'查询视频任务失败 HTTP {resp.status_code}: {body}',
                    retryable=resp.status_code >= 500 or resp.status_code == 429,
                )

            status = str(body.get('status') or '').lower()
            urls = body.get('unsigned_urls') or []
            content_url = urls[0] if urls else f'{self.base_url}/videos/{task_id}/content?index=0'

            class _R:
                pass

            result = _R()
            result.task_id = task_id
            result.status = status.upper()
            result.video_url = content_url if status in TERMINAL_SUCCESS else None
            result.message = body.get('error')
            result.raw = body

            if status in TERMINAL_SUCCESS:
                return result
            if status in TERMINAL_FAILURE:
                raise OpenRouterVideoError(
                    result.message or f'视频任务失败: {status}',
                    retryable=False,
                )
            if asyncio.get_event_loop().time() + self.poll_interval_sec > deadline:
                raise OpenRouterVideoError(f'视频任务超时（>{budget:.0f}s）: {task_id}', retryable=True)
            await asyncio.sleep(self.poll_interval_sec)

    async def download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        headers = {'Authorization': f'Bearer {self.api_key}'} if self.api_key else {}
        try:
            async with self._client().stream(
                'GET', url, headers=headers, follow_redirects=True
            ) as resp:
                if resp.status_code >= 400:
                    raise OpenRouterVideoError(f'下载视频失败 HTTP {resp.status_code}')
                tmp = dest.with_suffix(dest.suffix + '.part')
                with tmp.open('wb') as fh:
                    async for chunk in resp.aiter_bytes():
                        fh.write(chunk)
                tmp.replace(dest)
        except httpx.HTTPError as exc:
            raise OpenRouterVideoError(f'下载视频网络错误: {exc}') from exc
        return dest
