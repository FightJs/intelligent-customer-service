"""anthropic SDK client 封装。

通过 DeepSeek /anthropic 端点调用，面向 Anthropic 协议编程。
厂商可替换：改 base_url + key 即可。
"""
from __future__ import annotations

import os
from functools import lru_cache

from anthropic import Anthropic
from dotenv import load_dotenv
import httpx

load_dotenv()

LLM_API_KEY = os.getenv('LLM_API_KEY', '')
LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://api.deepseek.com/anthropic')
LLM_MODEL = os.getenv('LLM_MODEL', 'deepseek-v4-flash')


@lru_cache(maxsize=1)
def get_client() -> Anthropic:
    """获取 anthropic client（绕过本地代理）。"""
    http_client = httpx.Client(
        trust_env=False,
        timeout=httpx.Timeout(60.0, connect=10.0),
    )
    return Anthropic(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        http_client=http_client,
    )
