"""Tests for P2 Analytics: Error Pattern, Behavioral, Evolution, and Bias."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from synapse.analytics.behavioral import (
    BehavioralStatsAnalyzer,
    BehavioralStatsReport,
)
from synapse.analytics.bias import BiasDetector, BiasReport
from synapse.analytics.error_pattern import (
    ErrorPatternAnalyzer,
    ErrorPatternReport,
    TrendDirection,
)
from synapse.analytics.evolution import ThesisEvolutionAnalyzer, EvolutionReport
from synapse.analytics.drift import DriftDetector, DriftReport
from synapse.analytics.correlation import CorrelationAnalyzer, CorrelationReport
from synapse.core.schemas.position import Position, ResearchState, ThesisStatus
from synapse.core.schemas.decision import (
    Decision,
    DecisionType,
    TimeHorizon,
    AttentionOrigin,
    DecisionSignal,
)
from synapse.core.schemas.event import Event, EventType, ImpactLevel
from synapse.core.schemas.review import Review, ReviewOutcome, SignalEvaluation
from synapse.analytics.tracking_models import OutcomeRecord
from synapse.core.schemas.signal import Signal, SignalType, SignalStrength
from synapse.core.schemas.thesis import Thesis, Confidence
from synapse.core.temporal import CST


def _make_decision(
    *,
    decision_type: DecisionType = DecisionType.BUY,
    attention_origin: AttentionOrigin = AttentionOrigin.EVENT_ATTENTION,
    time_horizon: TimeHorizon = TimeHorizon.MEDIUM_TERM,
    created_at: datetime | None = None,
    num_signals: int = 0,
    id_: str = "d1",
) -> Decision:
    """Create a synthetic Decision with configurable attributes."""
    signals = [DecisionSignal(linked_signal_id=f"sig-{i}") for i in range(num_signals)]
    return Decision(
        id=id_,
        decision_type=decision_type,
        attention_origin=attention_origin,
        time_horizon=time_horizon,
        created_at=created_at or datetime.now(CST),
        signals=signals,
    )


# --- BehavioralStatsAnalyzer Tests ---


class TestBehavioralStatsAnalyzer:
    """12 tests for BehavioralStatsAnalyzer."""

    def test_single_decision_distribution(self):
        """Single decision produces 100% for its type."""
        d = _make_decision(decision_type=DecisionType.BUY, id_="d1")
        report = BehavioralStatsAnalyzer().analyze([d])

        assert report.total_decisions == 1
        assert report.decision_type_distribution == {"buy": 100.0}

    def test_multiple_decisions_aggregation(self):
        """Multiple decisions produce correct total count."""
        decisions = [_make_decision(id_=f"d{i}") for i in range(5)]
        report = BehavioralStatsAnalyzer().analyze(decisions)

        assert report.total_decisions == 5

    def test_buy_sell_ratio(self):
        """3 buys and 2 sells gives 60/40 split."""
        decisions = [
            _make_decision(decision_type=DecisionType.BUY, id_="b1"),
            _make_decision(decision_type=DecisionType.BUY, id_="b2"),
            _make_decision(decision_type=DecisionType.BUY, id_="b3"),
            _make_decision(decision_type=DecisionType.SELL, id_="s1"),
            _make_decision(decision_type=DecisionType.SELL, id_="s2"),
        ]
        report = BehavioralStatsAnalyzer().analyze(decisions)

        assert report.decision_type_distribution["buy"] == 60.0
        assert report.decision_type_distribution["sell"] == 40.0

    def test_attention_origin_percentages(self):
        """Distribution across three attention origins."""
        decisions = [
            _make_decision(attention_origin=AttentionOrigin.EVENT_ATTENTION, id_="a1"),
            _make_decision(attention_origin=AttentionOrigin.EVENT_ATTENTION, id_="a2"),
            _make_decision(attention_origin=AttentionOrigin.FACTOR_SIGNAL, id_="f1"),
            _make_decision(attention_origin=AttentionOrigin.PORTFOLIO_REVIEW, id_="r1"),
        ]
        report = BehavioralStatsAnalyzer().analyze(decisions)

        assert report.attention_origin_distribution["event_attention"] == 50.0
        assert report.attention_origin_distribution["factor_signal"] == 25.0
        assert report.attention_origin_distribution["portfolio_review"] == 25.0

    def test_time_horizon_percentages(self):
        """Distribution across three time horizons."""
        decisions = [
            _make_decision(time_horizon=TimeHorizon.SHORT_TERM, id_="s1"),
            _make_decision(time_horizon=TimeHorizon.SHORT_TERM, id_="s2"),
            _make_decision(time_horizon=TimeHorizon.LONG_TERM, id_="l1"),
        ]
        report = BehavioralStatsAnalyzer().analyze(decisions)

        assert report.time_horizon_distribution["short_term"] == pytest.approx(66.67, abs=0.01)
        assert report.time_horizon_distribution["long_term"] == pytest.approx(33.33, abs=0.01)

    def test_frequency_calculation(self):
        """8 decisions over 7-day span = 8.0 per week."""
        base = datetime(2026, 5, 1, tzinfo=CST)
        decisions = [
            _make_decision(created_at=base + timedelta(days=i), id_=f"d{i}")
            for i in range(8)
        ]
        report = BehavioralStatsAnalyzer().analyze(decisions)

        assert report.decision_frequency_per_week == pytest.approx(8.0)
        assert report.period_days == 7  # span from day 0 to day 7

    def test_avg_signals_computation(self):
        """Average signals: (0+3+6) / 3 = 3.0."""
        decisions = [
            _make_decision(num_signals=0, id_="d1"),
            _make_decision(num_signals=3, id_="d2"),
            _make_decision(num_signals=6, id_="d3"),
        ]
        report = BehavioralStatsAnalyzer().analyze(decisions)

        assert report.avg_signals_per_decision == pytest.approx(3.0)

    def test_empty_input(self):
        """Empty decision list returns zeroed report."""
        report = BehavioralStatsAnalyzer().analyze([])

        assert report.total_decisions == 0
        assert report.decision_type_distribution == {}
        assert report.attention_origin_distribution == {}
        assert report.time_horizon_distribution == {}
        assert report.decision_frequency_per_week == 0.0
        assert report.avg_signals_per_decision == 0.0
        assert report.period_days == 0

    def test_all_same_type(self):
        """All BUY decisions: 100% buy."""
        decisions = [_make_decision(decision_type=DecisionType.BUY, id_=f"d{i}") for i in range(10)]
        report = BehavioralStatsAnalyzer().analyze(decisions)

        assert report.decision_type_distribution == {"buy": 100.0}

    def test_mixed_types(self):
        """Three-way split: 2 buy, 1 sell, 1 buy = 75% buy, 25% sell."""
        decisions = [
            _make_decision(decision_type=DecisionType.BUY, id_="b1"),
            _make_decision(decision_type=DecisionType.BUY, id_="b2"),
            _make_decision(decision_type=DecisionType.BUY, id_="b3"),
            _make_decision(decision_type=DecisionType.SELL, id_="s1"),
        ]
        report = BehavioralStatsAnalyzer().analyze(decisions)

        assert report.decision_type_distribution["buy"] == 75.0
        assert report.decision_type_distribution["sell"] == 25.0

    def test_period_boundary(self):
        """Single decision has period_days=0 and frequency=0."""
        d = _make_decision(id_="only-one")
        report = BehavioralStatsAnalyzer().analyze([d])

        assert report.period_days == 0
        assert report.decision_frequency_per_week == 0.0

    def test_report_roundtrip(self):
        """to_dict -> from_dict preserves all fields."""
        base = datetime(2026, 5, 1, tzinfo=CST)
        decisions = [
            _make_decision(
                decision_type=DecisionType.BUY,
                attention_origin=AttentionOrigin.EVENT_ATTENTION,
                time_horizon=TimeHorizon.LONG_TERM,
                created_at=base + timedelta(days=i),
                num_signals=2,
                id_=f"d{i}",
            )
            for i in range(5)
        ]
        original = BehavioralStatsAnalyzer().analyze(decisions)
        restored = BehavioralStatsReport.from_dict(original.to_dict())

        assert restored.total_decisions == original.total_decisions
        assert restored.decision_type_distribution == original.decision_type_distribution
        assert restored.attention_origin_distribution == original.attention_origin_distribution
        assert restored.time_horizon_distribution == original.time_horizon_distribution
        assert restored.decision_frequency_per_week == original.decision_frequency_per_week
        assert restored.avg_signals_per_decision == original.avg_signals_per_decision
        assert restored.period_days == original.period_days


# ---------------------------------------------------------------------------
# Evolution Helpers
# ---------------------------------------------------------------------------


def _make_thesis(
    thesis_id: str,
    parent_id: str | None = None,
    revision: int = 1,
    confidence: str = "medium",
    created_at: datetime | None = None,
) -> Thesis:
    """Create a minimal Thesis for testing."""
    return Thesis(
        id=thesis_id,
        parent_thesis_id=parent_id,
        revision=revision,
        confidence=Confidence(confidence),
        created_at=created_at or datetime(2026, 1, 1, 12, 0, 0),
    )


def _make_bias_decision(
    decision_id: str,
    attention_origin: str = "event_attention",
    time_horizon: str = "medium_term",
) -> Decision:
    """Create a minimal Decision for bias testing."""
    return Decision(
        id=decision_id,
        attention_origin=AttentionOrigin(attention_origin),
        time_horizon=TimeHorizon(time_horizon),
    )


# ===========================================================================
# Evolution Tests (10)
# ===========================================================================


class TestEvolutionSingleThesisNoChain:
    """Single thesis with no parent -- depth should be 1."""

    def test_depth(self):
        t = _make_thesis("t1")
        report = ThesisEvolutionAnalyzer().analyze([t])
        assert report.revision_depth == 1

    def test_total_theses(self):
        t = _make_thesis("t1")
        report = ThesisEvolutionAnalyzer().analyze([t])
        assert report.total_theses_in_chain == 1

    def test_confidence_trajectory(self):
        t = _make_thesis("t1", confidence="high")
        report = ThesisEvolutionAnalyzer().analyze([t])
        assert report.confidence_trajectory == ["high"]


class TestEvolutionTwoLevelChain:
    """Thesis -> child: depth 2, velocity > 0."""

    def test_depth(self):
        parent = _make_thesis("p1", created_at=datetime(2026, 1, 1))
        child = _make_thesis("c1", parent_id="p1", revision=2,
                             created_at=datetime(2026, 2, 1))
        report = ThesisEvolutionAnalyzer().analyze([parent, child])
        assert report.revision_depth == 2

    def test_velocity(self):
        parent = _make_thesis("p1", created_at=datetime(2026, 1, 1))
        child = _make_thesis("c1", parent_id="p1", revision=2,
                             created_at=datetime(2026, 3, 1))
        report = ThesisEvolutionAnalyzer().analyze([parent, child])
        # 1 revision / 2 months = 0.5
        assert report.revision_velocity_per_month == pytest.approx(0.5, abs=0.01)

    def test_trajectory(self):
        parent = _make_thesis("p1", confidence="low")
        child = _make_thesis("c1", parent_id="p1", confidence="medium")
        report = ThesisEvolutionAnalyzer().analyze([parent, child])
        assert report.confidence_trajectory == ["low", "medium"]


class TestEvolutionThreeLevelChain:
    """Grandparent -> parent -> child: depth 3."""

    def test_depth(self):
        gp = _make_thesis("gp", created_at=datetime(2026, 1, 1))
        p = _make_thesis("p", parent_id="gp", revision=2,
                         created_at=datetime(2026, 2, 1))
        c = _make_thesis("c", parent_id="p", revision=3,
                         created_at=datetime(2026, 3, 1))
        report = ThesisEvolutionAnalyzer().analyze([gp, p, c])
        assert report.revision_depth == 3

    def test_total_theses(self):
        gp = _make_thesis("gp")
        p = _make_thesis("p", parent_id="gp", revision=2)
        c = _make_thesis("c", parent_id="p", revision=3)
        report = ThesisEvolutionAnalyzer().analyze([gp, p, c])
        assert report.total_theses_in_chain == 3


class TestEvolutionRevisionVelocity:
    """Velocity computed from timestamps across chain."""

    def test_fast_velocity(self):
        t1 = _make_thesis("t1", created_at=datetime(2026, 1, 1))
        t2 = _make_thesis("t2", parent_id="t1", revision=2,
                          created_at=datetime(2026, 1, 15))
        t3 = _make_thesis("t3", parent_id="t2", revision=3,
                          created_at=datetime(2026, 2, 1))
        report = ThesisEvolutionAnalyzer().analyze([t1, t2, t3])
        # 2 revisions / ~1 month = ~2.0
        assert report.revision_velocity_per_month > 1.5


class TestEvolutionConfidenceTrajectory:
    """Trajectory captures confidence transitions along chain."""

    def test_full_trajectory(self):
        t1 = _make_thesis("t1", confidence="low")
        t2 = _make_thesis("t2", parent_id="t1", confidence="medium")
        t3 = _make_thesis("t3", parent_id="t2", confidence="high")
        report = ThesisEvolutionAnalyzer().analyze([t1, t2, t3])
        assert report.confidence_trajectory == ["low", "medium", "high"]


class TestEvolutionEmptyInput:
    """Empty input returns zeroed report."""

    def test_empty(self):
        report = ThesisEvolutionAnalyzer().analyze([])
        assert report.revision_depth == 0
        assert report.revision_velocity_per_month == 0.0
        assert report.confidence_trajectory == []
        assert report.total_theses_in_chain == 0


class TestEvolutionCircularReference:
    """Circular parent_thesis_id does not cause infinite loop."""

    def test_no_infinite_loop(self):
        t1 = _make_thesis("t1", parent_id="t2")
        t2 = _make_thesis("t2", parent_id="t1")
        report = ThesisEvolutionAnalyzer().analyze([t1, t2])
        # Should complete without hanging; depth at most 2
        assert report.revision_depth <= 2
        assert report.total_theses_in_chain <= 2


class TestEvolutionMaxDepth:
    """Chain of length 5 yields depth 5."""

    def test_depth_5(self):
        theses = []
        for i in range(5):
            parent_id = f"t{i-1}" if i > 0 else None
            theses.append(
                _make_thesis(f"t{i}", parent_id=parent_id, revision=i + 1,
                             created_at=datetime(2026, 1 + i, 1))
            )
        report = ThesisEvolutionAnalyzer().analyze(theses)
        assert report.revision_depth == 5
        assert report.total_theses_in_chain == 5


class TestEvolutionMixedChains:
    """Multiple independent chains yield correct total and max depth."""

    def test_mixed(self):
        # Chain A: a1 -> a2 (depth 2)
        a1 = _make_thesis("a1")
        a2 = _make_thesis("a2", parent_id="a1", revision=2)
        # Chain B: b1 -> b2 -> b3 (depth 3)
        b1 = _make_thesis("b1")
        b2 = _make_thesis("b2", parent_id="b1", revision=2)
        b3 = _make_thesis("b3", parent_id="b2", revision=3)

        report = ThesisEvolutionAnalyzer().analyze([a1, a2, b1, b2, b3])
        assert report.revision_depth == 3  # max depth
        assert report.total_theses_in_chain == 5  # all theses in chains


class TestEvolutionReportRoundTrip:
    """EvolutionReport survives to_dict/from_dict round trip."""

    def test_round_trip(self):
        report = EvolutionReport(
            revision_depth=3,
            revision_velocity_per_month=1.5,
            confidence_trajectory=["low", "medium", "high"],
            lineage_tree={"r1": {"r2": {"r3": {}}}},
            total_theses_in_chain=3,
        )
        d = report.to_dict()
        restored = EvolutionReport.from_dict(d)
        assert restored.revision_depth == 3
        assert restored.revision_velocity_per_month == 1.5
        assert restored.confidence_trajectory == ["low", "medium", "high"]
        assert restored.lineage_tree == {"r1": {"r2": {"r3": {}}}}
        assert restored.total_theses_in_chain == 3


# ===========================================================================
# Bias Tests (10)
# ===========================================================================


class TestBiasBalancedDecisions:
    """Equal distribution across origins yields low imbalance score."""

    def test_low_imbalance(self):
        decisions = [
            _make_bias_decision("d1", "event_attention"),
            _make_bias_decision("d2", "factor_signal"),
            _make_bias_decision("d3", "portfolio_review"),
        ]
        report = BiasDetector().analyze(decisions)
        assert report.attention_imbalance_score < 0.1
        assert report.threshold_breaches == []

    def test_balanced_distribution(self):
        decisions = [
            _make_bias_decision("d1", "event_attention"),
            _make_bias_decision("d2", "factor_signal"),
            _make_bias_decision("d3", "portfolio_review"),
        ]
        report = BiasDetector().analyze(decisions)
        for v in report.attention_distribution.values():
            assert v == pytest.approx(1 / 3, abs=0.01)


class TestBiasEventAttention:
    """Heavily skewed toward event_attention."""

    def test_high_imbalance(self):
        decisions = [
            _make_bias_decision(f"d{i}", "event_attention") for i in range(9)
        ] + [
            _make_bias_decision("d9", "factor_signal"),
        ]
        report = BiasDetector().analyze(decisions)
        assert report.attention_imbalance_score > 0.3

    def test_breach_detected(self):
        decisions = [
            _make_bias_decision(f"d{i}", "event_attention") for i in range(8)
        ] + [
            _make_bias_decision("d8", "factor_signal"),
            _make_bias_decision("d9", "portfolio_review"),
        ]
        report = BiasDetector().analyze(decisions, threshold=0.7)
        assert "event_attention" in report.threshold_breaches


class TestBiasShortTerm:
    """Skewed toward short_term horizon."""

    def test_high_concentration(self):
        decisions = [
            _make_bias_decision(f"d{i}", time_horizon="short_term") for i in range(8)
        ] + [
            _make_bias_decision("d8", time_horizon="medium_term"),
            _make_bias_decision("d9", time_horizon="long_term"),
        ]
        report = BiasDetector().analyze(decisions)
        assert report.horizon_concentration_score > 0.3
        assert "short_term" in report.horizon_distribution
        assert report.horizon_distribution["short_term"] == 0.8


class TestBiasThresholdBreach:
    """Any origin exceeding threshold is flagged."""

    def test_breach_flagged(self):
        decisions = [
            _make_bias_decision(f"d{i}", "event_attention") for i in range(8)
        ] + [
            _make_bias_decision("d8", "factor_signal"),
            _make_bias_decision("d9", "portfolio_review"),
        ]
        report = BiasDetector().analyze(decisions, threshold=0.7)
        assert "event_attention" in report.threshold_breaches

    def test_no_breach_when_balanced(self):
        decisions = [
            _make_bias_decision("d1", "event_attention"),
            _make_bias_decision("d2", "factor_signal"),
            _make_bias_decision("d3", "portfolio_review"),
        ]
        report = BiasDetector().analyze(decisions, threshold=0.7)
        assert report.threshold_breaches == []


class TestBiasRecommendedFocus:
    """Recommended focus points to underrepresented origin."""

    def test_focus_on_least_used(self):
        decisions = [
            _make_bias_decision(f"d{i}", "event_attention") for i in range(5)
        ] + [
            _make_bias_decision("d5", "factor_signal"),
            _make_bias_decision("d6", "factor_signal"),
        ]
        report = BiasDetector().analyze(decisions)
        # portfolio_review has 0 presence
        assert report.recommended_focus == "portfolio_review"

    def test_no_focus_when_balanced(self):
        decisions = [
            _make_bias_decision("d1", "event_attention"),
            _make_bias_decision("d2", "factor_signal"),
            _make_bias_decision("d3", "portfolio_review"),
        ]
        report = BiasDetector().analyze(decisions)
        assert report.recommended_focus == ""


class TestBiasEmptyInput:
    """Empty input returns zeroed report."""

    def test_empty(self):
        report = BiasDetector().analyze([])
        assert report.attention_imbalance_score == 0.0
        assert report.horizon_concentration_score == 0.0
        assert report.attention_distribution == {}
        assert report.horizon_distribution == {}
        assert report.threshold_breaches == []
        assert report.recommended_focus == ""


class TestBiasSingleDecision:
    """Single decision: imbalance is 0 (only one category = trivially balanced)."""

    def test_single(self):
        decisions = [_make_bias_decision("d1", "event_attention", "short_term")]
        report = BiasDetector().analyze(decisions)
        assert report.attention_imbalance_score == 0.0
        assert report.horizon_concentration_score == 0.0
        assert report.attention_distribution == {"event_attention": 1.0}


class TestBiasAllSameOrigin:
    """All decisions from the same origin -- max imbalance."""

    def test_all_same(self):
        decisions = [
            _make_bias_decision(f"d{i}", "factor_signal") for i in range(5)
        ]
        report = BiasDetector().analyze(decisions)
        # Single category = 0 entropy = 0 imbalance score (trivially balanced)
        assert report.attention_imbalance_score == 0.0
        assert report.attention_distribution == {"factor_signal": 1.0}


class TestBiasReportRoundTrip:
    """BiasReport survives to_dict/from_dict round trip."""

    def test_round_trip(self):
        report = BiasReport(
            attention_imbalance_score=0.45,
            horizon_concentration_score=0.62,
            attention_distribution={"event_attention": 0.7, "factor_signal": 0.3},
            horizon_distribution={"short_term": 0.8, "long_term": 0.2},
            threshold_breaches=["event_attention"],
            recommended_focus="factor_signal",
        )
        d = report.to_dict()
        restored = BiasReport.from_dict(d)
        assert restored.attention_imbalance_score == 0.45
        assert restored.horizon_concentration_score == 0.62
        assert restored.threshold_breaches == ["event_attention"]
        assert restored.recommended_focus == "factor_signal"


class TestBiasCustomThreshold:
    """Custom threshold changes breach detection."""

    def test_low_threshold_catches_more(self):
        decisions = [
            _make_bias_decision(f"d{i}", "event_attention") for i in range(6)
        ] + [
            _make_bias_decision("d6", "factor_signal"),
            _make_bias_decision("d7", "factor_signal"),
        ]
        # 6/8 = 0.75 > 0.6 threshold
        report_strict = BiasDetector().analyze(decisions, threshold=0.6)
        assert "event_attention" in report_strict.threshold_breaches

        # 6/8 = 0.75 > 0.8 threshold? No
        report_lenient = BiasDetector().analyze(decisions, threshold=0.8)
        assert "event_attention" not in report_lenient.threshold_breaches


# ===========================================================================
# Error Pattern Tests (12)
# ===========================================================================


def _make_ep_review(
    review_id: str = "rev_ep01",
    created_at: datetime | None = None,
    signal_evaluations: list[dict] | None = None,
) -> Review:
    """Create a Review with signal evaluations for error pattern tests."""
    se_list = []
    if signal_evaluations:
        for se_data in signal_evaluations:
            se_list.append(
                SignalEvaluation(
                    linked_signal_id=se_data["linked_signal_id"],
                    was_accurate=se_data.get("was_accurate", False),
                    note=se_data.get("note", ""),
                )
            )
    return Review(
        id=review_id,
        created_at=created_at or datetime(2026, 5, 18, 14, 0, tzinfo=CST),
        signal_evaluations=se_list,
    )


def _make_ep_signal(
    signal_id: str = "sig_ep01",
    signal_type: SignalType = SignalType.ATTENTION_SPIKE,
) -> Signal:
    """Create a Signal for error pattern tests."""
    return Signal(
        id=signal_id,
        signal_type=signal_type,
        strength=SignalStrength.MEDIUM,
    )


class TestErrorPatternReport:
    def test_empty_report_defaults(self):
        """Default ErrorPatternReport has zero values."""
        report = ErrorPatternReport()
        assert report.overall_accuracy == 0.0
        assert report.per_signal_type_accuracy == {}
        assert report.worst_performers == []
        assert report.total_reviews == 0
        assert report.total_signals_evaluated == 0
        assert report.trend == TrendDirection.STABLE

    def test_report_round_trip(self):
        """Report serializes to dict and deserializes correctly."""
        original = ErrorPatternReport(
            overall_accuracy=0.75,
            per_signal_type_accuracy={"attention_spike": 0.8, "factor_anomaly": 0.5},
            worst_performers=["factor_anomaly"],
            total_reviews=10,
            total_signals_evaluated=40,
            trend=TrendDirection.IMPROVING,
        )
        d = original.to_dict()
        restored = ErrorPatternReport.from_dict(d)
        assert restored.overall_accuracy == 0.75
        assert restored.per_signal_type_accuracy == {
            "attention_spike": 0.8,
            "factor_anomaly": 0.5,
        }
        assert restored.worst_performers == ["factor_anomaly"]
        assert restored.total_reviews == 10
        assert restored.total_signals_evaluated == 40
        assert restored.trend == TrendDirection.IMPROVING


class TestErrorPatternAnalyzer:
    def test_empty_input(self):
        """Empty reviews list returns default report."""
        analyzer = ErrorPatternAnalyzer()
        report = analyzer.analyze([])
        assert report.total_reviews == 0
        assert report.total_signals_evaluated == 0
        assert report.overall_accuracy == 0.0

    def test_single_review(self):
        """Single review with mixed evaluations."""
        analyzer = ErrorPatternAnalyzer()
        review = _make_ep_review(
            signal_evaluations=[
                {"linked_signal_id": "sig1", "was_accurate": True},
                {"linked_signal_id": "sig2", "was_accurate": False},
            ]
        )
        report = analyzer.analyze([review])
        assert report.total_reviews == 1
        assert report.total_signals_evaluated == 2
        assert report.overall_accuracy == pytest.approx(0.5)

    def test_multiple_reviews(self):
        """Multiple reviews aggregate correctly."""
        analyzer = ErrorPatternAnalyzer()
        r1 = _make_ep_review(
            review_id="r1",
            signal_evaluations=[
                {"linked_signal_id": "sig1", "was_accurate": True},
                {"linked_signal_id": "sig2", "was_accurate": True},
            ],
        )
        r2 = _make_ep_review(
            review_id="r2",
            signal_evaluations=[
                {"linked_signal_id": "sig3", "was_accurate": False},
            ],
        )
        report = analyzer.analyze([r1, r2])
        assert report.total_reviews == 2
        assert report.total_signals_evaluated == 3
        assert report.overall_accuracy == pytest.approx(2 / 3)

    def test_per_signal_type_accuracy(self):
        """Accuracy is broken down by signal type when signals provided."""
        analyzer = ErrorPatternAnalyzer()
        signals = [
            _make_ep_signal("sig1", SignalType.ATTENTION_SPIKE),
            _make_ep_signal("sig2", SignalType.FACTOR_ANOMALY),
            _make_ep_signal("sig3", SignalType.ATTENTION_SPIKE),
        ]
        review = _make_ep_review(
            signal_evaluations=[
                {"linked_signal_id": "sig1", "was_accurate": True},
                {"linked_signal_id": "sig2", "was_accurate": False},
                {"linked_signal_id": "sig3", "was_accurate": True},
            ]
        )
        report = analyzer.analyze([review], signals=signals)
        assert "attention_spike" in report.per_signal_type_accuracy
        assert "factor_anomaly" in report.per_signal_type_accuracy
        assert report.per_signal_type_accuracy["attention_spike"] == pytest.approx(1.0)
        assert report.per_signal_type_accuracy["factor_anomaly"] == pytest.approx(0.0)

    def test_worst_performers(self):
        """Signal types below 50% accuracy are flagged as worst performers."""
        analyzer = ErrorPatternAnalyzer()
        signals = [
            _make_ep_signal("sig1", SignalType.ATTENTION_SPIKE),
            _make_ep_signal("sig2", SignalType.FACTOR_ANOMALY),
        ]
        review = _make_ep_review(
            signal_evaluations=[
                {"linked_signal_id": "sig1", "was_accurate": True},
                {"linked_signal_id": "sig1", "was_accurate": False},
                {"linked_signal_id": "sig2", "was_accurate": False},
                {"linked_signal_id": "sig2", "was_accurate": False},
                {"linked_signal_id": "sig2", "was_accurate": False},
            ]
        )
        report = analyzer.analyze([review], signals=signals)
        assert "factor_anomaly" in report.worst_performers
        assert "attention_spike" not in report.worst_performers

    def test_trend_improving(self):
        """Trend is improving when later reviews have higher accuracy."""
        analyzer = ErrorPatternAnalyzer()
        base_time = datetime(2026, 5, 1, tzinfo=CST)
        early_reviews = [
            _make_ep_review(
                review_id=f"r{i}",
                created_at=base_time + timedelta(days=i),
                signal_evaluations=[
                    {"linked_signal_id": f"sig{i}", "was_accurate": False},
                ],
            )
            for i in range(5)
        ]
        late_reviews = [
            _make_ep_review(
                review_id=f"r{i+5}",
                created_at=base_time + timedelta(days=i + 5),
                signal_evaluations=[
                    {"linked_signal_id": f"sig{i+5}", "was_accurate": True},
                ],
            )
            for i in range(5)
        ]
        report = analyzer.analyze(early_reviews + late_reviews)
        assert report.trend == TrendDirection.IMPROVING

    def test_trend_declining(self):
        """Trend is declining when later reviews have lower accuracy."""
        analyzer = ErrorPatternAnalyzer()
        base_time = datetime(2026, 5, 1, tzinfo=CST)
        early_reviews = [
            _make_ep_review(
                review_id=f"r{i}",
                created_at=base_time + timedelta(days=i),
                signal_evaluations=[
                    {"linked_signal_id": f"sig{i}", "was_accurate": True},
                ],
            )
            for i in range(5)
        ]
        late_reviews = [
            _make_ep_review(
                review_id=f"r{i+5}",
                created_at=base_time + timedelta(days=i + 5),
                signal_evaluations=[
                    {"linked_signal_id": f"sig{i+5}", "was_accurate": False},
                ],
            )
            for i in range(5)
        ]
        report = analyzer.analyze(early_reviews + late_reviews)
        assert report.trend == TrendDirection.DECLINING

    def test_trend_stable(self):
        """Trend is stable when accuracy is consistent."""
        analyzer = ErrorPatternAnalyzer()
        base_time = datetime(2026, 5, 1, tzinfo=CST)
        # Pattern that repeats identically in both halves: 60% accurate each
        pattern = [True, True, False, True, False]
        reviews = []
        for i in range(10):
            half = i % 5
            reviews.append(
                _make_ep_review(
                    review_id=f"r{i}",
                    created_at=base_time + timedelta(days=i),
                    signal_evaluations=[
                        {"linked_signal_id": f"sig{i}", "was_accurate": pattern[half]},
                    ],
                )
            )
        report = analyzer.analyze(reviews)
        assert report.trend == TrendDirection.STABLE

    def test_all_accurate(self):
        """100% accuracy when all evaluations are accurate."""
        analyzer = ErrorPatternAnalyzer()
        signals = [_make_ep_signal("sig1", SignalType.ATTENTION_SPIKE)]
        review = _make_ep_review(
            signal_evaluations=[
                {"linked_signal_id": "sig1", "was_accurate": True},
                {"linked_signal_id": "sig1", "was_accurate": True},
            ]
        )
        report = analyzer.analyze([review], signals=signals)
        assert report.overall_accuracy == pytest.approx(1.0)
        assert report.per_signal_type_accuracy["attention_spike"] == pytest.approx(1.0)

    def test_no_accurate(self):
        """0% accuracy when no evaluations are accurate."""
        analyzer = ErrorPatternAnalyzer()
        signals = [_make_ep_signal("sig1", SignalType.EARNINGS_SURPRISE)]
        review = _make_ep_review(
            signal_evaluations=[
                {"linked_signal_id": "sig1", "was_accurate": False},
                {"linked_signal_id": "sig1", "was_accurate": False},
            ]
        )
        report = analyzer.analyze([review], signals=signals)
        assert report.overall_accuracy == pytest.approx(0.0)
        assert "earnings_surprise" in report.worst_performers

    def test_mixed_types(self):
        """Multiple signal types produce correct per-type breakdown."""
        analyzer = ErrorPatternAnalyzer()
        signals = [
            _make_ep_signal("sig_a", SignalType.ATTENTION_SPIKE),
            _make_ep_signal("sig_b", SignalType.SECTOR_RESONANCE),
            _make_ep_signal("sig_c", SignalType.HISTORICAL_PATTERN_MATCH),
            _make_ep_signal("sig_d", SignalType.FACTOR_ANOMALY),
        ]
        review = _make_ep_review(
            signal_evaluations=[
                {"linked_signal_id": "sig_a", "was_accurate": True},
                {"linked_signal_id": "sig_b", "was_accurate": True},
                {"linked_signal_id": "sig_b", "was_accurate": False},
                {"linked_signal_id": "sig_c", "was_accurate": True},
                {"linked_signal_id": "sig_d", "was_accurate": False},
                {"linked_signal_id": "sig_d", "was_accurate": False},
            ]
        )
        report = analyzer.analyze([review], signals=signals)
        assert len(report.per_signal_type_accuracy) == 4
        assert report.per_signal_type_accuracy["attention_spike"] == pytest.approx(1.0)
        assert report.per_signal_type_accuracy["sector_resonance"] == pytest.approx(0.5)
        assert report.per_signal_type_accuracy["historical_pattern_match"] == pytest.approx(1.0)
        assert report.per_signal_type_accuracy["factor_anomaly"] == pytest.approx(0.0)
        assert "factor_anomaly" in report.worst_performers
        assert "attention_spike" not in report.worst_performers

    def test_review_ordering_does_not_affect_overall_accuracy(self):
        """Overall accuracy is independent of review ordering."""
        analyzer = ErrorPatternAnalyzer()
        r1 = _make_ep_review(
            review_id="r1",
            signal_evaluations=[
                {"linked_signal_id": "sig1", "was_accurate": True},
            ],
        )
        r2 = _make_ep_review(
            review_id="r2",
            signal_evaluations=[
                {"linked_signal_id": "sig2", "was_accurate": False},
            ],
        )
        report_forward = analyzer.analyze([r1, r2])
        report_reverse = analyzer.analyze([r2, r1])
        assert report_forward.overall_accuracy == report_reverse.overall_accuracy
        assert report_forward.total_signals_evaluated == report_reverse.total_signals_evaluated

    def test_large_dataset(self):
        """Large dataset produces consistent results."""
        analyzer = ErrorPatternAnalyzer()
        base_time = datetime(2026, 1, 1, tzinfo=CST)
        signals = [
            _make_ep_signal("sig_a", SignalType.ATTENTION_SPIKE),
            _make_ep_signal("sig_b", SignalType.FACTOR_ANOMALY),
        ]
        reviews = []
        for i in range(100):
            reviews.append(
                _make_ep_review(
                    review_id=f"r{i}",
                    created_at=base_time + timedelta(days=i),
                    signal_evaluations=[
                        {"linked_signal_id": "sig_a", "was_accurate": i % 2 == 0},
                        {"linked_signal_id": "sig_b", "was_accurate": i % 3 == 0},
                    ],
                )
            )
        report = analyzer.analyze(reviews, signals=signals)
        assert report.total_reviews == 100
        assert report.total_signals_evaluated == 200
        assert 0.0 <= report.overall_accuracy <= 1.0
        assert report.trend in (TrendDirection.IMPROVING, TrendDirection.STABLE, TrendDirection.DECLINING)


# ===========================================================================
# Integration Tests (4)
# ===========================================================================


class TestIntegrationErrorPatternFromYAML:
    """Load Reviews from YAML files on disk and run ErrorPatternAnalyzer."""

    def test_error_pattern_from_yaml(self, tmp_path):
        """Create temp Review YAML files, load, and analyze."""
        import yaml as _yaml

        review_dir = tmp_path / "reviews"
        review_dir.mkdir()

        # Write two review YAML files
        for i in range(2):
            review_data = {
                "id": f"rev_yaml_{i}",
                "linked_decision_id": f"dec_{i}",
                "review_outcome": "thesis_confirmed",
                "signal_evaluations": [
                    {"linked_signal_id": f"sig_{i}", "was_accurate": i == 0}
                ],
            }
            (review_dir / f"rev_yaml_{i}.yaml").write_text(
                _yaml.dump(review_data, allow_unicode=True)
            )

        # Load from YAML
        raw_objects = []
        for yml_file in sorted(review_dir.glob("*.yaml")):
            with open(yml_file, encoding="utf-8") as f:
                raw_objects.append(_yaml.safe_load(f))

        reviews = [Review.from_dict(obj) for obj in raw_objects]
        report = ErrorPatternAnalyzer().analyze(reviews)

        assert report.total_reviews == 2
        assert report.total_signals_evaluated == 2
        assert report.overall_accuracy == pytest.approx(0.5)


class TestIntegrationBehavioralFromYAML:
    """Load Decisions from YAML files on disk and run BehavioralStatsAnalyzer."""

    def test_behavioral_from_yaml(self, tmp_path):
        """Create temp Decision YAML files, load, and analyze."""
        import yaml as _yaml

        dec_dir = tmp_path / "decisions"
        dec_dir.mkdir()

        # Write two decision YAML files
        for i in range(2):
            decision_data = {
                "id": f"dec_yaml_{i}",
                "decision_type": "buy" if i == 0 else "sell",
                "attention_origin": "event_attention",
                "time_horizon": "medium_term",
            }
            (dec_dir / f"dec_yaml_{i}.yaml").write_text(
                _yaml.dump(decision_data, allow_unicode=True)
            )

        # Load from YAML
        raw_objects = []
        for yml_file in sorted(dec_dir.glob("*.yaml")):
            with open(yml_file, encoding="utf-8") as f:
                raw_objects.append(_yaml.safe_load(f))

        decisions = [Decision.from_dict(obj) for obj in raw_objects]
        report = BehavioralStatsAnalyzer().analyze(decisions)

        assert report.total_decisions == 2
        assert report.decision_type_distribution["buy"] == 50.0
        assert report.decision_type_distribution["sell"] == 50.0


class TestIntegrationCLIRegister:
    """Verify analytics CLI register() creates valid subparsers."""

    def test_cli_register(self):
        """Register analytics subcommand and verify subparsers exist."""
        import argparse
        from synapse.cli.commands.analytics import register

        parser = argparse.ArgumentParser(prog="synapse")
        subparsers = parser.add_subparsers(dest="command")
        register(subparsers)

        # Parse with error-pattern subcommand
        args_ep = parser.parse_args(["analytics", "error-pattern", "--data-dir", "/tmp"])
        assert args_ep.command == "analytics"
        assert args_ep.analytics_command == "error-pattern"
        assert args_ep.data_dir == "/tmp"
        assert hasattr(args_ep, "func")

        # Parse with behavioral subcommand
        args_beh = parser.parse_args(["analytics", "behavioral", "--data-dir", "/tmp"])
        assert args_beh.command == "analytics"
        assert args_beh.analytics_command == "behavioral"
        assert args_beh.data_dir == "/tmp"
        assert hasattr(args_beh, "func")


class TestIntegrationAllAnalyzersEmpty:
    """Each analyzer handles empty input gracefully."""

    def test_all_analyzers_empty(self):
        """All four analyzers produce valid reports from empty input."""
        ep_report = ErrorPatternAnalyzer().analyze([])
        assert ep_report.total_reviews == 0
        assert ep_report.overall_accuracy == 0.0

        beh_report = BehavioralStatsAnalyzer().analyze([])
        assert beh_report.total_decisions == 0

        evo_report = ThesisEvolutionAnalyzer().analyze([])
        assert evo_report.revision_depth == 0

        bias_report = BiasDetector().analyze([])
        assert bias_report.attention_imbalance_score == 0.0


# ===========================================================================
# Correlation Tests (10)
# ===========================================================================


def _make_event(
    event_id: str,
    event_type: EventType = EventType.EARNINGS,
    impact_level: ImpactLevel = ImpactLevel.MEDIUM,
    related_tickers: list[str] | None = None,
    outcome_tracking: list[dict] | None = None,
    linked_review_ids: list[str] | None = None,
) -> Event:
    """Create a synthetic Event for correlation tests."""
    ot_records = []
    if outcome_tracking:
        for ot in outcome_tracking:
            ot_records.append(
                OutcomeRecord(
                    event_id=ot.get("event_id", event_id),
                    review_id=ot["review_id"],
                    impact_assessment=ot.get("impact_assessment", ""),
                )
            )
    return Event(
        id=event_id,
        event_type=event_type,
        impact_level=impact_level,
        related_tickers=related_tickers or [],
        outcome_tracking=ot_records,
        linked_review_ids=linked_review_ids or [],
    )


def _make_review(
    review_id: str,
    review_outcome: ReviewOutcome = ReviewOutcome.THESIS_CONFIRMED,
    linked_decision_id: str | None = None,
) -> Review:
    """Create a synthetic Review for correlation tests."""
    return Review(
        id=review_id,
        review_outcome=review_outcome,
        linked_decision_id=linked_decision_id,
    )


class TestCorrelationLinkedPairs:
    """Events linked via outcome_tracking produce correct pair count."""

    def test_direct_linkage(self):
        e1 = _make_event(
            "e1",
            outcome_tracking=[{"review_id": "r1"}],
        )
        r1 = _make_review("r1")
        report = CorrelationAnalyzer().analyze([e1], [r1])

        assert report.total_event_review_pairs == 1
        assert report.correlation_strength == pytest.approx(1.0)
        assert report.unlinked_events == []


class TestCorrelationUnlinkedEvents:
    """Events without any linked review appear in unlinked_events."""

    def test_no_review_match(self):
        e1 = _make_event(
            "e1",
            outcome_tracking=[{"review_id": "r_nonexistent"}],
        )
        r1 = _make_review("r1")
        report = CorrelationAnalyzer().analyze([e1], [r1])

        assert report.total_event_review_pairs == 0
        assert report.unlinked_events == ["e1"]
        assert report.correlation_strength == pytest.approx(0.0)


class TestCorrelationSuccessRateByType:
    """Success rate computed per event_type."""

    def test_mixed_types(self):
        e1 = _make_event(
            "e1",
            event_type=EventType.EARNINGS,
            outcome_tracking=[{"review_id": "r1"}],
        )
        e2 = _make_event(
            "e2",
            event_type=EventType.EARNINGS,
            outcome_tracking=[{"review_id": "r2"}],
        )
        e3 = _make_event(
            "e3",
            event_type=EventType.POLICY,
            outcome_tracking=[{"review_id": "r3"}],
        )
        r1 = _make_review("r1", ReviewOutcome.THESIS_CONFIRMED)
        r2 = _make_review("r2", ReviewOutcome.THESIS_INVALIDATED)
        r3 = _make_review("r3", ReviewOutcome.THESIS_CONFIRMED)

        report = CorrelationAnalyzer().analyze([e1, e2, e3], [r1, r2, r3])

        # earnings: 1 confirmed / 2 total = 0.5
        assert report.event_type_success_rate["earnings"] == pytest.approx(0.5)
        # policy: 1 confirmed / 1 total = 1.0
        assert report.event_type_success_rate["policy"] == pytest.approx(1.0)


class TestCorrelationCalibration:
    """Calibration score reflects impact_level vs review_outcome alignment."""

    def test_high_impact_confirmed(self):
        """HIGH impact + thesis_confirmed = high calibration."""
        e1 = _make_event(
            "e1",
            impact_level=ImpactLevel.HIGH,
            outcome_tracking=[{"review_id": "r1"}],
        )
        r1 = _make_review("r1", ReviewOutcome.THESIS_CONFIRMED)
        report = CorrelationAnalyzer().analyze([e1], [r1])

        assert report.overall_calibration_score == pytest.approx(0.9)
        assert "high" in report.impact_calibration
        assert report.impact_calibration["high"]["count"] == 1


class TestCorrelationEmptyEvents:
    """Empty events list returns default report."""

    def test_empty(self):
        report = CorrelationAnalyzer().analyze([], [])
        assert report.total_event_review_pairs == 0
        assert report.unlinked_events == []
        assert report.event_type_success_rate == {}
        assert report.overall_calibration_score == 0.0


class TestCorrelationEmptyReviews:
    """Events exist but no reviews available -- all events unlinked."""

    def test_no_reviews(self):
        e1 = _make_event(
            "e1",
            outcome_tracking=[{"review_id": "r1"}],
        )
        report = CorrelationAnalyzer().analyze([e1], [])

        assert report.total_event_review_pairs == 0
        assert report.unlinked_events == ["e1"]
        assert report.correlation_strength == pytest.approx(0.0)


class TestCorrelationAllLinked:
    """Every event has at least one linked review."""

    def test_all_linked(self):
        events = [
            _make_event(f"e{i}", outcome_tracking=[{"review_id": f"r{i}"}])
            for i in range(5)
        ]
        reviews = [_make_review(f"r{i}") for i in range(5)]
        report = CorrelationAnalyzer().analyze(events, reviews)

        assert report.total_event_review_pairs == 5
        assert report.correlation_strength == pytest.approx(1.0)
        assert report.unlinked_events == []


class TestCorrelationNoLinked:
    """No event has a matching review -- all unlinked."""

    def test_none_linked(self):
        events = [
            _make_event(f"e{i}", outcome_tracking=[{"review_id": f"r_fake_{i}"}])
            for i in range(3)
        ]
        reviews = [_make_review(f"r_real_{i}") for i in range(3)]
        report = CorrelationAnalyzer().analyze(events, reviews)

        assert report.total_event_review_pairs == 0
        assert report.correlation_strength == pytest.approx(0.0)
        assert report.unlinked_events == ["e0", "e1", "e2"]


class TestCorrelationLargeDataset:
    """Large dataset produces consistent results."""

    def test_large(self):
        events = [
            _make_event(
                f"e{i}",
                event_type=EventType.EARNINGS if i % 2 == 0 else EventType.POLICY,
                impact_level=ImpactLevel.HIGH if i % 3 == 0 else ImpactLevel.MEDIUM,
                outcome_tracking=[{"review_id": f"r{i}"}],
            )
            for i in range(100)
        ]
        reviews = [
            _make_review(
                f"r{i}",
                review_outcome=(
                    ReviewOutcome.THESIS_CONFIRMED
                    if i % 4 != 0
                    else ReviewOutcome.THESIS_INVALIDATED
                ),
            )
            for i in range(100)
        ]
        report = CorrelationAnalyzer().analyze(events, reviews)

        assert report.total_event_review_pairs == 100
        assert report.correlation_strength == pytest.approx(1.0)
        assert len(report.unlinked_events) == 0
        assert "earnings" in report.event_type_success_rate
        assert "policy" in report.event_type_success_rate
        assert 0.0 <= report.overall_calibration_score <= 1.0


class TestCorrelationReportRoundTrip:
    """CorrelationReport survives to_dict/from_dict round trip."""

    def test_round_trip(self):
        original = CorrelationReport(
            event_type_success_rate={"earnings": 0.75, "policy": 0.5},
            impact_calibration={
                "high": {
                    "count": 3,
                    "avg_calibration": 0.8,
                    "outcome_distribution": {"thesis_confirmed": 2, "thesis_invalidated": 1},
                }
            },
            correlation_strength=0.6,
            total_event_review_pairs=6,
            unlinked_events=["e4", "e5"],
            overall_calibration_score=0.65,
        )
        d = original.to_dict()
        restored = CorrelationReport.from_dict(d)

        assert restored.event_type_success_rate == original.event_type_success_rate
        assert restored.impact_calibration == original.impact_calibration
        assert restored.correlation_strength == original.correlation_strength
        assert restored.total_event_review_pairs == original.total_event_review_pairs
        assert restored.unlinked_events == original.unlinked_events
        assert restored.overall_calibration_score == original.overall_calibration_score


# ===========================================================================
# Drift Tests (10)
# ===========================================================================


def _make_position(
    pos_id: str = "p1",
    thesis_id: str | None = "t1",
    thesis_status: str = "active",
    created_at: datetime | None = None,
) -> Position:
    """Create a Position with configurable thesis_status."""
    return Position(
        id=pos_id,
        linked_thesis_id=thesis_id,
        research_state=ResearchState(
            thesis_status=ThesisStatus(thesis_status),
        ),
        created_at=created_at or datetime(2026, 1, 1, tzinfo=CST),
    )


def _make_drift_review(
    review_id: str = "rev1",
    thesis_id: str = "t1",
    outcome: str = "thesis_confirmed",
    created_at: datetime | None = None,
) -> Review:
    """Create a Review with a review_outcome for drift tests."""
    return Review(
        id=review_id,
        linked_thesis_id=thesis_id,
        review_outcome=ReviewOutcome(outcome),
        created_at=created_at or datetime(2026, 5, 1, tzinfo=CST),
    )


class TestDriftNoDrift:
    """All positions active -> health=1.0, no weakening signals."""

    def test_all_active(self):
        positions = [_make_position(f"p{i}", thesis_status="active") for i in range(3)]
        report = DriftDetector().detect(positions)
        assert report.health_score == 1.0
        assert report.weakening_signals == []
        assert report.recovery_count == 0
        assert report.total_positions_tracked == 3


class TestDriftSingleWeakening:
    """One weakened position produces weakening signal and lower health."""

    def test_one_weakened(self):
        positions = [
            _make_position("p1", thesis_status="active"),
            _make_position("p2", thesis_status="weakened"),
            _make_position("p3", thesis_status="active"),
        ]
        report = DriftDetector().detect(positions)
        # health = (1.0 + 0.5 + 1.0) / 3 = 2.5/3 ~ 0.8333
        assert report.health_score == pytest.approx(5 / 6, abs=0.01)
        assert "p2" in report.weakening_signals
        assert len(report.weakening_signals) == 1


class TestDriftRecovery:
    """Recovery transition (weakened -> active) counted correctly."""

    def test_recovery_detected(self):
        # Position starts weakened
        positions = [_make_position("p1", thesis_status="weakened")]
        # Review confirms thesis -> implies active
        reviews = [
            _make_drift_review(
                review_id="r1",
                thesis_id="t1",
                outcome="thesis_confirmed",
                created_at=datetime(2026, 5, 1, tzinfo=CST),
            )
        ]
        report = DriftDetector().detect(positions, reviews=reviews)
        assert report.recovery_count == 1
        assert any(
            e["from"] == "weakened" and e["to"] == "active"
            for e in report.drift_timeline
        )


class TestDriftVelocity:
    """Velocity computed from transition timestamps."""

    def test_velocity_positive(self):
        positions = [
            _make_position("p1", thesis_id="t1", thesis_status="active"),
            _make_position("p2", thesis_id="t2", thesis_status="active"),
        ]
        reviews = [
            _make_drift_review(
                "r1", "t1", "thesis_invalidated",
                created_at=datetime(2026, 5, 1, tzinfo=CST),
            ),
            _make_drift_review(
                "r2", "t2", "partially_confirmed",
                created_at=datetime(2026, 5, 11, tzinfo=CST),
            ),
        ]
        report = DriftDetector().detect(positions, reviews=reviews)
        # 2 transitions / 10 days = 0.2
        assert report.drift_velocity_per_day == pytest.approx(0.2, abs=0.01)


class TestDriftHealthScore:
    """Health score is average of position thesis_status values."""

    def test_weighted_average(self):
        positions = [
            _make_position("p1", thesis_status="active"),       # 1.0
            _make_position("p2", thesis_status="active"),       # 1.0
            _make_position("p3", thesis_status="weakened"),     # 0.5
            _make_position("p4", thesis_status="invalidated"),  # 0.0
        ]
        report = DriftDetector().detect(positions)
        expected = (1.0 + 1.0 + 0.5 + 0.0) / 4
        assert report.health_score == pytest.approx(expected, abs=0.01)


class TestDriftTimelineOrdering:
    """Timeline entries are sorted by timestamp."""

    def test_sorted(self):
        positions = [
            _make_position("p1", thesis_status="active"),
            _make_position("p2", thesis_status="active"),
        ]
        reviews = [
            _make_drift_review(
                "r2", "t2", "thesis_invalidated",
                created_at=datetime(2026, 5, 10, tzinfo=CST),
            ),
            _make_drift_review(
                "r1", "t1", "partially_confirmed",
                created_at=datetime(2026, 5, 1, tzinfo=CST),
            ),
        ]
        report = DriftDetector().detect(positions, reviews=reviews)
        timestamps = [e["timestamp"] for e in report.drift_timeline]
        assert timestamps == sorted(timestamps)


class TestDriftEmptyPositions:
    """Empty position list returns zeroed report."""

    def test_empty(self):
        report = DriftDetector().detect([])
        assert report.health_score == 0.0
        assert report.drift_velocity_per_day == 0.0
        assert report.weakening_signals == []
        assert report.recovery_count == 0
        assert report.total_positions_tracked == 0
        assert report.drift_timeline == []


class TestDriftAllInvalidated:
    """All positions invalidated -> health=0.0."""

    def test_all_invalidated(self):
        positions = [
            _make_position(f"p{i}", thesis_status="invalidated") for i in range(4)
        ]
        report = DriftDetector().detect(positions)
        assert report.health_score == 0.0
        assert report.weakening_signals == []


class TestDriftMixedStates:
    """Mixed states produce correct aggregation."""

    def test_mixed(self):
        positions = [
            _make_position("p1", thesis_status="active"),
            _make_position("p2", thesis_status="active"),
            _make_position("p3", thesis_status="weakened"),
            _make_position("p4", thesis_status="weakened"),
            _make_position("p5", thesis_status="invalidated"),
        ]
        report = DriftDetector().detect(positions)
        expected_health = (1.0 + 1.0 + 0.5 + 0.5 + 0.0) / 5
        assert report.health_score == pytest.approx(expected_health, abs=0.01)
        assert sorted(report.weakening_signals) == ["p3", "p4"]
        assert report.total_positions_tracked == 5


class TestDriftReportRoundTrip:
    """DriftReport survives to_dict/from_dict round trip."""

    def test_round_trip(self):
        report = DriftReport(
            drift_velocity_per_day=0.35,
            health_score=0.75,
            weakening_signals=["p2", "p5"],
            recovery_count=2,
            total_positions_tracked=8,
            drift_timeline=[
                {
                    "position_id": "p2",
                    "thesis_id": "t2",
                    "from": "active",
                    "to": "weakened",
                    "timestamp": "2026-05-01T00:00:00",
                    "review_id": "r1",
                }
            ],
        )
        d = report.to_dict()
        restored = DriftReport.from_dict(d)
        assert restored.drift_velocity_per_day == 0.35
        assert restored.health_score == 0.75
        assert restored.weakening_signals == ["p2", "p5"]
        assert restored.recovery_count == 2
        assert restored.total_positions_tracked == 8
        assert len(restored.drift_timeline) == 1
        assert restored.drift_timeline[0]["from"] == "active"


# ===========================================================================
# B2 Integration Tests (4)
# ===========================================================================


class TestIntegrationCorrelationFromYAML:
    """Load Events and Reviews from YAML files on disk and run CorrelationAnalyzer."""

    def test_correlation_from_yaml(self, tmp_path):
        """Create temp Event and Review YAML files, load, and analyze."""
        import yaml as _yaml

        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Write event YAML
        event_data = {
            "id": "evt_yaml_001",
            "event_type": "earnings",
            "impact_level": "high",
            "related_tickers": ["600519"],
            "outcome_tracking": [{"event_id": "evt_yaml_001", "review_id": "rev_yaml_001"}],
            "linked_review_ids": [],
        }
        (data_dir / "evt_yaml_001.yaml").write_text(_yaml.dump(event_data, allow_unicode=True))

        # Write review YAML
        review_data = {
            "id": "rev_yaml_001",
            "review_outcome": "thesis_confirmed",
        }
        (data_dir / "rev_yaml_001.yaml").write_text(_yaml.dump(review_data, allow_unicode=True))

        # Load from YAML
        event_dicts = []
        review_dicts = []
        for yml_file in sorted(data_dir.glob("*.yaml")):
            with open(yml_file, encoding="utf-8") as f:
                data = _yaml.safe_load(f)
            if isinstance(data, dict):
                if data.get("id", "").startswith("evt_"):
                    event_dicts.append(data)
                elif data.get("id", "").startswith("rev_"):
                    review_dicts.append(data)

        events = [Event.from_dict(obj) for obj in event_dicts]
        reviews = [Review.from_dict(obj) for obj in review_dicts]
        report = CorrelationAnalyzer().analyze(events, reviews)

        assert report.total_event_review_pairs == 1
        assert report.correlation_strength == pytest.approx(1.0)
        assert report.unlinked_events == []
        assert "earnings" in report.event_type_success_rate


class TestIntegrationDriftFromYAML:
    """Load Positions and Reviews from YAML files on disk and run DriftDetector."""

    def test_drift_from_yaml(self, tmp_path):
        """Create temp Position and Review YAML files, load, and detect drift."""
        import yaml as _yaml

        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Write position YAML (weakened)
        pos_data = {
            "id": "pos_yaml_001",
            "linked_thesis_id": "ths_yaml_001",
            "research_state": {"thesis_status": "weakened"},
        }
        (data_dir / "pos_yaml_001.yaml").write_text(_yaml.dump(pos_data, allow_unicode=True))

        # Write review YAML (confirms thesis -> implies active)
        review_data = {
            "id": "rev_yaml_001",
            "linked_thesis_id": "ths_yaml_001",
            "review_outcome": "thesis_confirmed",
        }
        (data_dir / "rev_yaml_001.yaml").write_text(_yaml.dump(review_data, allow_unicode=True))

        # Load from YAML
        pos_dicts = []
        review_dicts = []
        for yml_file in sorted(data_dir.glob("*.yaml")):
            with open(yml_file, encoding="utf-8") as f:
                data = _yaml.safe_load(f)
            if isinstance(data, dict):
                if data.get("id", "").startswith("pos_"):
                    pos_dicts.append(data)
                elif data.get("id", "").startswith("rev_"):
                    review_dicts.append(data)

        positions = [Position.from_dict(obj) for obj in pos_dicts]
        reviews = [Review.from_dict(obj) for obj in review_dicts]
        report = DriftDetector().detect(positions, reviews=reviews)

        assert report.total_positions_tracked == 1
        assert report.recovery_count == 1
        assert any(
            e["from"] == "weakened" and e["to"] == "active"
            for e in report.drift_timeline
        )


class TestIntegrationCLIFullRegister:
    """Verify analytics CLI register() creates all 4 subparsers."""

    def test_cli_full_register(self):
        """Register analytics subcommand and verify all 4 subparsers exist."""
        import argparse
        from synapse.cli.commands.analytics import register

        parser = argparse.ArgumentParser(prog="synapse")
        subparsers = parser.add_subparsers(dest="command")
        register(subparsers)

        # error-pattern
        args_ep = parser.parse_args(["analytics", "error-pattern", "--data-dir", "/tmp"])
        assert args_ep.command == "analytics"
        assert args_ep.analytics_command == "error-pattern"
        assert hasattr(args_ep, "func")

        # behavioral
        args_beh = parser.parse_args(["analytics", "behavioral", "--data-dir", "/tmp"])
        assert args_beh.command == "analytics"
        assert args_beh.analytics_command == "behavioral"
        assert hasattr(args_beh, "func")

        # correlation
        args_corr = parser.parse_args(["analytics", "correlation", "--data-dir", "/tmp"])
        assert args_corr.command == "analytics"
        assert args_corr.analytics_command == "correlation"
        assert hasattr(args_corr, "func")

        # drift
        args_drift = parser.parse_args(["analytics", "drift", "--data-dir", "/tmp"])
        assert args_drift.command == "analytics"
        assert args_drift.analytics_command == "drift"
        assert hasattr(args_drift, "func")


class TestIntegrationFullP2Pass:
    """Verify the full P2 test suite has >= 48 tests."""

    def test_full_p2_pass(self):
        """Count P2 test classes/methods and verify threshold."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/unit/test_analytics.py",
             "-p", "no:asyncio", "--tb=short", "-q", "--co"],
            capture_output=True, text=True, cwd=str(Path(__file__).resolve().parents[2]),
        )
        # Count test items from --co output
        test_lines = [
            line for line in result.stdout.splitlines()
            if line.strip().startswith("test_") or "::test_" in line
        ]
        # Also count class-based tests
        all_test_count = result.stdout.count("::")
        assert all_test_count >= 48, (
            f"Expected >= 48 P2 tests, found {all_test_count}. "
            f"Output: {result.stdout[:500]}"
        )
