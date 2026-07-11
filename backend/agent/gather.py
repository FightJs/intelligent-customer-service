"""会话开场白生成。

run_turn/run_turn_stream 已移到 loop.py（agent tool use 循环）。
本文件只保留 initial_greeting。
"""
from __future__ import annotations

from agent.llm import get_client, LLM_MODEL
from survey.models import StudioFormState


def initial_greeting(state: StudioFormState) -> str:
    """生成开场白。"""
    client = get_client()
    resp = client.messages.create(
        model=LLM_MODEL,
        max_tokens=200,
        thinking={'type': 'disabled'},
        messages=[{'role': 'user', 'content': '你好'}],
        system=(
            '你是直播间搭建顾问。这是会话开始，请简短自我介绍'
            '（1 句话），然后问第一个问题：客户品牌名。保持亲切自然。'
        ),
    )
    for block in resp.content:
        if block.type == 'text' and block.text:
            return block.text.strip()
    return '您好！我是直播间搭建顾问，请问您的品牌名是？'
