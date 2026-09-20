"""对话内微意图：确定性规则层。

只做文本/schema 匹配与基于当前题的写入，不跑 LLM。
复杂表达仍交给 agent loop 的 tool-use 循环。
"""
from __future__ import annotations

import re

from agent import flow
from agent.tools import ToolEvent, execute_tool
from survey.models import StudioFormState
from survey.schema_def import FieldDef

SKIP_INTENT_RE = re.compile(
    r'^(?:我说)?(?:暂时)?(?:没有|没了|无|暂无|不需要|不用|无需|不想|不方便)'
    r'(?:再|了|啦|补充|提供|上传|回答|填写|图片|照片|参考图|内容|其他|特殊要求|其他要求)*[。！!]*$'
)

UNKNOWN_ANSWER_WORDS = ('不知道', '不清楚', '不确定', '随便', '没想好')
YES_WORDS = ('有', '有的', '是', '是的', '需要', '要', '已经有', '目前有')
NO_WORDS = ('没有', '没', '无', '不是', '不需要', '不要', '目前没有')

PRICE_NUMBER_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?)\s*(万|千|[wk])?',
    re.IGNORECASE,
)
PRICE_RANGE_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?)\s*(万|千|[wk])?\s*'
    r'(?:-|~|～|—|至|到)\s*'
    r'(\d+(?:\.\d+)?)\s*(万|千|[wk])?',
    re.IGNORECASE,
)
URL_PATTERN = re.compile(r'https?://[^\s，。；]+', re.IGNORECASE)

UNKNOWN_EQUIPMENT_ANSWERS = frozenset({
    '不知道',
    '不清楚',
    '不记得',
    '不认识',
    '不知道型号',
    '不清楚型号',
    '不记得型号',
    '不认识型号',
    '不知道具体型号',
    '不清楚具体型号',
})

ADVICE_MARKERS = (
    '我建议', '建议您', '推荐您', '可以考虑', '优化方案',
    '设备方案', '预算方案', '灯光方案', '设计方案',
    '应该', '最好', '更适合', '不妨', '原因是', '这是因为',
)

# 用户明显在问方案/FAQ/转人工，而不是回答当前采集题
OFF_TOPIC_MARKERS = (
    '推荐', '帮我选', '怎么选', '用什么灯', '用什么设备', '用什么相机',
    '怎么办', '怎么设计', '帮我设计', '帮我配', '出个方案', '有没有方案',
    '大概多少钱', '怎么收费', '收费标准', '报价', '转人工', '人工客服',
    '你是谁', '你是机器人', '介绍一下你们', '效果图怎么做',
)

TOPIC_CORRECTION_LEAD = '这个我们信息收齐后会一起出方案。'


def compact_text(text: str) -> str:
    return re.sub(r'[\s，,。！？!?；;]', '', text.strip())


def is_skip_intent(text: str) -> bool:
    return bool(SKIP_INTENT_RE.fullmatch(compact_text(text)))


def is_unknown_answer(text: str) -> bool:
    compact = compact_text(text)
    return any(word in compact for word in UNKNOWN_ANSWER_WORDS)


def parse_yes_no(text: str) -> str | None:
    compact = compact_text(text)
    if compact in NO_WORDS or re.fullmatch(r'(?:没有|不需要|不要)(?:的|了|啊|呀)?', compact):
        return 'no'
    if compact in YES_WORDS or re.fullmatch(r'(?:有|需要|要)(?:的|了|啊|呀)?', compact):
        return 'yes'
    return None


def _scaled_price(number: str, unit: str | None) -> float:
    value = float(number)
    normalized_unit = (unit or '').lower()
    if normalized_unit in {'万', 'w'}:
        return value * 10_000
    if normalized_unit in {'千', 'k'}:
        return value * 1_000
    return value


