"""Event Patterns -- Chinese financial event trigger patterns.

Provides 30+ regex trigger patterns for 5 event types:
EARNINGS_FORECAST, MERGER_ACQUISITION, EQUITY_CHANGE, POLICY_CHANGE, DIVIDEND.

Each pattern captures the trigger phrase and optional contextual groups
(amount, date, parties).

Part of P4 Chinese Financial NLP Layer (F-042).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Event type constants (internal names, mapped to P3 EventType in extractor)
# ---------------------------------------------------------------------------

EARNINGS_FORECAST = "EARNINGS_FORECAST"
MERGER_ACQUISITION = "MERGER_ACQUISITION"
EQUITY_CHANGE = "EQUITY_CHANGE"
POLICY_CHANGE = "POLICY_CHANGE"
DIVIDEND = "DIVIDEND"


# ---------------------------------------------------------------------------
# Pattern definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TriggerPattern:
    """A single trigger pattern for event detection.

    Attributes
    ----------
    event_type:
        Internal event type name (e.g. "EARNINGS_FORECAST").
    pattern:
        Compiled regex pattern. Group 0 is the full trigger phrase.
        Additional groups may capture amounts, dates, or parties.
    base_confidence:
        Base confidence score when this pattern matches (0.0--1.0).
    description:
        Human-readable description of the trigger phrase.
    """

    event_type: str
    pattern: re.Pattern[str]
    base_confidence: float = 0.8
    description: str = ""


# ---------------------------------------------------------------------------
# Amount pattern (shared across event types)
# ---------------------------------------------------------------------------

_AMOUNT_RE = r"(?:人民币)?\s*(?:[\d,.]+)\s*(?:亿元|万元|百万|千万|%|股|份|美元|港元)?"

# Date pattern (YYYY-MM-DD, YYYY年MM月DD日, etc.)
_DATE_RE = r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?"

# Percentage pattern
_PCT_RE = r"\d+(?:\.\d+)?%"

# ---------------------------------------------------------------------------
# 1. EARNINGS_FORECAST patterns (7 patterns)
# ---------------------------------------------------------------------------

_EARNINGS_PATTERNS: list[TriggerPattern] = [
    TriggerPattern(
        event_type=EARNINGS_FORECAST,
        pattern=re.compile(r"预计(?:.{0,30}?)(?:净利润|营收|利润|业绩|收入)(?:.{0,20}?)(?:增长|提升|上升|增加|下降|减少|下滑|亏损|扭亏)"),
        base_confidence=0.85,
        description="预计 + metric + direction",
    ),
    TriggerPattern(
        event_type=EARNINGS_FORECAST,
        pattern=re.compile(r"业绩预[增减盈亏]"),
        base_confidence=0.90,
        description="业绩预增/预减/预盈/预亏",
    ),
    TriggerPattern(
        event_type=EARNINGS_FORECAST,
        pattern=re.compile(r"扭亏为盈"),
        base_confidence=0.88,
        description="扭亏为盈",
    ),
    TriggerPattern(
        event_type=EARNINGS_FORECAST,
        pattern=re.compile(r"(?:净利润|营收|收入)(?:同比)?(?:.{0,10}?)(?:增长|提升|上升|下滑|下降)"),
        base_confidence=0.80,
        description="metric + direction (no 预计)",
    ),
    TriggerPattern(
        event_type=EARNINGS_FORECAST,
        pattern=re.compile(r"(?:净利润|营业收入|利润总额)(?:同比)?(?:增加|减少|增长|下降)(?:了)?\s*" + _PCT_RE),
        base_confidence=0.82,
        description="metric + percentage change",
    ),
    TriggerPattern(
        event_type=EARNINGS_FORECAST,
        pattern=re.compile(r"(?:发布|披露|公布)(?:了)?(?:20\d{2})?(?:年度|季度|半年度)?(?:业绩|财报|年报|季报|半年报)"),
        base_confidence=0.75,
        description="业绩报告发布事件",
    ),
    TriggerPattern(
        event_type=EARNINGS_FORECAST,
        pattern=re.compile(r"(?:净利|营收|利润)(?:同比)?(?:.{0,15}?)(?:约|达|超|逾)\s*" + _AMOUNT_RE),
        base_confidence=0.80,
        description="metric + approximate amount",
    ),
]


# ---------------------------------------------------------------------------
# 2. MERGER_ACQUISITION patterns (7 patterns)
# ---------------------------------------------------------------------------

_MA_PATTERNS: list[TriggerPattern] = [
    TriggerPattern(
        event_type=MERGER_ACQUISITION,
        pattern=re.compile(r"(?:收购|并购|合并|重组)(?:.{0,20}?)(?:100%|全部|部分)?(?:股权|资产|股份|业务)"),
        base_confidence=0.90,
        description="M&A action + target",
    ),
    TriggerPattern(
        event_type=MERGER_ACQUISITION,
        pattern=re.compile(r"拟(?:收购|并购|合并)"),
        base_confidence=0.85,
        description="拟 + M&A action",
    ),
    TriggerPattern(
        event_type=MERGER_ACQUISITION,
        pattern=re.compile(r"(?:重大资产重组|资产收购|股权收购)"),
        base_confidence=0.88,
        description="compound M&A term",
    ),
    TriggerPattern(
        event_type=MERGER_ACQUISITION,
        pattern=re.compile(r"(?:收购|并购)(?:了)?(?:.{0,20}?)(?:100%|全部|部分)?(?:股权|资产|股份)"),
        base_confidence=0.88,
        description="M&A action + completion",
    ),
    TriggerPattern(
        event_type=MERGER_ACQUISITION,
        pattern=re.compile(r"(?:合并|重组)(?:方案|计划|预案)"),
        base_confidence=0.80,
        description="restructuring plan",
    ),
    TriggerPattern(
        event_type=MERGER_ACQUISITION,
        pattern=re.compile(r"(?:现金|发行股份)(?:购买|收购|置换)(?:.{0,15}?)(?:资产|股权)"),
        base_confidence=0.82,
        description="consideration-based M&A",
    ),
    TriggerPattern(
        event_type=MERGER_ACQUISITION,
        pattern=re.compile(r"(?:拟|计划|意向)(?:.{0,10}?)(?:收购|并购)(?:.{0,20}?)(?:公司|企业)"),
        base_confidence=0.80,
        description="intent to acquire",
    ),
]


# ---------------------------------------------------------------------------
# 3. EQUITY_CHANGE patterns (7 patterns)
# ---------------------------------------------------------------------------

_EQUITY_PATTERNS: list[TriggerPattern] = [
    TriggerPattern(
        event_type=EQUITY_CHANGE,
        pattern=re.compile(r"(?:控股股东|大股东|实际控制人|董事|监事|高管)(?:.{0,10}?)(?:增持|减持)(?:.{0,15}?)(?:股|万股|份)"),
        base_confidence=0.90,
        description="insider equity change",
    ),
    TriggerPattern(
        event_type=EQUITY_CHANGE,
        pattern=re.compile(r"(?:增持|减持)(?:了)?(?:.{0,20}?)(?:股|万股|份|%)"),
        base_confidence=0.85,
        description="equity action + amount",
    ),
    TriggerPattern(
        event_type=EQUITY_CHANGE,
        pattern=re.compile(r"(?:股份)?回购(?:方案|计划|预案)?(?:.{0,20}?)(?:不超过|不低于|拟)?.*" + _AMOUNT_RE),
        base_confidence=0.85,
        description="share buyback",
    ),
    TriggerPattern(
        event_type=EQUITY_CHANGE,
        pattern=re.compile(r"(?:股权|股份)(?:质押|解除质押)"),
        base_confidence=0.88,
        description="share pledge/unpledge",
    ),
    TriggerPattern(
        event_type=EQUITY_CHANGE,
        pattern=re.compile(r"(?:定向增发|非公开发行|配股|增发)(?:.{0,15}?)(?:方案|预案|获批)?"),
        base_confidence=0.82,
        description="equity issuance",
    ),
    TriggerPattern(
        event_type=EQUITY_CHANGE,
        pattern=re.compile(r"(?:持股|持有)(?:比例)?(?:.{0,10}?)(?:变动|变化|超过|达到)"),
        base_confidence=0.78,
        description="holding percentage change",
    ),
    TriggerPattern(
        event_type=EQUITY_CHANGE,
        pattern=re.compile(r"(?:限售|解禁|解除限售)(?:.{0,10}?)(?:股|万股|份)"),
        base_confidence=0.80,
        description="lock-up expiry",
    ),
]


# ---------------------------------------------------------------------------
# 4. POLICY_CHANGE patterns (6 patterns)
# ---------------------------------------------------------------------------

_POLICY_PATTERNS: list[TriggerPattern] = [
    TriggerPattern(
        event_type=POLICY_CHANGE,
        pattern=re.compile(r"(?:证监会|央行|银保监|发改委|财政部|国务院)(?:.{0,10}?)(?:发布|印发|出台|修订|调整|修改)(?:了)?(?:.{0,20}?)?(?:通知|办法|规定|意见|指引|政策|规则|方案)"),
        base_confidence=0.90,
        description="regulator + action + document type",
    ),
    TriggerPattern(
        event_type=POLICY_CHANGE,
        pattern=re.compile(r"(?:发布|印发|出台|实施|调整|修改)(?:了)?(?:.{0,15}?)?(?:通知|办法|规定|意见|指引|规则)"),
        base_confidence=0.80,
        description="policy document issuance",
    ),
    TriggerPattern(
        event_type=POLICY_CHANGE,
        pattern=re.compile(r"(?:新规|新政策|新规定|监管政策|产业政策)(?:.{0,15}?)(?:发布|实施|落地|生效)"),
        base_confidence=0.82,
        description="new regulation announcement",
    ),
    TriggerPattern(
        event_type=POLICY_CHANGE,
        pattern=re.compile(r"(?:利率|存款准备金|增值税|关税|印花税)(?:.{0,10}?)(?:调整|下调|上调|减免|取消)"),
        base_confidence=0.85,
        description="rate/tax adjustment",
    ),
    TriggerPattern(
        event_type=POLICY_CHANGE,
        pattern=re.compile(r"(?:暂停|恢复|放开|限制|禁止)(?:.{0,10}?)(?:IPO|发行|上市|交易|审批)"),
        base_confidence=0.80,
        description="regulatory action on market activity",
    ),
    TriggerPattern(
        event_type=POLICY_CHANGE,
        pattern=re.compile(r"(?:自.{0,15}?起|将于.{0,15}?)(?:施行|实施|执行)(?:.{0,15}?)?(?:通知|办法|规定|意见)"),
        base_confidence=0.78,
        description="policy effective date announcement",
    ),
]


# ---------------------------------------------------------------------------
# 5. DIVIDEND patterns (6 patterns)
# ---------------------------------------------------------------------------

_DIVIDEND_PATTERNS: list[TriggerPattern] = [
    TriggerPattern(
        event_type=DIVIDEND,
        pattern=re.compile(r"(?:分红|派息|送股|转增)(?:方案|预案|计划)?(?:.{0,20}?)(?:每10股|每股)?.*" + _AMOUNT_RE),
        base_confidence=0.90,
        description="dividend/bonus announcement",
    ),
    TriggerPattern(
        event_type=DIVIDEND,
        pattern=re.compile(r"(?:高送转)(?:.{0,15}?)(?:预案|方案|分配方案)"),
        base_confidence=0.85,
        description="high transfer/bonus plan",
    ),
    TriggerPattern(
        event_type=DIVIDEND,
        pattern=re.compile(r"(?:每10股|每股)(?:.{0,10}?)(?:派|送|转增?)\s*\d+(?:\.\d+)?元?"),
        base_confidence=0.88,
        description="per-share dividend detail",
    ),
    TriggerPattern(
        event_type=DIVIDEND,
        pattern=re.compile(r"(?:分红|派息|利润分配)(?:方案)?(?:.{0,15}?)(?:通过|批准|实施|登记|除权)"),
        base_confidence=0.85,
        description="dividend lifecycle event",
    ),
    TriggerPattern(
        event_type=DIVIDEND,
        pattern=re.compile(r"(?:股利|红利)(?:发放|支付|到账)(?:.{0,15}?)"),
        base_confidence=0.80,
        description="dividend payment",
    ),
    TriggerPattern(
        event_type=DIVIDEND,
        pattern=re.compile(r"(?:半年度|中期|年度)(?:分红|派息|利润分配)(?:方案)?"),
        base_confidence=0.85,
        description="periodic dividend plan",
    ),
]


# ---------------------------------------------------------------------------
# All patterns combined
# ---------------------------------------------------------------------------

ALL_TRIGGER_PATTERNS: list[TriggerPattern] = (
    _EARNINGS_PATTERNS
    + _MA_PATTERNS
    + _EQUITY_PATTERNS
    + _POLICY_PATTERNS
    + _DIVIDEND_PATTERNS
)


# ---------------------------------------------------------------------------
# Event type to P3 EventType mapping
# ---------------------------------------------------------------------------

EVENT_TYPE_TO_P3: dict[str, str] = {
    EARNINGS_FORECAST: "earnings",
    MERGER_ACQUISITION: "corporate_action",
    EQUITY_CHANGE: "corporate_action",
    POLICY_CHANGE: "policy_change",
    DIVIDEND: "corporate_action",
}


# ---------------------------------------------------------------------------
# Keyword-based classification (fallback when no trigger pattern matches)
# ---------------------------------------------------------------------------

EVENT_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    EARNINGS_FORECAST: (
        "预计", "业绩", "净利润", "营收", "利润", "盈利", "亏损", "扭亏",
        "预增", "预减", "预盈", "预亏", "年报", "季报", "半年报",
    ),
    MERGER_ACQUISITION: (
        "收购", "并购", "合并", "重组", "资产收购", "股权收购",
        "重大资产重组", "收购方", "被收购", "标的公司",
    ),
    EQUITY_CHANGE: (
        "增持", "减持", "回购", "质押", "解禁", "增发", "配股",
        "定向增发", "限售", "解质押", "股权变动",
    ),
    POLICY_CHANGE: (
        "政策", "规定", "通知", "办法", "意见", "指引", "规则",
        "证监会", "央行", "银保监", "发改委", "新规", "监管",
    ),
    DIVIDEND: (
        "分红", "派息", "送股", "转增", "高送转", "股利", "红利",
        "利润分配", "每10股", "每股", "除权",
    ),
}


# ---------------------------------------------------------------------------
# Count verification (ensure 30+ patterns)
# ---------------------------------------------------------------------------

def count_patterns() -> int:
    """Return total number of trigger patterns."""
    return len(ALL_TRIGGER_PATTERNS)


def count_patterns_by_type() -> dict[str, int]:
    """Return pattern count per event type."""
    result: dict[str, int] = {}
    for p in ALL_TRIGGER_PATTERNS:
        result[p.event_type] = result.get(p.event_type, 0) + 1
    return result
