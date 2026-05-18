"""Tests for ImpactAnalyzer -- 4 impact metrics + ImpactReport."""

from __future__ import annotations

import time
import uuid

import pytest

from synapse.core.schemas.event import Event, EventType, PropagationState
from synapse.event.graph import PropagationGraph
from synapse.event.impact import ImpactAnalyzer, ImpactReport
from synapse.event.lifecycle import compute_decay


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    *,
    severity: float = 0.9,
    confidence: float = 0.8,
    decay_rate: float = 0.1,
    propagation_state: PropagationState = PropagationState.DETECTED,
) -> Event:
    """Create a test Event with unique id."""
    return Event(
        id=str(uuid.uuid4()),
        event_type=EventType.EARNINGS,
        severity=severity,
        confidence=confidence,
        decay_rate=decay_rate,
        propagation_state=propagation_state,
    )


def _build_two_hop_graph() -> tuple[PropagationGraph, str, str, str]:
    """Build graph: event -> thesis_A (0.8) -> position_X (0.7).

    Returns (graph, event_id, thesis_a_id, position_x_id).
    """
    graph = PropagationGraph()
    event_id = str(uuid.uuid4())
    thesis_a_id = str(uuid.uuid4())
    position_x_id = str(uuid.uuid4())

    graph.add_edge(event_id, thesis_a_id, weight=0.8)
    graph.add_edge(thesis_a_id, position_x_id, weight=0.7)
    return graph, event_id, thesis_a_id, position_x_id


# ---------------------------------------------------------------------------
# TestDirectImpact
# ---------------------------------------------------------------------------


class TestDirectImpact:
    """Single-hop impact: event -> direct neighbors."""

    def test_direct_impact_two_neighbors(self) -> None:
        """event -> thesis_A (0.8), event -> thesis_B (0.6)."""
        graph = PropagationGraph()
        event_id = str(uuid.uuid4())
        thesis_a_id = str(uuid.uuid4())
        thesis_b_id = str(uuid.uuid4())

        graph.add_edge(event_id, thesis_a_id, weight=0.8)
        graph.add_edge(event_id, thesis_b_id, weight=0.6)

        event = _make_event(severity=0.9, confidence=0.8, decay_rate=0.1)
        event.id = event_id

        analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)
        result = analyzer.compute_direct_impact()

        # severity * confidence * decay(1.0, 0.1, 0) * weight
        # decay(1.0, 0.1, 0) = 1.0
        # thesis_A: 0.9 * 0.8 * 1.0 * 0.8 = 0.576
        # thesis_B: 0.9 * 0.8 * 1.0 * 0.6 = 0.432
        assert len(result) == 2
        assert result[thesis_a_id] == pytest.approx(0.576, abs=1e-6)
        assert result[thesis_b_id] == pytest.approx(0.432, abs=1e-6)


# ---------------------------------------------------------------------------
# TestCascadedImpact
# ---------------------------------------------------------------------------


class TestCascadedImpact:
    """Multi-hop impact: event -> thesis -> position."""

    def test_cascaded_impact_two_hops(self) -> None:
        """event -> thesis_A (0.8) -> position_X (0.7)."""
        graph, event_id, thesis_a_id, position_x_id = _build_two_hop_graph()

        event = _make_event(severity=0.9, confidence=0.8, decay_rate=0.1)
        event.id = event_id

        analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)
        result = analyzer.compute_cascaded_impact()

        # position_X path weight = 0.8 * 0.7 = 0.56
        # score = 0.9 * 0.8 * 1.0 * 0.56 = 0.4032
        # thesis_A also appears (direct hop)
        assert result[position_x_id] == pytest.approx(0.4032, abs=1e-6)
        assert result[thesis_a_id] == pytest.approx(0.576, abs=1e-6)


# ---------------------------------------------------------------------------
# TestDecayAccuracy
# ---------------------------------------------------------------------------