def looks_like_price_answer(text: str) -> bool:
    normalized = text.strip()
    if any(word in normalized for word in ('没想好', '不确定', '不知道', '还没定')):
        return False
    if re.fullmatch(r'\d+(?:\.\d+)?\s*(?:元|块|人民币)?', normalized):
        return True
    if PRICE_RANGE_PATTERN.search(normalized):
        return True
    if re.search(r'(?:价格带|客单价|商品价格|价格).{0,8}\d', normalized):
        return True
    return re.search(
        r'\d+(?:\.\d+)?\s*(?:元|块|人民币|万|千|[wk])',
        normalized,
        re.IGNORECASE,
    ) is not None


def price_band_from_text(text: str) -> str | None:
    """把明确且落在单一档位的商品价格确定性归类。"""
    range_match = PRICE_RANGE_PATTERN.search(text)
    if range_match is not None:
        number1, unit1, number2, unit2 = range_match.groups()
        amounts = [
            _scaled_price(number1, unit1),
            _scaled_price(number2, unit2),
        ]
    else:
        context = text
        keyword_positions = [
            position
            for keyword in ('价格带', '客单价', '商品价格', '价格')
            if (position := text.find(keyword)) >= 0
        ]
        if keyword_positions:
            context = text[min(keyword_positions):]
        amounts = [
            _scaled_price(number, unit)
            for number, unit in PRICE_NUMBER_PATTERN.findall(context)
        ]

    if not amounts:
        return None
    lower = min(amounts[:2])
    upper = max(amounts[:2])

    if upper < 100:
        return 'low'
    if lower >= 500 and upper <= 2_000:
        return 'high'
    if lower >= 100 and lower < 500 and upper <= 500:
        return 'mid'
    if lower > 2_000:
        return 'ultra'
    return None


def extract_url(text: str) -> str | None:
    match = URL_PATTERN.search(text)
    return match.group(0) if match else None


def is_unknown_equipment_inventory(text: str) -> bool:
    normalized = text.strip().rstrip('。！!？?，,')
    return normalized in UNKNOWN_EQUIPMENT_ANSWERS


def match_choice_single(field: FieldDef, text: str) -> str | None:
    compact = compact_text(text)
    options = field.options or []
    option_values = {option.value for option in options}
    value = next(
        (
            option.value
            for option in options
            if compact == re.sub(r'\s', '', option.label)
        ),
        None,
    )
    if value is None and {'yes', 'no'} <= option_values:
        value = parse_yes_no(text)
    return value


def match_choice_multi(field: FieldDef, text: str) -> list[str] | None:
    if is_unknown_answer(text):
        return None
    matched = [
        option.value
        for option in (field.options or [])
        if option.label in text
    ]
    if matched:
        return matched
    answer = text.strip()
    return [answer] if answer and len(answer) <= 80 else None


def looks_like_current_answer(
    section_id: str,
    field: FieldDef,
    text: str,
) -> bool:
    """粗判用户这句话是否像在回答当前题，避免把有效答案当成跑偏。"""
    compact = compact_text(text)
    if not compact:
        return False
    if field.skippable and is_skip_intent(text):
        return True
    if field.type == 'choice-single':
        return match_choice_single(field, text) is not None
    if field.type == 'choice-multi':
        return match_choice_multi(field, text) is not None
    if field.type == 'image':
        return '[图片' in text or '上传' in text or '照片' in text
    if field.type == 'table':
        return len(text) >= 4
    if field.type == 'dimension':
        return bool(re.search(r'\d', text))
    if section_id == 'industry' and field.id in {'price_band', 'price_range_raw'}:
        return looks_like_price_answer(text)
    if section_id == 'benchmark' and extract_url(text):
        return True
    # text 题：有实质内容就先当有效回答，跑偏交给 LLM 与回复侧收敛
    return len(compact) >= 2 and not any(marker in text for marker in OFF_TOPIC_MARKERS)


def is_user_off_topic(user_message: str, state: StudioFormState) -> bool:
    """用户明显在问方案/FAQ，且不像在回答当前采集题。"""
    text = (user_message or '').strip()
    if not text or len(text) > 200:
        return False
    current = flow.next_question_field(state)
    if current is None:
        return False
    if not any(marker in text for marker in OFF_TOPIC_MARKERS):
        return False
    return not looks_like_current_answer(current[0], current[1], text)


