"""Tests for Capital Flow Divergence -- schema, scoring, classification, build, settle."""

import pytest

from synapse.event.divergence import (
    CapitalFlowDivergence,
    compute_divergence_score,
    classify_divergence,
    build_divergence_from_flows,
    settle_divergence_contract,
)


# ------------------------------------------------------------------
# Mock helpers
# ------------------------------------------------------------------


class MockFlowEvent:
    """Duck-typed event with event_type and _flow_data."""

    def __init__(self, inst_flow=0.0, retail_flow=0.0, event_type=None):
        self.event_type = event_type
        self._flow_data = {
            "institutional_flow": inst_flow,
            "retail_flow": retail_flow,
        }


class MockContract:
    """Duck-typed contract that records settle() calls."""

    def __init__(self):
        self.settle_kwargs = None

    def settle(self, **kwargs):
        self.settle_kwargs = kwargs


# Use real EventType for the mock events
from synapse.core.schemas.event import EventType


# ------------------------------------------------------------------
# TestCapitalFlowDivergence (3 tests: defaults, round-trip, validation)
# ------------------------------------------------------------------


class TestCapitalFlowDivergence:
    def test_default_values(self):
        div = CapitalFlowDivergence()
        assert div.divergence_id == ""
        assert div.ticker == ""
        assert div.institutional_flow == 0.0
        assert div.retail_flow == 0.0
        assert div.divergence_score == 0.0
        assert div.classification == "neutral"
        assert div.magnitude == 0.5
        assert div.window_days == 5
        assert div.computed_at is None

    def test_to_dict_from_dict_roundtrip(self):
        from datetime import datetime
        from synapse.core.temporal import CST

        now = datetime.now(tz=CST)
        div = CapitalFlowDivergence(
            divergence_id="div-1",
            ticker="AAPL",
            sector="tech",
            institutional_flow=100.0,
            retail_flow=-50.0,
            divergence_score=0.6,
            classification="bullish_divergence",
            magnitude=0.8,
            window_days=10,
            computed_at=now,
        )
        d = div.to_dict()
        restored = CapitalFlowDivergence.from_dict(d)

        assert restored.divergence_id == "div-1"
        assert restored.ticker == "AAPL"
        assert restored.sector == "tech"
        assert restored.institutional_flow == 100.0
        assert restored.retail_flow == -50.0
        assert restored.divergence_score == pytest.approx(0.6)
        assert restored.classification == "bullish_divergence"
        assert restored.magnitude == pytest.approx(0.8)
        assert restored.window_days == 10
        assert restored.computed_at is not None

    def test_validation_score_out_of_range(self):
        with pytest.raises(ValueError, match="divergence_score must be in"):
            CapitalFlowDivergence(divergence_score=1.5)

    def test_validation_magnitude_out_of_range(self):
        with pytest.raises(ValueError, match="magnitude must be in"):
            CapitalFlowDivergence(magnitude=2.0)

    def test_validation_invalid_classification(self):
        with pytest.raises(ValueError, match="classification must be one of"):
            CapitalFlowDivergence(classification="invalid_label")


# ------------------------------------------------------------------
# TestComputeDivergenceScore (3 tests: bullish, bearish, neutral, zero)
# ------------------------------------------------------------------


class TestComputeDivergenceScore:
    def test_bullish_score(self):
        """Institutional inflow >> retail outflow -> positive score."""
        score = compute_divergence_score(inst_flow=100.0, retail_flow=-50.0)
        # numerator = 100 - (-50) = 150
        # denominator = 100 + 50 + epsilon ~ 150
        assert score == pytest.approx(150.0 / 150.0, abs=1e-6)

    def test_bearish_score(self):
        """Institutional outflow >> retail inflow -> negative score."""
        score = compute_divergence_score(inst_flow=-80.0, retail_flow=60.0)
        # numerator = -80 - 60 = -140
        # denominator = 80 + 60 + epsilon ~ 140
        assert score == pytest.approx(-140.0 / 140.0, abs=1e-6)

    def test_neutral_score(self):
        """Equal flows -> score near 0."""
        score = compute_divergence_score(inst_flow=50.0, retail_flow=50.0)
        # numerator = 50 - 50 = 0
        assert score == pytest.approx(0.0, abs=1e-6)

    def test_zero_flows(self):
        """Both flows zero -> score = 0 (epsilon in denominator prevents div-by-zero)."""
        score = compute_divergence_score(inst_flow=0.0, retail_flow=0.0)
        assert score == pytest.approx(0.0, abs=1e-6)


# ------------------------------------------------------------------
# TestClassifyDivergence (2 tests: threshold boundaries)
# ------------------------------------------------------------------


