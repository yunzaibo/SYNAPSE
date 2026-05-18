"""Concrete Detectors -- Pluggable A-share market event detectors.

Six detectors covering earnings, policy, sentiment, theme, capital flow,
and corporate action event types.  Each implements BaseDetector.
"""

from __future__ import annotations

from datetime import date
from typing import Optional
import uuid

from synapse.core.schemas.event import (
    Event,
    EventSourceType,
    EventType,
    ImpactLevel,
)
from synapse.event.base import BaseDetector


def _event_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# EarningsDetector
# ---------------------------------------------------------------------------


class EarningsDetector(BaseDetector):
    """Detects earnings reports and pre-announcements.

    Triggers when data contains:
    - report_type in ["Q1", "Q2", "Q3", "Q4"]
    - eps_surprise > 0.0
    - pre_announcement = True
    """

    _REPORT_TYPES = {"Q1", "Q2", "Q3", "Q4"}

    @classmethod
    def event_type(cls) -> str:
        return "earnings"

    def detect(self, data: dict) -> Optional[Event]:
        has_report = data.get("report_type") in self._REPORT_TYPES
        has_surprise = isinstance(data.get("eps_surprise"), (int, float)) and data["eps_surprise"] > 0.0
        has_pre = data.get("pre_announcement") is True

        if not (has_report or has_surprise or has_pre):
            return None

        confidence = self.confidence_score(data)
        title_parts: list[str] = []
        if has_report:
            title_parts.append(f"{data['report_type']} earnings report")
        if has_surprise:
            title_parts.append(f"EPS surprise {data['eps_surprise']:+.2f}")
        if has_pre:
            title_parts.append("pre-announcement")

        return Event(
            id=_event_id(),
            event_type=EventType.EARNINGS,
            title=f"Earnings: {', '.join(title_parts)}",
            description=f"Earnings event detected: {', '.join(title_parts)}",
            event_date=_extract_date(data),
            related_tickers=data.get("tickers", []),
            confidence=confidence,
            source=EventSourceType.DATA_FEED,
        )

    def confidence_score(self, data: dict) -> float:
        score = 0.0
        if data.get("report_type") in self._REPORT_TYPES:
            score += 0.5
        if isinstance(data.get("eps_surprise"), (int, float)) and data["eps_surprise"] > 0.0:
            score += 0.3
        if data.get("pre_announcement") is True:
            score += 0.2
        return min(score, 1.0)


# ---------------------------------------------------------------------------
# PolicyDetector
# ---------------------------------------------------------------------------


class PolicyDetector(BaseDetector):
    """Detects policy changes from official government sources.

    Triggers when data contains:
    - source in ["csrc.gov.cn", "pboc.gov.cn"]
    - policy_type in ["rate_cut", "rate_hike", "rrr_cut", "rrr_hike",
                       "fiscal_stimulus", "csrc_rule"]
    """

    _OFFICIAL_SOURCES = {"csrc.gov.cn", "pboc.gov.cn"}
    _POLICY_TYPES = {
        "rate_cut", "rate_hike", "rrr_cut", "rrr_hike",
        "fiscal_stimulus", "csrc_rule",
    }

    @classmethod
    def event_type(cls) -> str:
        return "policy"

    def detect(self, data: dict) -> Optional[Event]:
        source = data.get("source", "")
        ptype = data.get("policy_type", "")
        is_official = source in self._OFFICIAL_SOURCES
        is_valid_type = ptype in self._POLICY_TYPES

        if not (is_official or is_valid_type):
            return None

        confidence = self.confidence_score(data)
        return Event(
            id=_event_id(),
            event_type=EventType.POLICY,
            title=f"Policy: {ptype or 'regulatory update'}",
            description=f"Policy event from {source or 'official source'}: {ptype or 'regulatory update'}",
            event_date=_extract_date(data),
            related_tickers=data.get("tickers", []),
            confidence=confidence,
            source=EventSourceType.DATA_FEED,
        )

    def confidence_score(self, data: dict) -> float:
        source = data.get("source", "")
        if source in self._OFFICIAL_SOURCES:
            return 0.95
        if data.get("policy_type") in self._POLICY_TYPES:
            return 0.7
        return 0.0


# ---------------------------------------------------------------------------
# SentimentDetector
# ---------------------------------------------------------------------------


class SentimentDetector(BaseDetector):
    """Detects market sentiment signals.

    Triggers when data contains any of:
    - margin_change_pct (float, non-zero)
    - northbound_flow (float, non-zero)
    - block_trade_count (int > 0)
    - dragon_tiger_count (int > 0)
    """

    @classmethod
    def event_type(cls) -> str:
        return "sentiment"

    def detect(self, data: dict) -> Optional[Event]:
        signals = self._collect_signals(data)
        if not signals:
            return None

        confidence = self.confidence_score(data)
        return Event(
            id=_event_id(),
            event_type=EventType.SENTIMENT,
            title=f"Sentiment: {', '.join(signals)}",
            description=f"Sentiment signal detected: {', '.join(signals)}",
            event_date=_extract_date(data),
            related_tickers=data.get("tickers", []),
            confidence=confidence,
            source=EventSourceType.DATA_FEED,
        )

    def confidence_score(self, data: dict) -> float:
        signals = self._collect_signals(data)
        if not signals:
            return 0.0
        return min(0.4 + 0.15 * len(signals), 1.0)

    @staticmethod
    def _collect_signals(data: dict) -> list[str]:
        signals: list[str] = []
        if isinstance(data.get("margin_change_pct"), (int, float)) and data["margin_change_pct"] != 0:
            signals.append("margin_change")
        if isinstance(data.get("northbound_flow"), (int, float)) and data["northbound_flow"] != 0:
            signals.append("northbound_flow")
        if isinstance(data.get("block_trade_count"), int) and data["block_trade_count"] > 0:
            signals.append("block_trades")
        if isinstance(data.get("dragon_tiger_count"), int) and data["dragon_tiger_count"] > 0:
            signals.append("dragon_tiger")
        return signals


