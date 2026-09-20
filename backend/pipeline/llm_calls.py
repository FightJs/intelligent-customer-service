"""F2 的 LLM 调用：检索意图拆解 + 方案组合。"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from agent.llm import LLM_MODEL, LLM_TEMPERATURE, get_async_client
from knowledge.models import KnowledgeHit
from pipeline.models import PlanDraft, RequirementBrief, RetrievalIntent
from pipeline.normalize import industry_label

logger = logging.getLogger(__name__)

# 粗估：DeepSeek 兼容端点中文约 0.002 元 / 1k tokens（仅审计用）
_COST_PER_1K_TOKENS = 0.002

_JSON_FENCE = re.compile(r'```(?:json)?\s*([\s\S]*?)```', re.IGNORECASE)


def estimate_cost(prompt_chars: int, completion_chars: int) -> float:
    tokens = (prompt_chars + completion_chars) / 2.0
    return round(tokens / 1000.0 * _COST_PER_1K_TOKENS, 4)


def extract_json(text: str) -> Any:
    """从模型输出中解析 JSON 对象或数组。"""
    candidate = text.strip()
    fence = _JSON_FENCE.search(candidate)
    if fence:
        candidate = fence.group(1).strip()
    # 容忍前后多余说明文字：优先对象，其次数组
    start_obj = candidate.find('{')
    end_obj = candidate.rfind('}')
    start_arr = candidate.find('[')
    end_arr = candidate.rfind(']')
    if start_obj >= 0 and end_obj > start_obj and (start_arr < 0 or start_obj < start_arr):
        candidate = candidate[start_obj:end_obj + 1]
    elif start_arr >= 0 and end_arr > start_arr:
        candidate = candidate[start_arr:end_arr + 1]
    return json.loads(candidate)


async def call_llm_json(system: str, user: str) -> Any:
    """默认 LLM 实现：调用 Anthropic 兼容端点并解析 JSON。"""
    client = get_async_client()
    resp = await client.messages.create(
        model=LLM_MODEL,
        max_tokens=4000,
        temperature=LLM_TEMPERATURE,
        system=system,
        messages=[{'role': 'user', 'content': user}],
    )
    parts = []
    for block in resp.content:
        if getattr(block, 'type', '') == 'text':
            parts.append(block.text)
    raw = '\n'.join(parts).strip()
    if not raw:
        raise RuntimeError('LLM 返回空内容')
    return extract_json(raw)


def build_decompose_prompt(brief: RequirementBrief) -> tuple[str, str]:
    system = (
        '你是直播间搭建方案的检索策略师。'
        '根据用户需求摘要，输出 3-6 条检索意图，用于从知识库召回设备、搭建方案与垂类知识。'
        '只输出 JSON 数组，不要解释。'
    )
    user = json.dumps(
        {
            'task': '输出检索意图列表',
            'industry': brief.industry,
            'industry_label': industry_label(brief.industry),
            'subcategory': brief.subcategory,
            'room_size': brief.room_size,
            'area_band': brief.area_band,
            'budget_total': brief.budget_total,
            'budget_equip': brief.budget_equip,
            'price_band': brief.price_band,
            'positioning': brief.positioning,
            'live_type': brief.live_type,
            'goal_core': brief.goal_core,
            'product_main': brief.product_main,
            'product_keywords': brief.product_keywords,
            'host_count': brief.host_count,
            'host_movement': brief.host_movement,
            'schema': [
                {
                    'collection': 'setup_schemes|equipment_specs|vertical_knowledge',
                    'query': '中文检索词',
                    'filters': '可含 industry/room_size/budget_level/category/scene',
                }
            ],
            'rules': [
                '至少 1 条 setup_schemes',
                '至少 1 条 equipment_specs',
                '至少 1 条 vertical_knowledge',
                'filters.industry 使用 women/men/beauty 等英文枚举或 all',
            ],
        },
        ensure_ascii=False,
    )
    return system, user


def parse_decompose_payload(payload: dict[str, Any] | list[Any]) -> list[RetrievalIntent]:
    raw_items: list[Any]
    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        raw_items = payload.get('intents') or payload.get('queries') or payload.get('items') or []
    else:
        raw_items = []

    intents: list[RetrievalIntent] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        collection = str(item.get('collection') or '').strip()
        query = str(item.get('query') or '').strip()
        if collection not in {'setup_schemes', 'equipment_specs', 'vertical_knowledge'}:
            continue
        if not query:
            continue
        filters = item.get('filters')
        if not isinstance(filters, dict):
            filters = {}
        intents.append(RetrievalIntent(collection=collection, query=query, filters=filters))
    return intents


def fallback_intents(brief: RequirementBrief) -> list[RetrievalIntent]:
    """LLM 失败或输出无效时的确定性检索意图。"""
    industry = brief.industry
    return [
        RetrievalIntent(
            collection='setup_schemes',
            query=f'{industry_label(industry)} {brief.area_band or brief.room_size} 搭建方案',
            filters={
                'industry': industry,
                'room_size': brief.room_size,
                'budget_level': brief.budget_total,
            },
        ),
        RetrievalIntent(
            collection='equipment_specs',
            query=f'{industry_label(industry)} 直播间 灯光 相机 设备',
            filters={
                'industry': [industry, 'all'],
                'room_size': brief.room_size,
            },
        ),
        RetrievalIntent(
            collection='vertical_knowledge',
            query=f'{industry_label(industry)} 直播间 背景 布光 商品质感',
            filters={
                'industry': industry,
                'scene': '背景',
            },
        ),
    ]


def build_compose_prompt(
    brief: RequirementBrief,
    hits: list[KnowledgeHit],
) -> tuple[str, str]:
    hit_payload = [
        {
            'collection': hit.collection,
            'id': hit.id,
            'score': hit.score,
            'payload': hit.payload,
        }
        for hit in hits
    ]
    system = (
        '你是资深直播间搭建顾问。根据用户需求与知识库命中，生成可审计的中文搭建方案。'
        '严格输出一个 JSON 对象，不要输出 Markdown 解释。\n'
        '约束：\n'
        '1. 设备优先引用 knowledge_id；无法对应知识库时 is_custom=true，但 model/brand 仍写具体在售型号\n'
        '2. 已有设备保留在清单并标注 already_owned=true，不要虚构型号\n'
        '3. 三档套餐命名为 性价比/进阶/高配，total_range 使用 1.2-1.6w 这种万元区间；mode 为 rent|buy|mixed\n'
        '4. setup_steps 至少 3 条，中文步骤句\n'
        '5. scene_card 供后续生图使用，必须完整\n'
        '6. layout 必须非空；layout.zones 说明分区；meta.layout_scale 写面积/层高/供电建议\n'
        '7. must_buy=true 表示必买/必租核心设备；specs 写功率/色温/传感器等关键参数\n'
        '8. rental_channels 给出全国性租赁平台或本地器材城渠道（不要编造具体小店名）\n'
        '9. vertical_notes 给出该垂类布光/陈列/色温的专业要点\n'
    )
    schema_hint = {
        'summary': '一句话方案定位',
        'meta': {'layout_scale': '建议面积 20-35㎡；净高≥2.8m；供电单相 4kW'},
        'layout': {
            'zones': [{'name': '主播区', 'notes': '...'}],
            'lighting_plan': '...',
            'camera_plan': '...',
            'background_plan': '...',
        },
        'equipment_list': [
            {
                'knowledge_id': 1001,
                'category': '灯光',
                'name': 'LED COB 常亮主灯',
                'model': 'Aputure 200d',
                'brand': '爱图仕',
                'qty': 2,
                'unit_price_band': 'high|mid|low',
                'reason': '...',
                'is_custom': False,
                'already_owned': False,
                'must_buy': True,
                'specs': {'功率': '200W', '色温': '5600K'},
                'purchase_price': '¥2800-3600',
                'rent_monthly': '¥250-380',
            }
        ],
        'package_tiers': [
            {
                'tier': '性价比',
                'total_range': '1.2-1.6w',
                'mode': 'mixed',
                'monthly_rent_range': '500-800 元/月',
                'suitable': '适合...',
                'items': [{'name': '...', 'qty': 1, 'model': '...', 'brand': '...'}],
            }
        ],
        'rental_channels': [
            {'name': '人人租机', 'kind': 'platform', 'note': '...', 'categories': ['相机', '灯光']}
        ],
        'vertical_notes': ['垂类布光/陈列要点'],
        'setup_steps': ['第1步：...'],
        'risks': ['...'],
        'scene_card': {
            'room_size_band': 'medium',
            'style_keywords': ['国风', '高端'],
            'color_palette': ['#f5f0e8', '#2c2c2c', '#c4a574'],
            'color_temp': '4000K',
            'furniture': ['主播桌'],
            'lighting_fixtures': ['COB主灯×2'],
            'product_category': '女装',
            'camera_angles': ['front', 'left', 'rear'],
            'forbidden': ['文字水印', '品牌logo'],
        },
    }
    user = json.dumps(
        {
            'requirement_brief': brief.model_dump(),
            'knowledge_hits': hit_payload,
            'output_schema': schema_hint,
        },
        ensure_ascii=False,
    )
    return system, user


def parse_compose_payload(payload: dict[str, Any]) -> PlanDraft:
    """LLM 输出 → PlanDraft（缺省字段自动补齐）。"""
    data = dict(payload or {})
    # 允许外层包一层 plan
    if 'plan' in data and isinstance(data['plan'], dict):
        data = data['plan']
    return PlanDraft.model_validate(data)
