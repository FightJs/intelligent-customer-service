"""OpenRouter 文生图客户端（POST /api/v1/images，同步返回 b64）。

与 DashScope 客户端同一 ImageClient 协议，便于 F3 skill 无感切换。
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

DEFAULT_BASE_URL = 'https://openrouter.ai/api/v1'
DEFAULT_TIMEOUT_SEC = 180.0


class OpenRouterImageError(ImageClientError):
    """兼容 F3 skill 对 ImageClientError 的捕获。"""


@dataclass
class _Pending:
    result: dict[str, Any] = field(default_factory=dict)


class OpenRouterImageClient:
    """submit/wait/download 适配：submit 实际同步出图，wait 直接回结果。"""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout_sec: float | None = None,
    ):
        self.api_key = api_key if api_key is not None else os.getenv('OPENROUTER_API_KEY', '')
        self.base_url = (base_url or os.getenv('OPENROUTER_BASE_URL') or DEFAULT_BASE_URL).rstrip('/')
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
            raise OpenRouterImageError('缺少 OPENROUTER_API_KEY', retryable=False)
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-Title': 'intelligent-customer-service',
        }

    def _size_to_params(self, size: str) -> dict[str, Any]:
        """把 1280*720 / 2K 等映射为 OpenRouter resolution/aspect_ratio。"""
        size = (size or '').strip().lower().replace('×', '*')
        tier_map = {'512': '512', '1k': '1K', '2k': '2K', '4k': '4K'}
        if size in tier_map:
            return {'resolution': tier_map[size]}
        if '*' in size or 'x' in size:
            raw = size.replace('x', '*')
            try:
                w_s, h_s = raw.split('*', 1)
                w, h = int(w_s), int(h_s)
            except ValueError:
                return {}
            if w <= 0 or h <= 0:
                return {}
            # 简化比例
            def _gcd(a: int, b: int) -> int:
                while b:
                    a, b = b, a % b
                return a or 1

            g = _gcd(w, h)
            return {'aspect_ratio': f'{w // g}:{h // g}', 'size': f'{w}x{h}'}
        return {}

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
            raise OpenRouterImageError('缺少 OPENROUTER_API_KEY', retryable=False)
        payload: dict[str, Any] = {
            'model': model,
            'prompt': prompt,
            'n': max(1, min(n, 1)),
        }
        payload.update(self._size_to_params(size))
        if seed is not None:
            payload['seed'] = seed
        url = f'{self.base_url}/images'
        try:
            resp = await self._client().post(url, headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            raise OpenRouterImageError(f'提交生图网络错误: {exc}') from exc

        try:
            body = resp.json()
        except ValueError:
            body = {'raw_text': resp.text}
        if resp.status_code >= 400:
            raise OpenRouterImageError(
                f'生图失败 HTTP {resp.status_code}: {body}',
                retryable=resp.status_code >= 500 or resp.status_code == 429,
            )

        data = body.get('data') or []
        if not data:
            raise OpenRouterImageError(f'生图响应缺少 data: {body!r:.200}')

        # 统一成 data URI，供 download 解码落盘
        urls: list[str] = []
        for item in data:
            b64 = item.get('b64_json')
            media = item.get('media_type') or 'image/png'
            if b64:
                urls.append(f'data:{media};base64,{b64}')
            elif item.get('url'):
                urls.append(str(item['url']))
        if not urls:
            raise OpenRouterImageError('生图成功但无图片内容')

        usage = body.get('usage') or {}
        task_id = f'or-img-{uuid.uuid4().hex[:12]}'
        self._pending[task_id] = _Pending(
            result={
                'image_urls': urls,
                'seed': seed,
                'cost_usd': usage.get('cost'),
            }
        )
        return task_id

    async def wait_task(self, task_id: str, *, timeout_sec: float | None = None):
        pending = self._pending.pop(task_id, None)
        if pending is None:
            raise OpenRouterImageError(f'未知生图任务: {task_id}', retryable=False)

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
                raise OpenRouterImageError(f'解码 data URI 失败: {exc}') from exc
            return dest

        try:
            async with self._client().stream('GET', url, follow_redirects=True) as resp:
                if resp.status_code >= 400:
                    raise OpenRouterImageError(f'下载图片失败 HTTP {resp.status_code}')
                tmp = dest.with_suffix(dest.suffix + '.part')
                with tmp.open('wb') as fh:
                    async for chunk in resp.aiter_bytes():
                        fh.write(chunk)
                tmp.replace(dest)
        except httpx.HTTPError as exc:
            raise OpenRouterImageError(f'下载图片网络错误: {exc}') from exc
        return dest
