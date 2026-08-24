"""会话开场白。"""
from __future__ import annotations

from agent.flow import next_question_field
from agent.question_copy import question_with_help
from survey.models import StudioFormState
from survey.schema_def import SECTION_BY_ID

GREETING_INTRO = (
    '嗨，欢迎来聊直播间搭建～我是小搭，'
    '会边聊边帮你把需求整理好。'
)


def initial_greeting(state: StudioFormState) -> str:
    """返回固定开场白，创建会话不再等待一次无必要的 LLM 请求。"""
    current = next_question_field(state)
    if current is None:
        return GREETING_INTRO
    section_id, field = current
    return (
        f'{GREETING_INTRO}\n\n'
        f'{question_with_help(field, skippable=(field.skippable or SECTION_BY_ID[section_id].skippable))}'
    )
