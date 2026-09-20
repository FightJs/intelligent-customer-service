"""OpenAI 兼容文生图客户端（POST /v1/images/generations）。

适配 NewAPI 等中转站：返回 data[0].b64_json。
与 ImageClient 协议对齐，供 F3 使用。
"""
from __future__ import annotations

import base64
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from media.dashscope_image import ImageClientError

DEFAULT_TIMEOUT_SEC = 180.0


class OpenAIImageError(ImageClientError):
    """兼容 F3 skill 对 ImageClientError 的捕获。"""


@dataclass
class _Pending:
    result: dict[str, Any] = field(default_factory=dict)


def _size_to_openai(size: str) -> str:
    """把 1280*720 / 2K 映射为 OpenAI 允许的 size（不支持则退回 1024x1024）。"""
    allowed = {
        '256x256', '512x512', '1024x1024', '1024x1536', '1536x1024',
        '1792x1024', '1024x1792', 'auto',
    }
    raw = (size or '').strip().lower().replace('×', 'x').replace('*', 'x')
    if raw in allowed:
        return raw
    if 'x' in raw:
        try:
            w_s, h_s = raw.split('x', 1)
            w, h = int(w_s), int(h_s)
        except ValueError:
            return '1024x1024'
        # 选最接近的合法档
        if w >= h:
            return '1536x1024' if w / max(h, 1) > 1.2 else '1024x1024'
        return '1024x1536' if h / max(w, 1) > 1.2 else '1024x1024'
    tier = {'512': '512x512', '1k': '1024x1024', '2k': '1536x1024', '4k': '1536x1024'}
    return tier.get(raw, '1024x1024')


class OpenAIImageClient:
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
            else (os.getenv('OPENAI_IMAGE_API_KEY') or os.getenv('OPENROUTER_API_KEY') or '')
        )
        self.base_url = (
            base_url
            or os.getenv('OPENAI_IMAGE_BASE_URL')
            or 'https://api.openai.com/v1'
        ).rstrip('/')
        self._http = http_client
        self._owns_http = http_client is None
        self.timeout_sec = (
            timeout_sec
            if timeout_sec is not None
            else float(os.getenv('IMAGE_TIMEOUT_SEC', DEFAULT_TIMEOUT_SEC))
        )
        self._pending: dict[str, _Pending] = {}

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
            raise OpenAIImageError('缺少 OPENAI_IMAGE_API_KEY', retryable=False)
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
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
        if not self.api_key:
            raise OpenAIImageError('缺少 OPENAI_IMAGE_API_KEY', retryable=False)
        payload: dict[str, Any] = {
            'model': model,
            'prompt': prompt,
            'n': 1,
            'size': _size_to_openai(size),
        }
        # seed 多数中转不认，忽略
        url = f'{self.base_url}/images/generations'
        try:
            resp = await self._client().post(url, headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            raise OpenAIImageError(f'生图网络错误: {exc}') from exc

        try:
            body = resp.json()
        except ValueError:
            body = {'raw_text': resp.text}
        if resp.status_code >= 400:
            raise OpenAIImageError(
                f'生图失败 HTTP {resp.status_code}: {body}',
                retryable=resp.status_code >= 500 or resp.status_code == 429,
            )

        data = body.get('data') or []
        if not data:
            raise OpenAIImageError(f'生图响应缺少 data: {body!r:.200}')

        urls: list[str] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            b64 = item.get('b64_json')
            url_val = item.get('url')
            if b64:
                urls.append(f'data:image/png;base64,{b64}')
            elif url_val:
                urls.append(str(url_val))
        if not urls:
            raise OpenAIImageError('生图成功但无图片内容')

        usage = body.get('usage') or {}
        task_id = f'oai-img-{uuid.uuid4().hex[:12]}'
        self._pending[task_id] = _Pending(
            result={
                'image_urls': urls,
                'seed': seed,
                'cost_hint': usage,
            }
        )
        return task_id

    async def wait_task(self, task_id: str, *, timeout_sec: float | None = None):
        pending = self._pending.pop(task_id, None)
        if pending is None:
            raise OpenAIImageError(f'未知生图任务: {task_id}', retryable=False)

        class _R:
            status = 'SUCCEEDED'
            image_urls = pending.result['image_urls']
            seed = pending.result.get('seed')
            message = None
            raw = pending.result

        return _R()

    async def download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if url.startswith('data:'):
            try:
                _, b64 = url.split(',', 1)
                dest.write_bytes(base64.b64decode(b64))
            except Exception as exc:
                raise OpenAIImageError(f'解码 data URI 失败: {exc}') from exc
            return dest
        try:
            async with self._client().stream('GET', url, follow_redirects=True) as resp:
                if resp.status_code >= 400:
                    raise OpenAIImageError(f'下载图片失败 HTTP {resp.status_code}')
                tmp = dest.with_suffix(dest.suffix + '.part')
                with tmp.open('wb') as fh:
                    async for chunk in resp.aiter_bytes():
                        fh.write(chunk)
                tmp.replace(dest)
        except httpx.HTTPError as exc:
            raise OpenAIImageError(f'下载图片网络错误: {exc}') from exc
        return dest
