"""调研表字段 → 知识库过滤枚举映射。

约束（Spec §3.4）：
- room_size 由 venue.area / venue.size 推导
- budget_level 由 budget.total 与 budget.equipment 综合
- 原始区间值不在 F1 内改写
"""
from __future__ import annotations

from typing import Literal

RoomSize = Literal['small', 'medium', 'large', 'xlarge']
BudgetLevel = Literal['low', 'mid', 'high', 'ultra']

_AREA_TO_ROOM: dict[str, RoomSize] = {
    '<10': 'small',
    '10-20': 'small',
    '20-30': 'medium',
    '30-50': 'medium',
    '50+': 'large',
}

_TOTAL_BUDGET_TO_LEVEL: dict[str, BudgetLevel] = {
    '<1w': 'low',
    '1-3w': 'low',
    '3-5w': 'mid',
    '5-10w': 'mid',
    '10-20w': 'high',
    '20w+': 'ultra',
}

_EQUIP_BUDGET_TO_LEVEL: dict[str, BudgetLevel] = {
    '<5k': 'low',
    '5k-1w': 'low',
    '1-2w': 'mid',
    '2-5w': 'high',
    '5w+': 'ultra',
}

_LEVEL_RANK = {'low': 0, 'mid': 1, 'high': 2, 'ultra': 3}


def map_room_size(area: str | None, size_m2: float | None = None) -> RoomSize:
    """venue.area 选项值 + 可选实测面积 → room_size。

    Spec：
      small ← ['<10', '10-20']
      medium ← ['20-30', '30-50']
      large ← ['50+']
      xlarge ← 有具体尺寸且面积 > 80㎡
    """
    if size_m2 is not None and size_m2 > 80:
        return 'xlarge'
    if area is None or area == '':
        return 'medium'
    if area in _AREA_TO_ROOM:
        return _AREA_TO_ROOM[area]
    raise ValueError(f'unknown venue.area: {area!r}')


def map_budget_level(
    total: str | None = None,
    equipment: str | None = None,
) -> BudgetLevel:
    """budget.total + budget.equipment 综合取较高档，未填按 mid。

    未知枚举直接抛错，避免静默降级污染检索。
    """
    levels: list[BudgetLevel] = []
    if equipment is not None:
        if equipment not in _EQUIP_BUDGET_TO_LEVEL:
            raise ValueError(f'unknown budget.equipment: {equipment!r}')
        levels.append(_EQUIP_BUDGET_TO_LEVEL[equipment])
    if total is not None:
        if total not in _TOTAL_BUDGET_TO_LEVEL:
            raise ValueError(f'unknown budget.total: {total!r}')
        levels.append(_TOTAL_BUDGET_TO_LEVEL[total])
    if not levels:
        return 'mid'
    return max(levels, key=lambda item: _LEVEL_RANK[item])


def parse_budget_wan(value: str | None) -> tuple[float, float] | None:
    """把预算字符串解析为（下限万元, 上限万元）。解析失败返回 None。

    支持：`3-5w` / `1.2-1.6w` / `<1w` / `20w+` / `5000`（元）。
    """
    if not value:
        return None
    text = value.strip().lower().replace('，', ',').replace(' ', '')
    if not text:
        return None

    unit_wan = text.endswith('w') or '万' in text
    body = text.replace('w', '').replace('万', '')

    def _to_wan(num: float) -> float:
        return num if unit_wan else num / 10000.0

    if body.startswith('<'):
        try:
            return 0.0, _to_wan(float(body[1:]))
        except ValueError:
            return None
    if body.endswith('+'):
        try:
            low = _to_wan(float(body[:-1]))
            return low, low * 2.0
        except ValueError:
            return None
    if '-' in body:
        left, _, right = body.partition('-')
        try:
            return _to_wan(float(left)), _to_wan(float(right))
        except ValueError:
            return None
    try:
        single = _to_wan(float(body))
        return single * 0.9, single * 1.1
    except ValueError:
        return None
