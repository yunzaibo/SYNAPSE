"""Event-derived factor implementations (F-016).

Converts event signals (social sentiment, capital flow, policy) into
standardized factor values compatible with the FactorEngine pipeline.
"""

from __future__ import annotations

from abc import abstractmethod
from datetime import date
from typing import Optional

import pandas as pd

from synapse.factor.base import BaseFactor
from synapse.factor.spec import FactorSpec


# ---------------------------------------------------------------------------
# Impact weight mapping for ImpactLevel enum
# ---------------------------------------------------------------------------

_IMPACT_WEIGHTS: dict[str, float] = {
    "low": 0.25,
    "medium": 0.5,
    "high": 1.0,
    "unknown": 0.5,
}


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class EventFactor(BaseFactor):
    """Abstract base class for event-derived factors.

    Subclasses must implement factor_id(), spec(), and compute().
    All event factors use category="event" and data_source="event".
    """

    @classmethod
    def spec(cls) -> FactorSpec:  # type: ignore[override]
        raise NotImplementedError

    @abstractmethod
    def compute(self, data: pd.DataFrame) -> pd.Series:
        ...


# ---------------------------------------------------------------------------
# SentimentFactor
# ---------------------------------------------------------------------------


class SentimentFactor(EventFactor):
    """Weighted average social media sentiment score.

    Computes engagement-weighted mean of sentiment_score values.
    Input DataFrame must contain: sentiment_score, engagement_count.
    """

    @classmethod
    def factor_id(cls) -> str:
        return "sentiment_score"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="sentiment_score",
            name="Social Sentiment Score",
            description="Engagement-weighted average social media sentiment",
            category="event",
            inputs=["sentiment_score", "engagement_count"],
            lookback_days=1,
            data_source="event",
            publication_lag=0,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        weights = data["engagement_count"].astype(float)
        total = weights.sum()
        if total == 0:
            return pd.Series(0.0, index=data.index)
        return (data["sentiment_score"] * weights) / total


# ---------------------------------------------------------------------------
# CapitalFlowFactor
# ---------------------------------------------------------------------------


class CapitalFlowFactor(EventFactor):
    """Capital flow signal: institutional minus retail flow.

    Positive values indicate net institutional buying pressure.
    Input DataFrame must contain: institutional_flow, retail_flow.
    """

    @classmethod
    def factor_id(cls) -> str:
        return "capital_flow_signal"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="capital_flow_signal",
            name="Capital Flow Signal",
            description="Difference between institutional and retail capital flows",
            category="event",
            inputs=["institutional_flow", "retail_flow"],
            lookback_days=1,
            data_source="event",
            publication_lag=0,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        return data["institutional_flow"] - data["retail_flow"]


# ---------------------------------------------------------------------------
# PolicyFactor
# ---------------------------------------------------------------------------


class PolicyFactor(EventFactor):
    """Policy event impact score.

    Composite score: severity * confidence * impact_weight.
    Input DataFrame must contain: severity, confidence, impact_level.
    """

    @classmethod
    def factor_id(cls) -> str:
        return "policy_impact"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="policy_impact",
            name="Policy Impact Score",
            description="Composite policy impact from severity, confidence, and impact level",
            category="event",
            inputs=["severity", "confidence", "impact_level"],
            lookback_days=1,
            data_source="event",
            publication_lag=0,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        weights = data["impact_level"].map(_IMPACT_WEIGHTS).fillna(0.5)
        return data["severity"] * data["confidence"] * weights


# ---------------------------------------------------------------------------
# enrich_with_events — bridge function
# ---------------------------------------------------------------------------


def enrich_with_events(
    df: pd.DataFrame,
    events: list,
) -> pd.DataFrame:
    """Inject event-derived columns into a DataFrame.

    Groups events by related_tickers and adds aggregated columns:
      - social_sentiment_count: number of SOCIAL_SENTIMENT events per ticker
      - social_sentiment_mean: mean severity of SOCIAL_SENTIMENT events
      - capital_flow_count: number of CAPITAL_FLOW events per ticker
      - capital_flow_mean: mean severity of CAPITAL_FLOW events
      - policy_count: number of POLICY / POLICY_CHANGE events per ticker
      - policy_mean_severity: mean severity of policy events
      - policy_mean_confidence: mean confidence of policy events

    Parameters
    ----------
    df:
        DataFrame with a ``ticker`` column.
    events:
        List of Event objects (from synapse.core.schemas.event).

    Returns
    -------
    pd.DataFrame with event columns merged on ``ticker``.
    """
    from synapse.core.schemas.event import EventType

    result = df.copy()

    # Initialize event columns
    for col in [
        "social_sentiment_count",
        "social_sentiment_mean",
        "capital_flow_count",
        "capital_flow_mean",
        "policy_count",
        "policy_mean_severity",
        "policy_mean_confidence",
    ]:
        result[col] = 0 if "count" in col else 0.0

    if not events:
        return result

    # Build per-ticker event summaries
    from collections import defaultdict

    ticker_events: dict[str, list] = defaultdict(list)
    for ev in events:
        for ticker in getattr(ev, "related_tickers", []):
            ticker_events[ticker].append(ev)

    # Social sentiment aggregates
    sentiment_rows: dict[str, list[float]] = defaultdict(list)
    capital_rows: dict[str, list[float]] = defaultdict(list)
    policy_severity: dict[str, list[float]] = defaultdict(list)
    policy_confidence: dict[str, list[float]] = defaultdict(list)

    for ticker, evts in ticker_events.items():
        for ev in evts:
            ev_type = ev.event_type
            if ev_type == EventType.SOCIAL_SENTIMENT:
                sentiment_rows[ticker].append(ev.severity)
            elif ev_type == EventType.CAPITAL_FLOW:
                capital_rows[ticker].append(ev.severity)
            elif ev_type in (EventType.POLICY, EventType.POLICY_CHANGE):
                policy_severity[ticker].append(ev.severity)
                policy_confidence[ticker].append(ev.confidence)

    # Map aggregated values back to DataFrame
    if "ticker" in result.columns:
        for ticker, vals in sentiment_rows.items():
            mask = result["ticker"] == ticker
            result.loc[mask, "social_sentiment_count"] = len(vals)
            result.loc[mask, "social_sentiment_mean"] = sum(vals) / len(vals)

        for ticker, vals in capital_rows.items():
            mask = result["ticker"] == ticker
            result.loc[mask, "capital_flow_count"] = len(vals)
            result.loc[mask, "capital_flow_mean"] = sum(vals) / len(vals)

        for ticker in policy_severity:
            mask = result["ticker"] == ticker
            sev = policy_severity[ticker]
            conf = policy_confidence[ticker]
            result.loc[mask, "policy_count"] = len(sev)
            result.loc[mask, "policy_mean_severity"] = sum(sev) / len(sev)
            result.loc[mask, "policy_mean_confidence"] = sum(conf) / len(conf)

    return result
