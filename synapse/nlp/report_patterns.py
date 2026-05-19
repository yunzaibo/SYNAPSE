"""Report Patterns -- Chinese analyst research report structure patterns.

Provides 18 regex patterns for detecting report structure elements:
title, author, institution, rating, target price, section markers
(conclusion, key points, risks, investment highlights, valuation).

Each pattern is designed to match common Chinese brokerage report formats
from major institutions (CICC, CITIC, Guotai Junan, etc.).

Part of P4 Chinese Financial NLP Layer (F-038).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Rating types
# ---------------------------------------------------------------------------

class ReportRating(str, Enum):
    """Investment rating types used by Chinese brokerages."""

    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    OVERWEIGHT = "overweight"
    UNDERWEIGHT = "underweight"


# ---------------------------------------------------------------------------
# Rating keyword mapping (Chinese -> English)
# ---------------------------------------------------------------------------

RATING_KEYWORDS: dict[str, ReportRating] = {
    # Buy-side
    "买入": ReportRating.BUY,
    "强推": ReportRating.BUY,
    "强烈推荐": ReportRating.BUY,
    "推荐": ReportRating.BUY,
    # Overweight
    "增持": ReportRating.OVERWEIGHT,
    "优于大市": ReportRating.OVERWEIGHT,
    "跑赢行业": ReportRating.OVERWEIGHT,
    "超配": ReportRating.OVERWEIGHT,
    # Hold
    "中性": ReportRating.HOLD,
    "持有": ReportRating.HOLD,
    "同步大市": ReportRating.HOLD,
    "平配": ReportRating.HOLD,
    "谨慎增持": ReportRating.HOLD,
    # Underweight
    "减持": ReportRating.UNDERWEIGHT,
    "弱于大市": ReportRating.UNDERWEIGHT,
    "跑输行业": ReportRating.UNDERWEIGHT,
    "低配": ReportRating.UNDERWEIGHT,
    # Sell
    "卖出": ReportRating.SELL,
    "回避": ReportRating.SELL,
}


# ---------------------------------------------------------------------------
# Pattern definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class StructurePattern:
    """A single pattern for report structure detection.

    Attributes
    ----------
    name:
        Pattern identifier (e.g. "title", "author", "rating").
    pattern:
        Compiled regex pattern.
    description:
        Human-readable description of what this pattern matches.
    priority:
        Higher priority wins when multiple patterns match the same text.
    """

    name: str
    pattern: re.Pattern[str]
    description: str = ""
    priority: int = 0


# ---------------------------------------------------------------------------
# 1. Title detection patterns (3 patterns)
# ---------------------------------------------------------------------------

TITLE_PATTERNS: list[StructurePattern] = [
    StructurePattern(
        name="title_standard",
        pattern=re.compile(
            r"(.{2,10}?)(?:证券|研究|深度|点评|行业|公司)(?:报告|研究)"
        ),
        description="XX证券/XX研究报告 standard header",
        priority=10,
    ),
    StructurePattern(
        name="title_brokerage",
        pattern=re.compile(
            r"([\u4e00-\u9fff]{2,8}(?:证券|银行|基金|资管|期货))"
            r".*?"
            r"([\u4e00-\u9fffA-Za-z0-9]{2,20})(?:研究报告|深度报告|点评报告|行业报告)"
        ),
        description="Brokerage name + subject report header",
        priority=15,
    ),
    StructurePattern(
        name="title_simple",
        pattern=re.compile(
            r"^[\s]*(.{4,40}?)(?:深度|点评|行业|公司|专题|策略|宏观)(?:研究报告|深度报告|点评报告|研究报告)"
        ),
        description="Simple title with report type suffix",
        priority=5,
    ),
]


# ---------------------------------------------------------------------------
# 2. Author / analyst patterns (2 patterns)
# ---------------------------------------------------------------------------

AUTHOR_PATTERNS: list[StructurePattern] = [
    StructurePattern(
        name="author_with_role",
        pattern=re.compile(
            r"(?:分析师|研究员|作者|执笔|撰写|报告作者)[：:\s]*"
            r"([\u4e00-\u9fff]{2,4})"
        ),
        description="Author with role prefix",
        priority=10,
    ),
    StructurePattern(
        name="author_certificate",
        pattern=re.compile(
            r"([\u4e00-\u9fff]{2,4})\s*"
            r"(?:S[AC]?\s*[A-Z0-9]+|执业编号|证书编号)"
        ),
        description="Author name followed by analyst certificate number",
        priority=15,
    ),
]


# ---------------------------------------------------------------------------
# 3. Institution / brokerage patterns (2 patterns)
# ---------------------------------------------------------------------------

INSTITUTION_PATTERNS: list[StructurePattern] = [
    StructurePattern(
        name="institution_header",
        pattern=re.compile(
            r"([\u4e00-\u9fff]{2,10}(?:证券|银行|基金|资管|期货|研究))"
        ),
        description="Institution name in header (XX证券/XX银行)",
        priority=10,
    ),
    StructurePattern(
        name="institution_footer",
        pattern=re.compile(
            r"(?:机构|单位|公司|研究机构)[：:\s]*"
            r"([\u4e00-\u9fff]{2,15})"
        ),
        description="Institution with explicit label",
        priority=5,
    ),
]


# ---------------------------------------------------------------------------
# 4. Rating patterns (2 patterns)
# ---------------------------------------------------------------------------

_RATING_KEYWORDS_RE = "|".join(
    re.escape(kw) for kw in RATING_KEYWORDS
)

RATING_PATTERNS: list[StructurePattern] = [
    StructurePattern(
        name="rating_explicit",
        pattern=re.compile(
            r"(?:投资评级|评级|评级建议|投资建议|投资评级说明)[：:\s]*"
            r"([\u4e00-\u9fff]{2,4})"
        ),
        description="Explicit rating label",
        priority=15,
    ),
    StructurePattern(
        name="rating_inline",
        pattern=re.compile(
            r"([\u4e00-\u9fff]{2,4})"
            r"(?:评级|评价)"
        ),
        description="Inline rating (e.g. '买入评级')",
        priority=10,
    ),
    StructurePattern(
        name="rating_in_text",
        pattern=re.compile(
            r"(?:给予|维持|首次|下调|上调|重申)"
            r"([\u4e00-\u9fff]{2,4})"
            r"(?:评级|目标)"
        ),
        description="Rating in context (给予买入评级)",
        priority=12,
    ),
]


# ---------------------------------------------------------------------------
# 5. Target price patterns (2 patterns)
# ---------------------------------------------------------------------------

TARGET_PRICE_PATTERNS: list[StructurePattern] = [
    StructurePattern(
        name="target_price_range",
        pattern=re.compile(
            r"(?:目标价|目标价格)[：:\s]*"
            r"([\d,.]+)\s*(?:[-~至到])\s*([\d,.]+)\s*(?:元|港元|美元)?"
        ),
        description="Target price range (e.g. 50-60元)",
        priority=20,
    ),
    StructurePattern(
        name="target_price_standard",
        pattern=re.compile(
            r"(?:目标价|目标价格|合理价值|合理估值)[：:\s]*"
            r"([\d,.]+)\s*(?:元|港元|美元)?"
        ),
        description="Standard target price extraction",
        priority=15,
    ),
]


# ---------------------------------------------------------------------------
# 6. Section marker patterns (7 patterns)
# ---------------------------------------------------------------------------

SECTION_MARKERS: dict[str, StructurePattern] = {
    "conclusion": StructurePattern(
        name="section_conclusion",
        pattern=re.compile(
            r"(?:投资要点|核心观点|投资摘要|投资逻辑|摘要|核心结论|结论|总结|投资结论)"
            r"[：:\s]*"
        ),
        description="Conclusion / investment thesis section",
        priority=15,
    ),
    "key_points": StructurePattern(
        name="section_key_points",
        pattern=re.compile(
            r"(?:核心观点|关键要点|主要观点|投资亮点|业绩亮点|重要提示|要点)"
            r"[：:\s]*"
        ),
        description="Key points / highlights section",
        priority=15,
    ),
    "risks": StructurePattern(
        name="section_risks",
        pattern=re.compile(
            r"(?:风险提示|风险因素|主要风险|风险警示|风险评估)"
            r"[：:\s]*"
        ),
        description="Risk factors section",
        priority=15,
    ),
    "investment_highlights": StructurePattern(
        name="section_highlights",
        pattern=re.compile(
            r"(?:投资亮点|投资要点|核心竞争力|竞争优势|投资价值)"
            r"[：:\s]*"
        ),
        description="Investment highlights section",
        priority=10,
    ),
    "valuation": StructurePattern(
        name="section_valuation",
        pattern=re.compile(
            r"(?:估值分析|盈利预测|盈利预测与估值|估值与盈利预测|估值)"
            r"[：:\s]*"
        ),
        description="Valuation / earnings forecast section",
        priority=10,
    ),
    "company_overview": StructurePattern(
        name="section_overview",
        pattern=re.compile(
            r"(?:公司概况|公司简介|业务概览|公司介绍)"
            r"[：:\s]*"
        ),
        description="Company overview section",
        priority=5,
    ),
    "financial_summary": StructurePattern(
        name="section_financial",
        pattern=re.compile(
            r"(?:财务数据|主要财务数据|财务摘要|财务指标)"
            r"[：:\s]*"
        ),
        description="Financial summary section",
        priority=5,
    ),
}


# ---------------------------------------------------------------------------
# 7. Bullet / list patterns for key points extraction
# ---------------------------------------------------------------------------

BULLET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?:^|\n)\s*[•·●◆◇▪▸►]\s*(.{5,120})"),
    re.compile(r"(?:^|\n)\s*\d+[.、）)]\s*(.{5,120})"),
    re.compile(r"(?:^|\n)\s*[-—]\s*(.{5,120})"),
    re.compile(r"(?:^|\n)\s*[\(（]\d+[\)）]\s*(.{5,120})"),
]


# ---------------------------------------------------------------------------
# 8. Risk factor sentence patterns
# ---------------------------------------------------------------------------

RISK_SENTENCE_PATTERN = re.compile(
    r"(?:若|如果|假如|一旦)(?:.{5,60}?)(?:风险|不确定性|下降|亏损|恶化|波动)"
)


# ---------------------------------------------------------------------------
# All patterns combined (count = 18 structure patterns)
# ---------------------------------------------------------------------------

ALL_TITLE_PATTERNS: list[StructurePattern] = TITLE_PATTERNS
ALL_AUTHOR_PATTERNS: list[StructurePattern] = AUTHOR_PATTERNS
ALL_INSTITUTION_PATTERNS: list[StructurePattern] = INSTITUTION_PATTERNS
ALL_RATING_PATTERNS: list[StructurePattern] = RATING_PATTERNS
ALL_TARGET_PRICE_PATTERNS: list[StructurePattern] = TARGET_PRICE_PATTERNS

ALL_PATTERNS: list[StructurePattern] = (
    TITLE_PATTERNS
    + AUTHOR_PATTERNS
    + INSTITUTION_PATTERNS
    + RATING_PATTERNS
    + TARGET_PRICE_PATTERNS
)


# ---------------------------------------------------------------------------
# Pattern count verification
# ---------------------------------------------------------------------------

def count_all_patterns() -> int:
    """Return total number of structure patterns."""
    return len(ALL_PATTERNS) + len(SECTION_MARKERS)


def count_by_category() -> dict[str, int]:
    """Return pattern count per category."""
    return {
        "title": len(TITLE_PATTERNS),
        "author": len(AUTHOR_PATTERNS),
        "institution": len(INSTITUTION_PATTERNS),
        "rating": len(RATING_PATTERNS),
        "target_price": len(TARGET_PRICE_PATTERNS),
        "section_markers": len(SECTION_MARKERS),
    }
