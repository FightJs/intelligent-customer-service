"""媒体客户端工厂：按 MEDIA_PROVIDER 选择实现。

- dashscope: 阿里百炼
- openrouter: OpenRouter Image/Video API
- openai_images: OpenAI 兼容 /v1/images/generations（NewAPI 中转等）
  视频仍走 openrouter/dashscope（用 VIDEO_PROVIDER 可单独覆盖）
"""
from __future__ import annotations

import os
from typing import Any


def media_provider() -> str:
    return (os.getenv('MEDIA_PROVIDER') or 'dashscope').strip().lower()


def video_provider() -> str:
    return (os.getenv('VIDEO_PROVIDER') or media_provider()).strip().lower()


def get_image_client() -> Any:
    provider = media_provider()
    if provider == 'openai_images':
        from media.openai_image import OpenAIImageClient

        return OpenAIImageClient()
    if provider == 'openrouter':
        from media.openrouter_image import OpenRouterImageClient

        return OpenRouterImageClient()
    from media.dashscope_image import DashScopeImageClient

    return DashScopeImageClient()


def get_video_client() -> Any:
    provider = video_provider()
    if provider in {'relay', 'dogzee', 'openai_images'}:
        from media.relay_video import RelayVideoClient

        return RelayVideoClient()
    if provider == 'openrouter':
        from media.openrouter_video import OpenRouterVideoClient

        return OpenRouterVideoClient()
    from media.dashscope_video import DashScopeVideoClient

    return DashScopeVideoClient()