class TestClassifyDivergence:
    def test_bullish_above_threshold(self):
        """Score > 0.3 -> bullish_divergence."""
        assert classify_divergence(0.31) == "bullish_divergence"
        assert classify_divergence(1.0) == "bullish_divergence"

    def test_bearish_below_threshold(self):
        """Score < -0.3 -> bearish_divergence."""
        assert classify_divergence(-0.31) == "bearish_divergence"
        assert classify_divergence(-1.0) == "bearish_divergence"

    def test_neutral_in_range(self):
        """-0.3 <= score <= 0.3 -> neutral."""
        assert classify_divergence(0.0) == "neutral"
        assert classify_divergence(0.3) == "neutral"
        assert classify_divergence(-0.3) == "neutral"

    def test_boundary_exact_values(self):
        """Exact boundary values: 0.3 -> neutral, -0.3 -> neutral."""
        assert classify_divergence(0.3) == "neutral"
        assert classify_divergence(-0.3) == "neutral"


# ------------------------------------------------------------------
# TestBuildDivergenceFromFlows (1 test)
# ------------------------------------------------------------------


class TestBuildDivergenceFromFlows:
    def test_build_with_mock_events(self):
        """Aggregates capital flow events and produces correct divergence."""
        events = [
            MockFlowEvent(inst_flow=100.0, retail_flow=-30.0, event_type=EventType.CAPITAL_FLOW),
            MockFlowEvent(inst_flow=50.0, retail_flow=-20.0, event_type=EventType.CAPITAL_FLOW),
            MockFlowEvent(inst_flow=0.0, retail_flow=0.0, event_type=EventType.CAPITAL_FLOW),
        ]
        div = build_divergence_from_flows(events, ticker="TSLA", sector="auto", window_days=5)

        assert div.ticker == "TSLA"
        assert div.sector == "auto"
        assert div.institutional_flow == pytest.approx(150.0)
        assert div.retail_flow == pytest.approx(-50.0)
        assert div.divergence_score > 0.0  # institutional > retail
        assert div.classification == "bullish_divergence"
        assert div.window_days == 5
        assert div.computed_at is not None
        # magnitude = 3 events / 5 window_days = 0.6
        assert div.magnitude == pytest.approx(0.6)

    def test_build_ignores_non_flow_events(self):
        """Non-CAPITAL_FLOW events are skipped."""
        events = [
            MockFlowEvent(inst_flow=100.0, retail_flow=0.0, event_type=EventType.EARNINGS),
            MockFlowEvent(inst_flow=50.0, retail_flow=0.0, event_type=EventType.POLICY),
        ]
        div = build_divergence_from_flows(events, ticker="MSFT")
        assert div.institutional_flow == 0.0
        assert div.retail_flow == 0.0
        assert div.classification == "neutral"

    def test_build_empty_events(self):
        """No events -> zero flows, neutral classification."""
        div = build_divergence_from_flows([], ticker="GOOG")
        assert div.institutional_flow == 0.0
        assert div.retail_flow == 0.0
        assert div.classification == "neutral"
        assert div.magnitude == pytest.approx(0.0)


# ------------------------------------------------------------------
# TestSettleDivergenceContract (1 test)
# ------------------------------------------------------------------


class TestSettleDivergenceContract:
    def test_settle_bullish_divergence(self):
        """Settles contract with bullish_divergence result."""
        div = CapitalFlowDivergence(
            divergence_id="div-1",
            ticker="AAPL",
            institutional_flow=100.0,
            retail_flow=-50.0,
            divergence_score=0.8,
            classification="bullish_divergence",
            magnitude=0.7,
            window_days=5,
        )
        contract = MockContract()
        settle_divergence_contract(div, contract)

        assert contract.settle_kwargs["result"] == "bullish_divergence"
        meta = contract.settle_kwargs["metadata"]
        assert meta["divergence_score"] == pytest.approx(0.8)
        assert meta["flow_magnitude"] == pytest.approx(0.7)
        assert meta["institutional_flow"] == pytest.approx(100.0)
        assert meta["retail_flow"] == pytest.approx(-50.0)
        assert meta["classification"] == "bullish_divergence"
        assert meta["window_days"] == 5

    def test_settle_neutral_no_divergence(self):
        """Neutral classification settles as no_divergence."""
        div = CapitalFlowDivergence(classification="neutral")
        contract = MockContract()
        settle_divergence_contract(div, contract)
        assert contract.settle_kwargs["result"] == "no_divergence"

    def test_settle_bearish_divergence(self):
        """Bearish classification settles correctly."""
        div = CapitalFlowDivergence(classification="bearish_divergence")
        contract = MockContract()
        settle_divergence_contract(div, contract)
        assert contract.settle_kwargs["result"] == "bearish_divergence"

    def test_settle_no_settle_method_raises(self):
        """Contract without settle() -> TypeError."""
        div = CapitalFlowDivergence()
        with pytest.raises(TypeError, match="contract must have settle"):
            settle_divergence_contract(div, object())
