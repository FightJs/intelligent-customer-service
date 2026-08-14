"""会话开场白。"""
from __future__ import annotations

from survey.models import StudioFormState

FALLBACK_GREETING = (
    '嗨，欢迎来聊直播间搭建～我是小搭，'
    '会边聊边帮你把需求整理好。'
    '先跟我说说你的品牌叫什么、主要做哪类产品吧？'
)


def initial_greeting(state: StudioFormState) -> str:
    """返回固定开场白，创建会话不再等待一次无必要的 LLM 请求。"""
    _ = state
    return FALLBACK_GREETING