def apply_deterministic_price_range(
    state: StudioFormState,
    user_message: str,
) -> list[ToolEvent]:
    current = flow.next_question_field(state)
    asks_price_band = (
        current is not None
        and current[0] == 'industry'
        and current[1].id == 'price_band'
    )
    mentions_price_band = any(
        keyword in user_message
        for keyword in ('价格带', '客单价', '商品价格')
    )
    if not (asks_price_band or mentions_price_band):
        return []
    if '预算' in user_message and not mentions_price_band:
        return []
    if not looks_like_price_answer(user_message):
        return []

    band = price_band_from_text(user_message)
    if band is None:
        return []

    updates = [
        {
            'section_id': 'industry',
            'field_id': 'price_range_raw',
            'value': user_message.strip(),
            'confirmed': True,
        },
        {
            'section_id': 'industry',
            'field_id': 'price_band',
            'value': band,
            'confirmed': True,
        },
    ]
    events: list[ToolEvent] = []
    for update in updates:
        _, ok = execute_tool('fill_fields', {'updates': [update]}, state)
        if ok:
            field_id = update['field_id']
            events.append(ToolEvent(
                kind='fill',
                section_id='industry',
                field_id=field_id,
                value=state.sections['industry'].fields[field_id].value,
            ))
    return events


def apply_deterministic_reference_link(
    state: StudioFormState,
    user_message: str,
) -> list[ToolEvent]:
    """在对标模块中确定性保留用户粘贴的直播间链接。"""
    current = flow.next_question_field(state)
    if current is None or current[0] != 'benchmark':
        return []
    link = extract_url(user_message)
    if link is None:
        return []
    update = {
        'section_id': 'benchmark',
        'field_id': 'reference_link',
        'value': link,
        'confirmed': True,
    }
    _, ok = execute_tool('fill_fields', {'updates': [update]}, state)
    if not ok:
        return []
    return [ToolEvent(
        kind='fill',
        section_id='benchmark',
        field_id='reference_link',
        value=link,
    )]


def skip_unknown_equipment_inventory(
    state: StudioFormState,
    user_message: str,
) -> list[ToolEvent]:
    """用户明确不知道设备型号时，结束文字题并紧接着询问设备图片。"""
    current = flow.next_question_field(state)
    if current is None or (current[0], current[1].id) != ('equipment', 'inventory'):
        return []
    if not is_unknown_equipment_inventory(user_message):
        return []
    skipped, _ = flow.skip_field(state, 'equipment', 'inventory')
    if not skipped:
        return []
    return [ToolEvent(
        kind='skip',
        section_id='equipment',
        field_id='inventory',
    )]


def apply_deterministic_current_answer(
    state: StudioFormState,
    user_message: str,
) -> list[ToolEvent]:
    """优先处理明确的自然回答，避免简单答案依赖模型猜工具参数。"""
    current = flow.next_question_field(state)
    if current is None:
        return []

    section_id, field = current
    answer = user_message.strip()
    if not compact_text(answer):
        return []

    if field.skippable and is_skip_intent(answer):
        ok, _ = flow.skip_field(state, section_id, field.id)
        if ok:
            return [ToolEvent(
                kind='skip',
                section_id=section_id,
                field_id=field.id,
            )]

    if field.type == 'choice-single':
        value = match_choice_single(field, answer)
        if value is None:
            return []
        _, ok = execute_tool(
            'fill_fields',
            {'updates': [{
                'section_id': section_id,
                'field_id': field.id,
                'value': value,
            }]},
            state,
        )
        if not ok:
            return []
        return [ToolEvent(
            kind='fill',
            section_id=section_id,
            field_id=field.id,
            value=state.sections[section_id].fields[field.id].value,
        )]

    if field.type == 'choice-multi':
        value = match_choice_multi(field, answer)
        if not value:
            return []
        _, ok = execute_tool(
            'fill_fields',
            {'updates': [{
                'section_id': section_id,
                'field_id': field.id,
                'value': value,
            }]},
            state,
        )
        if not ok:
            return []
        return [ToolEvent(
            kind='fill',
            section_id=section_id,
            field_id=field.id,
            value=state.sections[section_id].fields[field.id].value,
        )]

    return []
