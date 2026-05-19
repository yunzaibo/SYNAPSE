"""Financial Patterns -- Regex patterns for extracting financial metrics from Chinese text.

20+ regex patterns covering:
- Revenue (营业收入/营收/总收入)
- Net profit (净利润/归母净利润/扣非净利润)
- EPS (每股收益)
- ROE (净资产收益率)
- Gross margin (毛利率)
- Period detection (Q1/Q2/Q3/Q4/年报)
- Approximation markers (约/超/近)

Part of P4 Chinese Financial NLP Layer (F-037).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Number matching utilities
# ---------------------------------------------------------------------------

# Matches: 123.45, 1,234.56, 123, -12.34, +5.67
_NUM = r"[+-]?\d[\d,]*(?:\.\d+)?"

# Chinese unit suffixes
_UNIT = r"(?:万亿|亿|千万|百万|万|千|百)"

# Approximation marker prefix (optional)
_APPROX_PREFIX = r"(?:约|超|近|逾|不足|接近|大概|估计|预计|左右|超过)?"

# Combined number with optional unit
_NUM_WITH_UNIT = rf"{_APPROX_PREFIX}{_NUM}\s*(?:{_UNIT})?"

# Approximation markers that appear before numbers
APPROXIMATION_MARKERS = ("约", "超", "近", "逾", "不足", "接近", "大概", "估计", "预计", "左右", "超过")

APPROXIMATION_PATTERN = re.compile(
    rf"({'|'.join(re.escape(m) for m in APPROXIMATION_MARKERS)})\s*{_NUM}\s*(?:{_UNIT})?"
)


# ---------------------------------------------------------------------------
# Pattern data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NumberPattern:
    """A compiled regex pattern for a financial metric.

    Attributes
    ----------
    metric_name:
        Standard metric name (e.g. "revenue", "net_profit").
    pattern:
        Compiled regex pattern.
    aliases:
        Human-readable aliases for logging/debugging.
    """

    metric_name: str
    pattern: re.Pattern[str]
    aliases: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Revenue patterns (5 patterns)
# ---------------------------------------------------------------------------

_REVENUE_PATTERNS = [
    # 营业收入 123.45亿元
    NumberPattern(
        metric_name="revenue",
        pattern=re.compile(
            rf"(?:营业收入|营收|总收入)\s*(?:为|达|为人民币)?\s*{_NUM_WITH_UNIT}"
        ),
        aliases=("营业收入", "营收", "总收入"),
    ),
    # 营业收入同比增加 12.3%
    NumberPattern(
        metric_name="revenue_growth",
        pattern=re.compile(
            rf"(?:营业收入|营收)\s*(?:同比|较上年)\s*(?:增加|增长|下降|减少)\s*{_NUM}%"
        ),
        aliases=("营收增长", "收入同比"),
    ),
    # 实现营收 100亿
    NumberPattern(
        metric_name="revenue",
        pattern=re.compile(
            rf"实现\s*(?:营收|营业收入|销售收入)\s*(?:{_NUM_WITH_UNIT})?"
        ),
        aliases=("实现营收",),
    ),
    # 主营业务收入
    NumberPattern(
        metric_name="revenue",
        pattern=re.compile(
            rf"主营业务收入\s*(?:为|达)?\s*{_NUM_WITH_UNIT}"
        ),
        aliases=("主营业务收入",),
    ),
    # 销售收入
    NumberPattern(
        metric_name="revenue",
        pattern=re.compile(
            rf"销售收入\s*(?:为|达)?\s*{_NUM_WITH_UNIT}"
        ),
        aliases=("销售收入",),
    ),
]

# ---------------------------------------------------------------------------
# Net profit patterns (5 patterns)
# ---------------------------------------------------------------------------

_PROFIT_PATTERNS = [
    # 净利润 12.34亿元
    NumberPattern(
        metric_name="net_profit",
        pattern=re.compile(
            rf"(?:净利润|归母净利润|归母净利|扣非净利润|扣非净利)"
            rf"\s*(?:为|达|约|实现)?\s*{_NUM_WITH_UNIT}"
        ),
        aliases=("净利润", "归母净利润", "扣非净利润"),
    ),
    # 归属于上市公司股东的净利润
    NumberPattern(
        metric_name="net_profit",
        pattern=re.compile(
            rf"归属于(?:上市公司)?(?:股东|母公司所有者)(?:的)?净利润"
            rf"\s*(?:为|达)?\s*{_NUM_WITH_UNIT}"
        ),
        aliases=("归母净利润(全称)",),
    ),
    # 扣除非经常性损益后的净利润
    NumberPattern(
        metric_name="deducted_profit",
        pattern=re.compile(
            rf"扣除非经常性损益(?:后的)?净利润"
            rf"\s*(?:为|达)?\s*{_NUM_WITH_UNIT}"
        ),
        aliases=("扣非净利润(全称)",),
    ),
    # 净利润同比增长
    NumberPattern(
        metric_name="net_profit_growth",
        pattern=re.compile(
            rf"净利润\s*(?:同比|较上年)\s*(?:增加|增长|下降|减少)\s*{_NUM}%"
        ),
        aliases=("净利润增长",),
    ),
    # 实现净利润
    NumberPattern(
        metric_name="net_profit",
        pattern=re.compile(
            rf"实现净利润\s*(?:约|达)?\s*{_NUM_WITH_UNIT}"
        ),
        aliases=("实现净利润",),
    ),
]

# ---------------------------------------------------------------------------
# EPS patterns (3 patterns)
# ---------------------------------------------------------------------------

_EPS_PATTERNS = [
    # 每股收益 1.23元
    NumberPattern(
        metric_name="eps",
        pattern=re.compile(
            rf"(?:每股收益|EPS|基本每股收益|稀释每股收益)"
            rf"\s*(?:为|达)?\s*{_NUM}\s*元?"
        ),
        aliases=("每股收益", "EPS", "基本每股收益"),
    ),
    # 每股收益同比
    NumberPattern(
        metric_name="eps_growth",
        pattern=re.compile(
            rf"每股收益\s*(?:同比|较上年)\s*(?:增加|增长|下降|减少)\s*{_NUM}"
        ),
        aliases=("EPS增长",),
    ),
    # 扣非每股收益
    NumberPattern(
        metric_name="deducted_eps",
        pattern=re.compile(
            rf"扣非每股收益\s*(?:为|达)?\s*{_NUM}\s*元?"
        ),
        aliases=("扣非每股收益",),
    ),
]

# ---------------------------------------------------------------------------
# ROE patterns (3 patterns)
# ---------------------------------------------------------------------------

_ROE_PATTERNS = [
    # 净资产收益率 12.34%
    NumberPattern(
        metric_name="roe",
        pattern=re.compile(
            rf"(?:净资产收益率|ROE|加权平均净资产收益率)"
            rf"\s*(?:为|达)?\s*{_NUM}\s*%?"
        ),
        aliases=("净资产收益率", "ROE", "加权平均ROE"),
    ),
    # 扣非后ROE
    NumberPattern(
        metric_name="deducted_roe",
        pattern=re.compile(
            rf"扣非后?(?:加权平均)?净资产收益率"
            rf"\s*(?:为|达)?\s*{_NUM}\s*%?"
        ),
        aliases=("扣非ROE",),
    ),
    # ROE同比下降
    NumberPattern(
        metric_name="roe_change",
        pattern=re.compile(
            rf"(?:净资产收益率|ROE)\s*(?:同比|较上年)\s*(?:下降|减少|增加|增长)\s*{_NUM}\s*%?"
        ),
        aliases=("ROE变化",),
    ),
]

# ---------------------------------------------------------------------------
# Gross margin patterns (4 patterns)
# ---------------------------------------------------------------------------

_MARGIN_PATTERNS = [
    # 毛利率 34.56%
    NumberPattern(
        metric_name="gross_margin",
        pattern=re.compile(
            rf"(?:毛利率|销售毛利率|综合毛利率)"
            rf"\s*(?:为|达)?\s*{_NUM}\s*%?"
        ),
        aliases=("毛利率", "销售毛利率"),
    ),
    # 净利率
    NumberPattern(
        metric_name="net_margin",
        pattern=re.compile(
            rf"(?:净利率|销售净利率|净利润率)"
            rf"\s*(?:为|达)?\s*{_NUM}\s*%?"
        ),
        aliases=("净利率",),
    ),
    # 毛利率同比
    NumberPattern(
        metric_name="gross_margin_change",
        pattern=re.compile(
            rf"毛利率\s*(?:同比|较上年)\s*(?:上升|下降|增加|减少)\s*{_NUM}\s*%?"
        ),
        aliases=("毛利率变化",),
    ),
    # 经营利润率
    NumberPattern(
        metric_name="operating_margin",
        pattern=re.compile(
            rf"(?:经营利润率|营业利润率)"
            rf"\s*(?:为|达)?\s*{_NUM}\s*%?"
        ),
        aliases=("经营利润率",),
    ),
]

# ---------------------------------------------------------------------------
# Additional financial metrics (4 patterns)
# ---------------------------------------------------------------------------

_EXTRA_PATTERNS = [
    # 总资产
    NumberPattern(
        metric_name="total_assets",
        pattern=re.compile(
            rf"(?:总资产|资产总额)\s*(?:为|达)?\s*{_NUM_WITH_UNIT}"
        ),
        aliases=("总资产",),
    ),
    # 净资产/股东权益
    NumberPattern(
        metric_name="net_assets",
        pattern=re.compile(
            rf"(?:净资产|股东权益)\s*(?:为|达)?\s*{_NUM_WITH_UNIT}"
        ),
        aliases=("净资产", "股东权益"),
    ),
    # 经营性现金流
    NumberPattern(
        metric_name="operating_cashflow",
        pattern=re.compile(
            rf"(?:经营性现金流|经营活动产生的现金流量净额)"
            rf"\s*(?:为|达)?\s*{_NUM_WITH_UNIT}"
        ),
        aliases=("经营性现金流",),
    ),
    # 资产负债率
    NumberPattern(
        metric_name="debt_ratio",
        pattern=re.compile(
            rf"资产负债率\s*(?:为|达)?\s*{_NUM}\s*%?"
        ),
        aliases=("资产负债率",),
    ),
]

# ---------------------------------------------------------------------------
# Combined metric pattern registry (20+ total)
# ---------------------------------------------------------------------------

ALL_PATTERNS: list[NumberPattern] = (
    _REVENUE_PATTERNS
    + _PROFIT_PATTERNS
    + _EPS_PATTERNS
    + _ROE_PATTERNS
    + _MARGIN_PATTERNS
    + _EXTRA_PATTERNS
)

METRIC_PATTERNS: dict[str, list[NumberPattern]] = {}
for _p in ALL_PATTERNS:
    METRIC_PATTERNS.setdefault(_p.metric_name, []).append(_p)


# ---------------------------------------------------------------------------
# Period detection patterns
# ---------------------------------------------------------------------------

_PERIOD_PATTERNS = [
    # 2024年年度报告 / 2024年报 / 年度报告
    re.compile(r"(\d{4})\s*年?\s*(?:年度|年报|年度报告)"),
    # 2024年第一季度报告 / 一季报 / Q1
    re.compile(r"(\d{4})\s*年?\s*(?:第?一|1|Q1)\s*季度(?:报告)?"),
    # 2024年第二季度报告 / 二季报 / Q2
    re.compile(r"(\d{4})\s*年?\s*(?:第?[二2]|Q2)\s*季度(?:报告)?"),
    # 2024年第三季度报告 / 三季报 / Q3
    re.compile(r"(\d{4})\s*年?\s*(?:第?[三3]|Q3)\s*季度(?:报告)?"),
    # 2024年第四季度报告 / 四季报 / Q4
    re.compile(r"(\d{4})\s*年?\s*(?:第?[四4]|Q4)\s*季度(?:报告)?"),
    # 半年报
    re.compile(r"(\d{4})\s*年?\s*半年(?:度)?(?:报告)?"),
    # 2024年中期报告 / 中报
    re.compile(r"(\d{4})\s*年?\s*(?:中期|中报)(?:报告)?"),
]

# Mapping from pattern index (in _PERIOD_PATTERNS) to period type
_PERIOD_INDEX_MAP: dict[int, str] = {
    0: "annual",       # 年度/年报
    1: "Q1",           # 一季度
    2: "Q2",           # 二季度
    3: "Q3",           # 三季度
    4: "Q4",           # 四季度
    5: "semi_annual",  # 半年报
    6: "semi_annual",  # 中期/中报
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def detect_period(text: str) -> Optional[dict[str, str]]:
    """Detect reporting period from text.

    Parameters
    ----------
    text:
        Chinese financial text (e.g. announcement title or body).

    Returns
    -------
    Dict with keys "year" and "period_type", or None if not detected.
    """
    for idx, pattern in enumerate(_PERIOD_PATTERNS):
        m = pattern.search(text)
        if m:
            year = m.group(1)
            period_type = _PERIOD_INDEX_MAP.get(idx, "")
            return {"year": year, "period_type": period_type}

    return None


def extract_approximation_markers(text: str) -> list[str]:
    """Extract all approximation markers found in text.

    Parameters
    ----------
    text:
        Chinese financial text.

    Returns
    -------
    List of approximation markers found (preserving order, no duplicates).
    """
    markers: list[str] = []
    for marker in APPROXIMATION_MARKERS:
        if marker in text and marker not in markers:
            markers.append(marker)
    return markers
