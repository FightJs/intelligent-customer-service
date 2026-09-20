"""DashScope 文生图异步客户端。

对接阿里百炼 image-generation 异步任务 API：
- 提交：POST /api/v1/services/aigc/text2image/image-synthesis
- 查询：GET  /api/v1/tasks/{task_id}

与 dashscope_video 同风格：不依赖 dashscope SDK，便于单测 mock。
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import httpx

DEFAULT_BASE_URL = 'https://dashscope.aliyuncs.com'
DEFAULT_POLL_INTERVAL_SEC = 2.0
DEFAULT_TIMEOUT_SEC = 180.0

TERMINAL_SUCCESS = {'SUCCEEDED'}
TERMINAL_FAILURE = {'FAILED', 'CANCELED', 'CANCELED_BY_USER'}

# 最小合法 PNG 头（8 字节）+ 少量数据，用于校验非空
PNG_MAGIC = b'\x89PNG\r\n\x1a\n'


class ImageClientError(Exception):
    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


@dataclass
class ImageTaskResult:
    task_id: str
    status: str
    image_urls: list[str] = field(default_factory=list)
    seed: int | None = None
    message: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class ImageClient(Protocol):
    """F3 skill 依赖的最小接口，便于注入 Fake。"""

    async def submit_t2i(
        self,
        *,
        model: str,
        prompt: str,
        seed: int | None = None,
        size: str = '1280*720',
        n: int = 1,
    ) -> str: ...

    async def wait_task(self, task_id: str, *, timeout_sec: float | None = None) -> ImageTaskResult: ...

    async def download(self, url: str, dest: Path) -> Path: ...


class DashScopeImageClient:
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
            else float(os.getenv('IMAGE_POLL_INTERVAL_SEC', DEFAULT_POLL_INTERVAL_SEC))
        )
        self.timeout_sec = (
            timeout_sec
            if timeout_sec is not None
            else float(os.getenv('IMAGE_TIMEOUT_SEC', DEFAULT_TIMEOUT_SEC))
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
            raise ImageClientError('缺少 DASHSCOPE_API_KEY', retryable=False)
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-DashScope-Async': 'enable',
        }

    async def submit_t2i(
        self,
        *,
        model: str,
        prompt: str,
        seed: int | None = None,
        size: str = '1280*720',
        n: int = 1,
    ) -> str:
        payload: dict[str, Any] = {
            'model': model,
            'input': {'prompt': prompt},
            'parameters': {
                'size': size,
                'n': n,
                'prompt_extend': True,
            },
        }
        if seed is not None:
            payload['parameters']['seed'] = seed
        url = f'{self.base_url}/api/v1/services/aigc/text2image/image-synthesis'
        try:
            resp = await self._client().post(url, headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            raise ImageClientError(f'提交生图任务网络错误: {exc}') from exc

        body = _safe_json(resp)
        if resp.status_code >= 400:
            raise ImageClientError(
                f'提交生图任务失败 HTTP {resp.status_code}: {body}',
                retryable=resp.status_code >= 500 or resp.status_code == 429,
            )
        task_id = (body.get('output') or {}).get('task_id')
        if not task_id:
            raise ImageClientError(f'提交响应缺少 task_id: {body}')
        return str(task_id)

    async def wait_task(self, task_id: str, *, timeout_sec: float | None = None) -> ImageTaskResult:
        budget = timeout_sec if timeout_sec is not None else self.timeout_sec
        url = f'{self.base_url}/api/v1/tasks/{task_id}'
        headers = {'Authorization': f'Bearer {self.api_key}'}
        deadline = asyncio.get_event_loop().time() + budget

        while True:
            try:
                resp = await self._client().get(url, headers=headers)
            except httpx.HTTPError as exc:
                raise ImageClientError(f'查询生图任务网络错误: {exc}') from exc

            body = _safe_json(resp)
            if resp.status_code >= 400:
                raise ImageClientError(
                    f'查询生图任务失败 HTTP {resp.status_code}: {body}',
                    retryable=resp.status_code >= 500 or resp.status_code == 429,
                )

            output = body.get('output') or {}
            status = str(output.get('task_status') or '').upper()
            results = output.get('results') or []
            urls: list[str] = []
            seed: int | None = None
            for item in results:
                if not isinstance(item, dict):
                    continue
                url_val = item.get('url') or item.get('image_url')
                if url_val:
                    urls.append(str(url_val))
                if seed is None and item.get('seed') is not None:
                    try:
                        seed = int(item['seed'])
                    except (TypeError, ValueError):
                        seed = None
            if seed is None and output.get('seed') is not None:
                try:
                    seed = int(output['seed'])
                except (TypeError, ValueError):
                    seed = None

            result = ImageTaskResult(
                task_id=task_id,
                status=status,
                image_urls=urls,
                seed=seed,
                message=output.get('message'),
                raw=body,
            )
            if status in TERMINAL_SUCCESS:
                if not urls:
                    raise ImageClientError('任务成功但未返回 image url')
                return result
            if status in TERMINAL_FAILURE:
                raise ImageClientError(
                    result.message or f'生图任务失败: {status}',
                    retryable=False,
                )

            if asyncio.get_event_loop().time() + self.poll_interval_sec > deadline:
                raise ImageClientError(f'生图任务超时（>{budget:.0f}s）: {task_id}', retryable=True)
            await asyncio.sleep(self.poll_interval_sec)

    async def download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with self._client().stream('GET', url, follow_redirects=True) as resp:
                if resp.status_code >= 400:
                    raise ImageClientError(f'下载图片失败 HTTP {resp.status_code}', retryable=True)
                tmp = dest.with_suffix(dest.suffix + '.part')
                with tmp.open('wb') as fh:
                    async for chunk in resp.aiter_bytes():
                        fh.write(chunk)
                tmp.replace(dest)
        except httpx.HTTPError as exc:
            raise ImageClientError(f'下载图片网络错误: {exc}') from exc
        return dest


def _safe_json(resp: httpx.Response) -> dict[str, Any]:
    try:
        data = resp.json()
    except ValueError:
        return {'raw_text': resp.text}
    return data if isinstance(data, dict) else {'data': data}


def is_valid_png(path: Path, min_bytes: int = 100) -> bool:
    """非 0 字节且带 PNG 魔数（CI 假图同样适用）。"""
    if not path.is_file():
        return False
    size = path.stat().st_size
    if size < min_bytes:
        return False
    try:
        header = path.read_bytes()[:8]
    except OSError:
        return False
    return header == PNG_MAGIC
