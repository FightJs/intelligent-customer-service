"""DashScope 图生视频（i2v）异步客户端。

对接阿里百炼 video-synthesis 异步任务 API：
- 提交：POST /api/v1/services/aigc/video-generation/video-synthesis
- 查询：GET  /api/v1/tasks/{task_id}

不依赖 dashscope SDK，便于单测 mock 与代理环境统一走 httpx。
"""
from __future__ import annotations

import asyncio
import base64
import mimetypes
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import httpx

DEFAULT_BASE_URL = 'https://dashscope.aliyuncs.com'
DEFAULT_POLL_INTERVAL_SEC = 5.0
DEFAULT_TIMEOUT_SEC = 300.0

TERMINAL_SUCCESS = {'SUCCEEDED'}
TERMINAL_FAILURE = {'FAILED', 'CANCELED', 'CANCELED_BY_USER'}


class VideoClientError(Exception):
    """外部视频服务错误（提交失败/任务失败/下载失败）。"""

    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


@dataclass
class VideoTaskResult:
    task_id: str
    status: str
    video_url: str | None = None
    message: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class VideoClient(Protocol):
    """F4 skill 依赖的最小接口，便于注入 Fake。"""

    async def submit_i2v(
        self,
        *,
        model: str,
        prompt: str,
        image_path: Path,
        duration_sec: int,
        resolution: str,
    ) -> str: ...

    async def wait_task(self, task_id: str, *, timeout_sec: float | None = None) -> VideoTaskResult: ...

    async def download(self, url: str, dest: Path) -> Path: ...


def load_image_data_uri(image_path: Path) -> str:
    """本地首帧图 → data URI，供 DashScope i2v 输入。"""
    if not image_path.is_file():
        raise VideoClientError(f'首帧图不存在: {image_path}', retryable=False)
    mime, _ = mimetypes.guess_type(image_path.name)
    mime = mime or 'image/png'
    data = base64.b64encode(image_path.read_bytes()).decode('ascii')
    return f'data:{mime};base64,{data}'


class DashScopeVideoClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        poll_interval_sec: float | None = None,
        timeout_sec: float | None = None,
    ):
        self.api_key = api_key if api_key is not None else os.getenv('DASHSCOPE_API_KEY', '')
        self.base_url = (base_url or os.getenv('DASHSCOPE_BASE_URL') or DEFAULT_BASE_URL).rstrip('/')
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
            raise VideoClientError('缺少 DASHSCOPE_API_KEY', retryable=False)
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-DashScope-Async': 'enable',
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
            'input': {
                'prompt': prompt,
                'img_url': img_url,
            },
            'parameters': {
                'resolution': resolution,
                'duration': duration_sec,
                'prompt_extend': True,
            },
        }
        url = f'{self.base_url}/api/v1/services/aigc/video-generation/video-synthesis'
        try:
            resp = await self._client().post(url, headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            raise VideoClientError(f'提交视频任务网络错误: {exc}') from exc

        body = _safe_json(resp)
        if resp.status_code >= 400:
            raise VideoClientError(
                f'提交视频任务失败 HTTP {resp.status_code}: {body}',
                retryable=resp.status_code >= 500 or resp.status_code == 429,
            )
        task_id = (body.get('output') or {}).get('task_id')
        if not task_id:
            raise VideoClientError(f'提交响应缺少 task_id: {body}')
        return str(task_id)

    async def wait_task(self, task_id: str, *, timeout_sec: float | None = None) -> VideoTaskResult:
        budget = timeout_sec if timeout_sec is not None else self.timeout_sec
        url = f'{self.base_url}/api/v1/tasks/{task_id}'
        headers = {'Authorization': f'Bearer {self.api_key}'}
        deadline = asyncio.get_event_loop().time() + budget

        while True:
            try:
                resp = await self._client().get(url, headers=headers)
            except httpx.HTTPError as exc:
                raise VideoClientError(f'查询视频任务网络错误: {exc}') from exc

            body = _safe_json(resp)
            if resp.status_code >= 400:
                raise VideoClientError(
                    f'查询视频任务失败 HTTP {resp.status_code}: {body}',
                    retryable=resp.status_code >= 500 or resp.status_code == 429,
                )

            output = body.get('output') or {}
            status = str(output.get('task_status') or '').upper()
            result = VideoTaskResult(
                task_id=task_id,
                status=status,
                video_url=output.get('video_url') or output.get('url'),
                message=output.get('message'),
                raw=body,
            )
            if status in TERMINAL_SUCCESS:
                if not result.video_url:
                    raise VideoClientError('任务成功但未返回 video_url')
                return result
            if status in TERMINAL_FAILURE:
                raise VideoClientError(
                    result.message or f'视频任务失败: {status}',
                    retryable=False,
                )

            if asyncio.get_event_loop().time() + self.poll_interval_sec > deadline:
                raise VideoClientError(f'视频任务超时（>{budget:.0f}s）: {task_id}', retryable=True)
            await asyncio.sleep(self.poll_interval_sec)

    async def download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with self._client().stream('GET', url, follow_redirects=True) as resp:
                if resp.status_code >= 400:
                    raise VideoClientError(f'下载视频失败 HTTP {resp.status_code}', retryable=True)
                tmp = dest.with_suffix(dest.suffix + '.part')
                with tmp.open('wb') as fh:
                    async for chunk in resp.aiter_bytes():
                        fh.write(chunk)
                tmp.replace(dest)
        except httpx.HTTPError as exc:
            raise VideoClientError(f'下载视频网络错误: {exc}') from exc
        return dest


def _safe_json(resp: httpx.Response) -> dict[str, Any]:
    try:
        data = resp.json()
    except ValueError:
        return {'raw_text': resp.text}
    return data if isinstance(data, dict) else {'data': data}
