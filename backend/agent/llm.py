"""Anthropic 兼容 LLM client 封装。

模型厂商由环境变量决定；图片理解要求所配置模型支持视觉输入。
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

from anthropic import Anthropic, AsyncAnthropic
from dotenv import load_dotenv
import httpx

load_dotenv()

LLM_API_KEY = os.getenv('LLM_API_KEY', '')
LLM_BASE_URL = os.getenv('LLM_BASE_URL', '')
LLM_MODEL = os.getenv('LLM_MODEL', '')
LLM_TEMPERATURE = 0.3

logger = logging.getLogger(__name__)
_async_client: AsyncAnthropic | None = None


def _validate_config() -> None:
    missing = [
        name
        for name, value in (
            ('LLM_API_KEY', LLM_API_KEY),
            ('LLM_BASE_URL', LLM_BASE_URL),
            ('LLM_MODEL', LLM_MODEL),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            '缺少 LLM 配置：' + ', '.join(missing)
        )


@lru_cache(maxsize=1)
def get_client() -> Anthropic:
    """获取同步 Anthropic 兼容 client（绕过本地代理）。"""
    _validate_config()
    http_client = httpx.Client(
        trust_env=False,
        timeout=httpx.Timeout(60.0, connect=10.0),
    )
    return Anthropic(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        http_client=http_client,
    )


def _create_async_client() -> AsyncAnthropic:
    """创建异步 Anthropic 兼容 client。"""
    _validate_config()
    http_client = httpx.AsyncClient(
        trust_env=False,
        timeout=httpx.Timeout(60.0, connect=10.0),
    )
    return AsyncAnthropic(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        http_client=http_client,
    )


def get_async_client() -> AsyncAnthropic:
    """获取应用生命周期内共享的异步 client，复用 HTTP 连接池。"""
    global _async_client
    if _async_client is None:
        _async_client = _create_async_client()
    return _async_client


async def close_clients() -> None:
    """应用退出时释放已创建的同步与异步 LLM 连接。"""
    global _async_client

    async_client = _async_client
    _async_client = None
    if async_client is not None:
        try:
            await async_client.close()
        except Exception:
            logger.warning('failed to close async LLM client', exc_info=True)

    if get_client.cache_info().currsize:
        sync_client = get_client()
        get_client.cache_clear()
        try:
            sync_client.close()
        except Exception:
            logger.warning('failed to close sync LLM client', exc_info=True)
