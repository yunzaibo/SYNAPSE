"""Event Taxonomy -- A-share market event type constants and source mappings.

Defines the six core event types, their data-source priority ordering,
category groupings, and propagation priority levels.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Event Types
# ---------------------------------------------------------------------------

EVENT_TYPES: dict[str, str] = {
    "earnings": "Earnings reports, pre-announcements, revisions, audit opinions",
    "policy": "CSRC rules, PBOC rate/RRR, fiscal policy, trading rules",
    "sentiment": "Margin trading, northbound capital, block trades, dragon-tiger list",
    "theme": "Policy themes, industry rotation, concept sectors",
    "capital_flow": "Institutional flows, retail flows, ETF subscriptions/redemptions",
    "corporate_action": "Secondary offerings, rights issues, dividends, equity incentives, M&A, buybacks",
    "policy_change": "Regulatory policy changes, CSRC/PBOC announcements, sector-specific regulations",
    "macro_shift": "Macroeconomic regime shifts, GDP/CPI/PMI trend changes, rate cycle transitions",
    "social_sentiment": "Social media sentiment signals — Weibo, Xueqiu, Eastmoney guba, news comment sentiment",
    "ner_enrichment": "NER entity enrichment — company, person, institution, metric recognition",
    "event_extraction": "Extracted structured events — earnings forecast, M&A, equity change, policy change, dividend",
}


# ---------------------------------------------------------------------------
# Source Priority (for deduplication -- lower index = higher authority)
# ---------------------------------------------------------------------------

SOURCE_PRIORITY: dict[str, int] = {
    "cninfo": 0,
    "csrc.gov.cn": 0,
    "pboc.gov.cn": 0,
    "akshare": 1,
    "hkex": 1,
    "exchange_data": 1,
    "wind": 1,
    "news": 2,
    "nlp": 3,
    "manual": 4,
}


# ---------------------------------------------------------------------------
# Category Map -- groups event types by broader category
# ---------------------------------------------------------------------------

EVENT_CATEGORY_MAP: dict[str, list[str]] = {
    "financial": ["earnings", "corporate_action"],
    "regulatory": ["policy", "policy_change"],
    "market_data": ["sentiment", "capital_flow", "macro_shift"],
    "social": ["social_sentiment"],
    "thematic": ["theme"],
    "nlp_enrichment": ["ner_enrichment", "event_extraction"],
}


# ---------------------------------------------------------------------------
# Priority Levels -- propagation priority (P0 highest, P3 lowest)
# ---------------------------------------------------------------------------

PRIORITY_LEVELS: dict[str, str] = {
    "P0": "Critical -- requires immediate propagation (e.g., trading halt, major policy change)",
    "P1": "High -- propagate within the same session (e.g., earnings surprise)",
    "P2": "Medium -- propagate within the day (e.g., sector theme shift)",
    "P3": "Low -- batch processing is acceptable (e.g., routine sentiment update)",
}
