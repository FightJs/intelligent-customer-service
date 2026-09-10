"""金额区间解析（预算 / 套餐 total_range）。

支持形如：3-5w / 1.2-1.6w / 5k-1w / <1w / 20w+ / 30000-50000 / 3-5万
"""
from __future__ import annotations

import re
from typing import NamedTuple

_W = 10_000.0
_K = 1_000.0

_NUM_UNIT = re.compile(r'^(?P<num>\d+(?:\.\d+)?)(?P<unit>[w万kK])?$')


class MoneyRange(NamedTuple):
    lo: float
    hi: float

    def midpoint(self) -> float:
        if self.hi == float('inf'):
            return self.lo if self.lo else float('inf')
        return (self.lo + self.hi) / 2


def _to_yuan(token: str, inherit_unit: str | None = None) -> float | None:
    token = token.strip()
    if not token:
        return None
    m = _NUM_UNIT.match(token)
    if not m:
        return None
    num = float(m.group('num'))
    unit = m.group('unit')
    if unit is None and inherit_unit:
        unit = inherit_unit
    if unit in ('w', '万'):
        return num * _W
    if unit in ('k', 'K'):
        return num * _K
    return num


def _unit_of(token: str) -> str | None:
    m = _NUM_UNIT.match(token.strip())
    if not m:
        return None
    return m.group('unit')


def parse_money_range(text: str | None) -> MoneyRange | None:
    """解析中文/英文金额区间，失败返回 None。"""
    if text is None:
        return None
    raw = re.sub(r'\s+', '', str(text).strip().replace('，', ','))
    raw = raw.replace('元', '')
    if not raw:
        return None

    # 开区间下限：1w+ / 20w+ / ≥20w / >10w
    if raw[-1] in '+＞>≥' or raw.startswith(('≥', '>')):
        core = raw.lstrip('≥＞>')
        if core.endswith('+'):
            core = core[:-1]
        lo = _to_yuan(core)
        if lo is not None:
            return MoneyRange(lo, float('inf'))
        return None

    # 开区间上限：<1w / ≤1w / ＜1w
    if raw[0] in '<＜≤':
        hi = _to_yuan(raw[1:])
        if hi is not None:
            return MoneyRange(0.0, hi)
        return None

    # 区间
    for sep in ('-', '~', '—', '–'):
        if sep in raw:
            left, right = raw.split(sep, 1)
            left_unit = _unit_of(left)
            right_unit = _unit_of(right)
            inherit = right_unit or left_unit
            left_yuan = _to_yuan(left, inherit_unit=inherit if left_unit is None else None)
            right_yuan = _to_yuan(right, inherit_unit=inherit if right_unit is None else None)
            if left_yuan is None or right_yuan is None:
                return None
            return MoneyRange(min(left_yuan, right_yuan), max(left_yuan, right_yuan))

    single = _to_yuan(raw)
    if single is not None:
        return MoneyRange(single, single)
    return None


def ranges_overlap(a: MoneyRange, b: MoneyRange) -> bool:
    return a.lo <= b.hi and b.lo <= a.hi


def tier_within_budget(
    tier_range: MoneyRange,
    budget_range: MoneyRange,
    tolerance: float,
) -> bool:
    """套餐区间是否与「预算 × (1±tolerance)」相交。

    tolerance=0.10 → ±10%；0.25 → ±25%。
    开区间 hi=inf 只放宽 lo。
    """
    expanded_hi = (
        float('inf')
        if budget_range.hi == float('inf')
        else budget_range.hi * (1 + tolerance)
    )
    expanded = MoneyRange(max(0.0, budget_range.lo * (1 - tolerance)), expanded_hi)
    return ranges_overlap(tier_range, expanded)


def budget_tolerance(flex: str | None) -> float:
    """budget_flex → 允许偏差比例。"""
    if flex == 'flexible':
        return 0.25
    return 0.10