class TestDecayAccuracy:
    """Verify decay factor is correctly applied."""

    def test_decay_at_10_days(self) -> None:
        """Event with decay_rate=0.1, days=10 should reflect e^(-1.0) decay."""
        graph, event_id, thesis_a_id, _ = _build_two_hop_graph()

        event = _make_event(severity=0.9, confidence=0.8, decay_rate=0.1)
        event.id = event_id

        analyzer = ImpactAnalyzer(graph, event, days_since_event=10.0)
        result = analyzer.compute_direct_impact()

        # decay_factor = e^(-0.1 * 10) = e^(-1.0) ~ 0.367879
        expected_decay = compute_decay(1.0, 0.1, 10.0)
        assert expected_decay == pytest.approx(0.367879, abs=1e-4)

        # thesis_A: 0.9 * 0.8 * 0.367879 * 0.8
        expected_score = 0.9 * 0.8 * expected_decay * 0.8
        assert result[thesis_a_id] == pytest.approx(expected_score, abs=1e-4)


# ---------------------------------------------------------------------------
# TestAggregateImpact
# ---------------------------------------------------------------------------


class TestAggregateImpact:
    """Sum impacts per position."""

    def test_aggregate_multiple_positions(self) -> None:
        """Verify aggregation over cascaded impacts."""
        graph = PropagationGraph()
        event_id = str(uuid.uuid4())
        thesis_id = str(uuid.uuid4())
        pos_a = str(uuid.uuid4())
        pos_b = str(uuid.uuid4())

        graph.add_edge(event_id, thesis_id, weight=0.8)
        graph.add_edge(thesis_id, pos_a, weight=0.7)
        graph.add_edge(thesis_id, pos_b, weight=0.5)

        event = _make_event(severity=0.9, confidence=0.8, decay_rate=0.1)
        event.id = event_id

        analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)
        result = analyzer.compute_aggregate_impact()

        # pos_a: 0.9 * 0.8 * 1.0 * (0.8 * 0.7) = 0.4032
        # pos_b: 0.9 * 0.8 * 1.0 * (0.8 * 0.5) = 0.288
        assert result[pos_a] == pytest.approx(0.4032, abs=1e-6)
        assert result[pos_b] == pytest.approx(0.288, abs=1e-6)

    def test_aggregate_with_position_filter(self) -> None:
        """Filter aggregate to specific position_ids."""
        graph = PropagationGraph()
        event_id = str(uuid.uuid4())
        thesis_id = str(uuid.uuid4())
        pos_a = str(uuid.uuid4())
        pos_b = str(uuid.uuid4())

        graph.add_edge(event_id, thesis_id, weight=0.8)
        graph.add_edge(thesis_id, pos_a, weight=0.7)
        graph.add_edge(thesis_id, pos_b, weight=0.5)

        event = _make_event(severity=0.9, confidence=0.8, decay_rate=0.1)
        event.id = event_id

        analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)
        result = analyzer.compute_aggregate_impact(position_ids=[pos_a])

        assert len(result) == 1
        assert pos_a in result
        assert pos_b not in result


# ---------------------------------------------------------------------------
# TestRiskAdjustedImpact
# ---------------------------------------------------------------------------