# ---------------------------------------------------------------------------
# ThemeDetector
# ---------------------------------------------------------------------------


class ThemeDetector(BaseDetector):
    """Detects theme / sector-rotation events.

    Triggers when data contains:
    - policy_theme (non-empty string)
    - sector_rotation (non-empty string)
    - concept_sector (non-empty string)
    """

    @classmethod
    def event_type(cls) -> str:
        return "theme"

    def detect(self, data: dict) -> Optional[Event]:
        themes = self._collect_themes(data)
        if not themes:
            return None

        confidence = self.confidence_score(data)
        return Event(
            id=_event_id(),
            event_type=EventType.THEME,
            title=f"Theme: {', '.join(themes)}",
            description=f"Theme/sector event: {', '.join(themes)}",
            event_date=_extract_date(data),
            related_tickers=data.get("tickers", []),
            confidence=confidence,
            source=EventSourceType.DATA_FEED,
        )

    def confidence_score(self, data: dict) -> float:
        themes = self._collect_themes(data)
        if not themes:
            return 0.0
        return min(0.5 + 0.15 * len(themes), 1.0)

    @staticmethod
    def _collect_themes(data: dict) -> list[str]:
        themes: list[str] = []
        for key in ("policy_theme", "sector_rotation", "concept_sector"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                themes.append(val.strip())
        return themes


# ---------------------------------------------------------------------------
# CapitalFlowDetector
# ---------------------------------------------------------------------------


class CapitalFlowDetector(BaseDetector):
    """Detects capital flow changes.

    Triggers when data contains:
    - mainforce_flow (float, non-zero)
    - retail_flow (float, non-zero)
    - etf_net_inflow (float, non-zero)
    """

    @classmethod
    def event_type(cls) -> str:
        return "capital_flow"

    def detect(self, data: dict) -> Optional[Event]:
        flows = self._collect_flows(data)
        if not flows:
            return None

        confidence = self.confidence_score(data)
        return Event(
            id=_event_id(),
            event_type=EventType.CAPITAL_FLOW,
            title=f"Capital flow: {', '.join(flows)}",
            description=f"Capital flow event: {', '.join(flows)}",
            event_date=_extract_date(data),
            related_tickers=data.get("tickers", []),
            confidence=confidence,
            source=EventSourceType.DATA_FEED,
        )

    def confidence_score(self, data: dict) -> float:
        flows = self._collect_flows(data)
        if not flows:
            return 0.0
        return min(0.4 + 0.2 * len(flows), 1.0)

    @staticmethod
    def _collect_flows(data: dict) -> list[str]:
        flows: list[str] = []
        for key in ("mainforce_flow", "retail_flow", "etf_net_inflow"):
            val = data.get(key)
            if isinstance(val, (int, float)) and val != 0:
                flows.append(key)
        return flows


# ---------------------------------------------------------------------------
# CorporateActionDetector
# ---------------------------------------------------------------------------


class CorporateActionDetector(BaseDetector):
    """Detects corporate actions (offerings, dividends, M&A, etc.).

    Triggers when data contains:
    - action_type in ["secondary_offering", "rights_issue", "dividend",
                       "equity_incentive", "shareholder_change",
                       "ma_restructuring", "buyback"]
    """

    _ACTION_TYPES = {
        "secondary_offering", "rights_issue", "dividend",
        "equity_incentive", "shareholder_change",
        "ma_restructuring", "buyback",
    }

    @classmethod
    def event_type(cls) -> str:
        return "corporate_action"

    def detect(self, data: dict) -> Optional[Event]:
        action = data.get("action_type", "")
        if action not in self._ACTION_TYPES:
            return None

        confidence = self.confidence_score(data)
        return Event(
            id=_event_id(),
            event_type=EventType.CORPORATE_ACTION,
            title=f"Corporate action: {action}",
            description=f"Corporate action detected: {action}",
            event_date=_extract_date(data),
            related_tickers=data.get("tickers", []),
            confidence=confidence,
            source=EventSourceType.DATA_FEED,
        )

    def confidence_score(self, data: dict) -> float:
        if data.get("action_type") in self._ACTION_TYPES:
            return 0.85
        return 0.0


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _extract_date(data: dict) -> Optional[date]:
    """Extract date from common field names in *data*."""
    for key in ("event_date", "date", "report_date"):
        val = data.get(key)
        if isinstance(val, str):
            try:
                return date.fromisoformat(val)
            except ValueError:
                continue
        if isinstance(val, date):
            return val
    return None
