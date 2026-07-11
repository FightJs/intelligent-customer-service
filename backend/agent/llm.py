"""LLM client 封装（DeepSeek V4-Flash，OpenAI 兼容接口）。

处理：
- 从 .env 读配置
- 代理绕过（国内 API 不走代理，否则 SSL 断开）
- 统一 client 实例
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
import httpx
from openai import OpenAI

load_dotenv()  # 读 backend/.env

LLM_API_KEY = os.getenv('LLM_API_KEY', '')
LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://api.deepseek.com')
LLM_MODEL = os.getenv('LLM_MODEL', 'deepseek-v4-flash')

# 国内 API 需绕过本地代理（Clash 等会干扰 TLS）
_LLM_HOST = LLM_BASE_URL.replace('https://', '').replace('http://', '').rstrip('/')


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    """获取 OpenAI 兼容 client（绕过代理）。"""
    http_client = httpx.Client(
        trust_env=False,  # 不读环境变量代理配置
        timeout=httpx.Timeout(60.0, connect=10.0),
    )
    return OpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        http_client=http_client,
    )