class TestRiskAdjustedImpact:
    """Risk-adjusted = aggregate / volatility."""

    def test_risk_adjusted_divides_by_volatility(self) -> None:
        """Verify division by portfolio_volatility."""
        graph = PropagationGraph()
        event_id = str(uuid.uuid4())
        thesis_id = str(uuid.uuid4())
        pos_a = str(uuid.uuid4())

        graph.add_edge(event_id, thesis_id, weight=0.8)
        graph.add_edge(thesis_id, pos_a, weight=0.7)

        event = _make_event(severity=0.9, confidence=0.8, decay_rate=0.1)
        event.id = event_id

        analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)
        aggregate = analyzer.compute_aggregate_impact()
        risk_adj = analyzer.compute_risk_adjusted_impact(portfolio_volatility=2.0)

        expected = aggregate[pos_a] / 2.0
        assert risk_adj[pos_a] == pytest.approx(expected, abs=1e-6)

    def test_risk_adjusted_zero_volatility_returns_empty(self) -> None:
        """volatility <= 0 should return empty dict."""
        graph = PropagationGraph()
        event_id = str(uuid.uuid4())
        graph.add_edge(event_id, "t1", weight=0.8)

        event = _make_event()
        event.id = event_id

        analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)
        result = analyzer.compute_risk_adjusted_impact(portfolio_volatility=0.0)
        assert result == {}


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases: expired events, zero-weight paths."""

    def test_expired_event_yields_zero_impact(self) -> None:
        """Expired event should produce zero impacts everywhere."""
        graph, event_id, thesis_a_id, position_x_id = _build_two_hop_graph()

        event = _make_event(
            severity=0.9,
            confidence=0.8,
            decay_rate=0.1,
            propagation_state=PropagationState.EXPIRED,
        )
        event.id = event_id

        analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)
        direct = analyzer.compute_direct_impact()
        cascaded = analyzer.compute_cascaded_impact()

        assert direct == {}
        assert cascaded == {}

    def test_zero_weight_path_yields_zero_impact(self) -> None:
        """Edge with weight=0 should produce zero impact."""
        graph = PropagationGraph()
        event_id = str(uuid.uuid4())
        thesis_id = str(uuid.uuid4())

        graph.add_edge(event_id, thesis_id, weight=0.0)

        event = _make_event(severity=0.9, confidence=0.8)
        event.id = event_id

        analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)
        result = analyzer.compute_direct_impact()

        assert result == {}

    def test_event_not_in_graph_returns_empty(self) -> None:
        """Event id not in graph nodes should return empty dicts."""
        graph = PropagationGraph()
        graph.add_edge("other1", "other2", weight=0.8)

        event = _make_event()
        event.id = "nonexistent_event"

        analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)
        assert analyzer.compute_direct_impact() == {}
        assert analyzer.compute_cascaded_impact() == {}


# ---------------------------------------------------------------------------
# TestImpactReport
# ---------------------------------------------------------------------------


class TestImpactReport:
    """ImpactReport dataclass serialization."""

    def test_to_dict_and_from_dict_roundtrip(self) -> None:
        """Verify to_dict -> from_dict preserves all fields."""
        report = ImpactReport(
            event_id="evt-001",
            direct_impacts={"thesis_A": 0.576},
            cascaded_impacts={"pos_X": 0.4032},
            aggregate_by_position={"pos_X": 0.4032},
            max_impact_entity="thesis_A",
            total_impact=0.9792,
            computed_at="2026-05-18",
        )
        d = report.to_dict()
        restored = ImpactReport.from_dict(d)

        assert restored.event_id == "evt-001"
        assert restored.direct_impacts == {"thesis_A": 0.576}
        assert restored.cascaded_impacts == {"pos_X": 0.4032}
        assert restored.total_impact == 0.9792

    def test_compute_full_report(self) -> None:
        """Full report populates all fields correctly."""
        graph, event_id, thesis_a_id, position_x_id = _build_two_hop_graph()

        event = _make_event(severity=0.9, confidence=0.8, decay_rate=0.1)
        event.id = event_id

        analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)
        report = analyzer.compute_full_report()

        assert report.event_id == event_id
        assert thesis_a_id in report.direct_impacts
        assert position_x_id in report.cascaded_impacts
        assert report.max_impact_entity != ""
        assert report.total_impact > 0
        assert report.computed_at != ""


# ---------------------------------------------------------------------------
# TestPerformance
# ---------------------------------------------------------------------------


class TestPerformance:
    """Performance sanity checks."""

    def test_1000_node_chain_under_150ms(self) -> None:
        """Chain graph of 1000 nodes should analyze in < 150ms."""
        graph = PropagationGraph()
        node_ids = [str(uuid.uuid4()) for _ in range(1000)]
        for i in range(len(node_ids) - 1):
            graph.add_edge(node_ids[i], node_ids[i + 1], weight=0.5)

        event = _make_event(severity=0.9, confidence=0.8, decay_rate=0.1)
        event.id = node_ids[0]

        analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)

        start = time.perf_counter()
        analyzer.compute_cascaded_impact()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 150, f"Took {elapsed_ms:.1f}ms, limit 150ms"
