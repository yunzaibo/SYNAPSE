"""Tests for event-derived factors (F-016)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from synapse.factor.base import BaseFactor
from synapse.factor.registry import FactorRegistry
from synapse.factor.spec import FactorSpec
from synapse.factor.factors.event_factor import (
    EventFactor,
    SentimentFactor,
    CapitalFlowFactor,
    PolicyFactor,
    enrich_with_events,
)
from synapse.core.schemas.event import Event, EventType, ImpactLevel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sentiment_data(n: int = 5) -> pd.DataFrame:
    """Generate synthetic social media sentiment data."""
    scores = [0.8, -0.3, 0.5, 0.1, -0.7][:n]
    engagements = [100, 50, 200, 10, 300][:n]
    return pd.DataFrame(
        {
            "sentiment_score": scores,
            "engagement_count": engagements,
        }
    )


def _make_capital_flow_data(n: int = 3) -> pd.DataFrame:
    """Generate synthetic capital flow data."""
    inst = [1e6, -5e5, 2e6][:n]
    retail = [-3e5, 8e5, -1e6][:n]
    return pd.DataFrame(
        {
            "institutional_flow": inst,
            "retail_flow": retail,
        }
    )


def _make_policy_data(n: int = 3) -> pd.DataFrame:
    """Generate synthetic policy event data."""
    sev = [0.8, 0.3, 0.6][:n]
    conf = [0.9, 0.5, 0.7][:n]
    imp = ["high", "low", "medium"][:n]
    return pd.DataFrame(
        {
            "severity": sev,
            "confidence": conf,
            "impact_level": imp,
        }
    )


def _make_events() -> list[Event]:
    """Generate a mix of event types for enrich_with_events tests."""
    return [
        Event(
            id="evt-001",
            event_type=EventType.SOCIAL_SENTIMENT,
            title="Positive social buzz",
            related_tickers=["600519.SH"],
            severity=0.7,
            confidence=0.8,
        ),
        Event(
            id="evt-002",
            event_type=EventType.SOCIAL_SENTIMENT,
            title="Negative social buzz",
            related_tickers=["600519.SH"],
            severity=0.3,
            confidence=0.6,
        ),
        Event(
            id="evt-003",
            event_type=EventType.CAPITAL_FLOW,
            title="Institutional inflow",
            related_tickers=["600519.SH"],
            severity=0.9,
            confidence=0.85,
        ),
        Event(
            id="evt-004",
            event_type=EventType.POLICY,
            title="Rate cut",
            related_tickers=["000001.SZ", "600519.SH"],
            severity=0.8,
            confidence=0.9,
        ),
        Event(
            id="evt-005",
            event_type=EventType.POLICY_CHANGE,
            title="Tax reform",
            related_tickers=["000001.SZ"],
            severity=0.5,
            confidence=0.7,
        ),
    ]


EVENT_FACTOR_CLASSES: list[type[BaseFactor]] = [
    SentimentFactor,
    CapitalFlowFactor,
    PolicyFactor,
]

EVENT_FACTOR_IDS: list[str] = [
    "sentiment_score",
    "capital_flow_signal",
    "policy_impact",
]


# ---------------------------------------------------------------------------
# EventFactor base class tests
# ---------------------------------------------------------------------------


class TestEventFactorBase:
    def test_cannot_instantiate_directly(self) -> None:
        """EventFactor is abstract — direct instantiation should fail."""
        with pytest.raises(TypeError):
            EventFactor()  # type: ignore[abstract]

    def test_is_base_factor_subclass(self) -> None:
        assert issubclass(EventFactor, BaseFactor)

    def test_all_concrete_factors_are_subclasses(self) -> None:
        for cls in EVENT_FACTOR_CLASSES:
            assert issubclass(cls, EventFactor)
            assert issubclass(cls, BaseFactor)


# ---------------------------------------------------------------------------
# Identity and spec tests
# ---------------------------------------------------------------------------


class TestEventFactorIdentity:
    @pytest.mark.parametrize(
        "factor_cls", EVENT_FACTOR_CLASSES, ids=lambda c: c.factor_id()
    )
    def test_factor_id_matches_spec(self, factor_cls: type[BaseFactor]) -> None:
        assert factor_cls.factor_id() == factor_cls.spec().factor_id

    @pytest.mark.parametrize(
        "factor_cls", EVENT_FACTOR_CLASSES, ids=lambda c: c.factor_id()
    )
    def test_spec_fields_not_empty(self, factor_cls: type[BaseFactor]) -> None:
        spec = factor_cls.spec()
        assert spec.name
        assert spec.description
        assert spec.category == "event"
        assert spec.inputs
        assert spec.lookback_days > 0
        assert spec.data_source == "event"

    @pytest.mark.parametrize(
        ("factor_cls", "expected_id"),
        list(zip(EVENT_FACTOR_CLASSES, EVENT_FACTOR_IDS)),
        ids=EVENT_FACTOR_IDS,
    )
    def test_factor_id_value(
        self, factor_cls: type[BaseFactor], expected_id: str
    ) -> None:
        assert factor_cls.factor_id() == expected_id


# ---------------------------------------------------------------------------
# SentimentFactor compute tests
# ---------------------------------------------------------------------------


class TestSentimentFactorCompute:
    def test_returns_series(self) -> None:
        df = _make_sentiment_data()
        result = SentimentFactor().compute(df)
        assert isinstance(result, pd.Series)
        assert len(result) == len(df)

    def test_weighted_average(self) -> None:
        """Verify engagement-weighted sentiment calculation."""
        df = _make_sentiment_data()
        result = SentimentFactor().compute(df)
        weights = df["engagement_count"].astype(float)
        total = weights.sum()
        expected = (df["sentiment_score"] * weights) / total
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_zero_engagement_returns_zero(self) -> None:
        df = pd.DataFrame(
            {
                "sentiment_score": [0.5, -0.5],
                "engagement_count": [0, 0],
            }
        )
        result = SentimentFactor().compute(df)
        assert (result == 0.0).all()

    def test_single_row(self) -> None:
        df = pd.DataFrame(
            {
                "sentiment_score": [0.7],
                "engagement_count": [100],
            }
        )
        result = SentimentFactor().compute(df)
        assert result.iloc[0] == pytest.approx(0.7)

    def test_all_positive_engagement(self) -> None:
        df = pd.DataFrame(
            {
                "sentiment_score": [1.0, 0.0],
                "engagement_count": [1, 1],
            }
        )
        result = SentimentFactor().compute(df)
        assert result.iloc[0] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# CapitalFlowFactor compute tests
# ---------------------------------------------------------------------------


class TestCapitalFlowFactorCompute:
    def test_returns_series(self) -> None:
        df = _make_capital_flow_data()
        result = CapitalFlowFactor().compute(df)
        assert isinstance(result, pd.Series)
        assert len(result) == len(df)

    def test_difference_calculation(self) -> None:
        df = _make_capital_flow_data()
        result = CapitalFlowFactor().compute(df)
        expected = df["institutional_flow"] - df["retail_flow"]
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_positive_institutional_excess(self) -> None:
        df = pd.DataFrame(
            {
                "institutional_flow": [1e6],
                "retail_flow": [0],
            }
        )
        result = CapitalFlowFactor().compute(df)
        assert result.iloc[0] == pytest.approx(1e6)

    def test_negative_excess(self) -> None:
        df = pd.DataFrame(
            {
                "institutional_flow": [0],
                "retail_flow": [5e5],
            }
        )
        result = CapitalFlowFactor().compute(df)
        assert result.iloc[0] == pytest.approx(-5e5)

    def test_symmetric_values(self) -> None:
        df = pd.DataFrame(
            {
                "institutional_flow": [1e5],
                "retail_flow": [1e5],
            }
        )
        result = CapitalFlowFactor().compute(df)
        assert result.iloc[0] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# PolicyFactor compute tests
# ---------------------------------------------------------------------------


class TestPolicyFactorCompute:
    def test_returns_series(self) -> None:
        df = _make_policy_data()
        result = PolicyFactor().compute(df)
        assert isinstance(result, pd.Series)
        assert len(result) == len(df)

    def test_composite_score(self) -> None:
        """Verify severity * confidence * impact_weight."""
        df = _make_policy_data()
        result = PolicyFactor().compute(df)
        # high=1.0, low=0.25, medium=0.5
        expected = df["severity"] * df["confidence"] * pd.Series([1.0, 0.25, 0.5])
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_high_impact(self) -> None:
        df = pd.DataFrame(
            {
                "severity": [1.0],
                "confidence": [1.0],
                "impact_level": ["high"],
            }
        )
        result = PolicyFactor().compute(df)
        assert result.iloc[0] == pytest.approx(1.0)

    def test_low_impact(self) -> None:
        df = pd.DataFrame(
            {
                "severity": [1.0],
                "confidence": [1.0],
                "impact_level": ["low"],
            }
        )
        result = PolicyFactor().compute(df)
        assert result.iloc[0] == pytest.approx(0.25)

    def test_unknown_impact_defaults_to_medium(self) -> None:
        df = pd.DataFrame(
            {
                "severity": [0.8],
                "confidence": [0.8],
                "impact_level": ["unknown"],
            }
        )
        result = PolicyFactor().compute(df)
        assert result.iloc[0] == pytest.approx(0.8 * 0.8 * 0.5)


# ---------------------------------------------------------------------------
# enrich_with_events tests
# ---------------------------------------------------------------------------


class TestEnrichWithEvents:
    def test_adds_event_columns(self) -> None:
        df = pd.DataFrame({"ticker": ["600519.SH", "000001.SZ"]})
        events = _make_events()
        result = enrich_with_events(df, events)
        expected_cols = [
            "social_sentiment_count",
            "social_sentiment_mean",
            "capital_flow_count",
            "capital_flow_mean",
            "policy_count",
            "policy_mean_severity",
            "policy_mean_confidence",
        ]
        for col in expected_cols:
            assert col in result.columns

    def test_preserves_original_columns(self) -> None:
        df = pd.DataFrame({"ticker": ["600519.SH"], "close": [100.0]})
        result = enrich_with_events(df, _make_events())
        assert "ticker" in result.columns
        assert "close" in result.columns

    def test_empty_events(self) -> None:
        df = pd.DataFrame({"ticker": ["600519.SH"]})
        result = enrich_with_events(df, [])
        assert result["social_sentiment_count"].iloc[0] == 0
        assert result["policy_count"].iloc[0] == 0

    def test_sentiment_aggregation(self) -> None:
        df = pd.DataFrame({"ticker": ["600519.SH"]})
        events = _make_events()
        result = enrich_with_events(df, events)
        # 2 SOCIAL_SENTIMENT events for 600519.SH
        row = result.iloc[0]
        assert row["social_sentiment_count"] == 2
        assert row["social_sentiment_mean"] == pytest.approx((0.7 + 0.3) / 2)

    def test_capital_flow_aggregation(self) -> None:
        df = pd.DataFrame({"ticker": ["600519.SH"]})
        events = _make_events()
        result = enrich_with_events(df, events)
        row = result.iloc[0]
        assert row["capital_flow_count"] == 1
        assert row["capital_flow_mean"] == pytest.approx(0.9)

    def test_policy_aggregation(self) -> None:
        df = pd.DataFrame({"ticker": ["600519.SH"]})
        events = _make_events()
        result = enrich_with_events(df, events)
        row = result.iloc[0]
        # Only 1 POLICY event touches 600519.SH (POLICY_CHANGE only touches 000001.SZ)
        assert row["policy_count"] == 1
        assert row["policy_mean_severity"] == pytest.approx(0.8)
        assert row["policy_mean_confidence"] == pytest.approx(0.9)

    def test_multi_ticker_policy(self) -> None:
        df = pd.DataFrame({"ticker": ["000001.SZ"]})
        events = _make_events()
        result = enrich_with_events(df, events)
        row = result.iloc[0]
        # POLICY + POLICY_CHANGE both touch 000001.SZ
        assert row["policy_count"] == 2
        assert row["policy_mean_severity"] == pytest.approx((0.8 + 0.5) / 2)
        assert row["policy_mean_confidence"] == pytest.approx((0.9 + 0.7) / 2)

    def test_does_not_mutate_input(self) -> None:
        df = pd.DataFrame({"ticker": ["600519.SH"]})
        original_cols = list(df.columns)
        enrich_with_events(df, _make_events())
        assert list(df.columns) == original_cols

    def test_multiple_tickers_independent(self) -> None:
        df = pd.DataFrame({"ticker": ["600519.SH", "000001.SZ"]})
        events = _make_events()
        result = enrich_with_events(df, events)
        # 600519.SH: 2 sentiment events
        assert result.iloc[0]["social_sentiment_count"] == 2
        # 000001.SZ: 0 sentiment events
        assert result.iloc[1]["social_sentiment_count"] == 0


# ---------------------------------------------------------------------------
# Registry integration tests
# ---------------------------------------------------------------------------


class TestEventRegistryIntegration:
    def test_all_event_factors_register(self) -> None:
        registry = FactorRegistry()
        for cls in EVENT_FACTOR_CLASSES:
            registry.register(cls)
        assert len(registry.list_factors()) == 3

    def test_all_event_factor_ids_present(self) -> None:
        registry = FactorRegistry()
        for cls in EVENT_FACTOR_CLASSES:
            registry.register(cls)
        for fid in EVENT_FACTOR_IDS:
            assert registry.get_factor(fid) is not None

    def test_event_category_filtering(self) -> None:
        registry = FactorRegistry()
        for cls in EVENT_FACTOR_CLASSES:
            registry.register(cls)
        event_factors = registry.list_by_category("event")
        assert len(event_factors) == 3
        for fid in EVENT_FACTOR_IDS:
            assert fid in event_factors

    def test_no_duplicate_factor_ids(self) -> None:
        ids = [cls.factor_id() for cls in EVENT_FACTOR_CLASSES]
        assert len(ids) == len(set(ids)), f"Duplicate factor IDs found: {ids}"


# ---------------------------------------------------------------------------
# Required columns tests
# ---------------------------------------------------------------------------


class TestEventRequiredColumns:
    def test_sentiment_columns(self) -> None:
        assert SentimentFactor.required_columns() == ["sentiment_score", "engagement_count"]

    def test_capital_flow_columns(self) -> None:
        assert CapitalFlowFactor.required_columns() == ["institutional_flow", "retail_flow"]

    def test_policy_columns(self) -> None:
        assert PolicyFactor.required_columns() == ["severity", "confidence", "impact_level"]
