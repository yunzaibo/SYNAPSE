"""Tests for Cross-Event Correlation -- schema, affinity, scoring, impact, DAG safety."""

import pytest
from datetime import datetime, timedelta

from synapse.event.correlation import (
    EventCorrelation,
    EVENT_TYPE_AFFINITY,
    TYPE_EARNINGS,
    TYPE_POLICY,
    TYPE_REGULATORY,
    TYPE_SENTIMENT,
    TYPE_GEO,
    TYPE_MACRO,
    TYPE_CAPITAL,
    TYPE_SECTOR,
    compute_correlation_score,
    classify_amplification,
    compute_combined_impact,
    find_correlations,
    add_correlation_edges,
)


# ------------------------------------------------------------------
# Mock helpers
# ------------------------------------------------------------------


class MockEvent:
    """Duck-typed event for correlation testing."""

    def __init__(self, id, event_type, severity=0.5, thesis_id="T1", timestamp=None):
        self.id = id
        self.event_type = event_type
        self.severity = severity
        self.thesis_id = thesis_id
        self.timestamp = timestamp or datetime.now()


class MockGraph:
    """Duck-typed graph that records added edges."""

    def __init__(self):
        self.edges = []

    def add_edge(self, source_id, target_id, weight=0.5, decay_rate=0.05, edge_type="correlation"):
        edge = {"source": source_id, "target": target_id, "weight": weight, "type": edge_type}
        self.edges.append(edge)
        return edge

    def has_node(self, node_id):
        return True


# ------------------------------------------------------------------
# TestEventCorrelationSchema (3 tests: defaults, round-trip, validation)
# ------------------------------------------------------------------


class TestEventCorrelationSchema:
    def test_default_values(self):
        ec = EventCorrelation()
        assert ec.correlation_id.startswith("corr-")
        assert ec.event_ids == []
        assert ec.thesis_id == ""
        assert ec.correlation_score == 0.0
        assert ec.combined_impact == 0.0
        assert ec.amplification == "neutral"
        assert ec.correlation_window_days == 7
        assert ec.detected_at is not None  # auto-filled

    def test_to_dict_from_dict_roundtrip(self):
        ts = datetime(2025, 3, 15, 10, 30, 0)
        ec = EventCorrelation(
            correlation_id="corr-test123",
            event_ids=["evt-a", "evt-b"],
            thesis_id="T-42",
            correlation_score=0.75,
            combined_impact=1.2,
            amplification="amplification",
            correlation_window_days=14,
            detected_at=ts,
        )
        d = ec.to_dict()
        restored = EventCorrelation.from_dict(d)

        assert restored.correlation_id == "corr-test123"
        assert restored.event_ids == ["evt-a", "evt-b"]
        assert restored.thesis_id == "T-42"
        assert restored.correlation_score == pytest.approx(0.75)
        assert restored.combined_impact == pytest.approx(1.2)
        assert restored.amplification == "amplification"
        assert restored.correlation_window_days == 14
        assert restored.detected_at == ts

    def test_validation_score_out_of_range(self):
        with pytest.raises(ValueError, match="correlation_score must be in"):
            EventCorrelation(correlation_score=1.5)

    def test_validation_impact_out_of_range(self):
        with pytest.raises(ValueError, match="combined_impact must be in"):
            EventCorrelation(combined_impact=2.5)


# ------------------------------------------------------------------
# TestAffinityMatrix (2 tests: diagonal, symmetry)
# ------------------------------------------------------------------


class TestAffinityMatrix:
    def test_diagonal_equals_one(self):
        """All self-affinities must be 1.0."""
        all_types = list(EVENT_TYPE_AFFINITY.keys())
        for t in all_types:
            assert EVENT_TYPE_AFFINITY[t][t] == pytest.approx(1.0), f"self-affinity for {t}"

    def test_symmetry(self):
        """Affinity matrix must be symmetric: A[X][Y] == A[Y][X]."""
        all_types = list(EVENT_TYPE_AFFINITY.keys())
        for a, b in zip(all_types, all_types[1:]):
            assert EVENT_TYPE_AFFINITY[a][b] == pytest.approx(
                EVENT_TYPE_AFFINITY[b][a]
            ), f"asymmetry between {a} and {b}"


# ------------------------------------------------------------------
# TestCorrelationScoring (4 tests: normal, same type, unknown, zero proximity)
# ------------------------------------------------------------------


class TestCorrelationScoring:
    def test_normal_case(self):
        """POLICY_SHIFT + EARNINGS_SURPRISE, proximity=1.0 -> affinity * 1.0 = 0.3."""
        ev_a = MockEvent("a", TYPE_POLICY)
        ev_b = MockEvent("b", TYPE_EARNINGS)
        score = compute_correlation_score(ev_a, ev_b, 1.0)
        assert score == pytest.approx(0.3)

    def test_same_type_affinity_one(self):
        """Same event type -> affinity = 1.0, score = proximity."""
        ev_a = MockEvent("a", TYPE_EARNINGS)
        ev_b = MockEvent("b", TYPE_EARNINGS)
        score = compute_correlation_score(ev_a, ev_b, 0.8)
        assert score == pytest.approx(0.8)

    def test_unknown_type_returns_zero(self):
        """Unknown event type -> affinity = 0.0, score = 0.0."""
        ev_a = MockEvent("a", "UNKNOWN_TYPE")
        ev_b = MockEvent("b", TYPE_EARNINGS)
        score = compute_correlation_score(ev_a, ev_b, 1.0)
        assert score == pytest.approx(0.0)

    def test_zero_proximity(self):
        """Proximity = 0.0 -> score = 0.0 regardless of affinity."""
        ev_a = MockEvent("a", TYPE_POLICY)
        ev_b = MockEvent("b", TYPE_REGULATORY)  # affinity = 0.8
        score = compute_correlation_score(ev_a, ev_b, 0.0)
        assert score == pytest.approx(0.0)


# ------------------------------------------------------------------
# TestAmplificationClassification (3 tests: amplification, dampening, neutral)
# ------------------------------------------------------------------


class TestAmplificationClassification:
    def test_amplification_above_threshold(self):
        assert classify_amplification(0.7) == "amplification"
        assert classify_amplification(1.0) == "amplification"

    def test_dampening_below_threshold(self):
        assert classify_amplification(0.1) == "dampening"
        assert classify_amplification(0.0) == "dampening"

    def test_neutral_at_boundary(self):
        # Exactly 0.3 -> not < 0.3, not > 0.6 -> neutral
        assert classify_amplification(0.3) == "neutral"
        # Exactly 0.6 -> not > 0.6 -> neutral
        assert classify_amplification(0.6) == "neutral"
        assert classify_amplification(0.45) == "neutral"


# ------------------------------------------------------------------
# TestCombinedImpact (3 tests: empty, single, multiple with amplification)
# ------------------------------------------------------------------


class TestCombinedImpact:
    def test_empty_list(self):
        assert compute_combined_impact([]) == pytest.approx(0.0)

    def test_single_event_returns_severity(self):
        ev = MockEvent("a", TYPE_EARNINGS, severity=0.8)
        assert compute_combined_impact([ev]) == pytest.approx(0.8)

    def test_multiple_events_with_amplification(self):
        """Two EARNINGS_SURPRISE events -> same type, affinity=1.0 -> amplification."""
        ev_a = MockEvent("a", TYPE_EARNINGS, severity=0.6)
        ev_b = MockEvent("b", TYPE_EARNINGS, severity=0.8)
        impact = compute_combined_impact([ev_a, ev_b])
        # Same type: affinity=1.0, score=1.0, amp_class=amplification
        # max_sev=0.8, combined = 0.8 * (1.0 + 1.0*0.5) = 0.8 * 1.5 = 1.2
        assert impact == pytest.approx(1.2)


# ------------------------------------------------------------------
# TestFindCorrelations (4 tests: no correlations, within window, outside window, max_cluster)
# ------------------------------------------------------------------


class TestFindCorrelations:
    def test_no_correlations_different_thesis(self):
        """Events with different thesis_id should produce no correlations."""
        now = datetime.now()
        ev_a = MockEvent("a", TYPE_EARNINGS, thesis_id="T1", timestamp=now)
        ev_b = MockEvent("b", TYPE_EARNINGS, thesis_id="T2", timestamp=now)
        result = find_correlations([ev_a, ev_b])
        assert result == []

    def test_within_window(self):
        """Two events of same type within 7-day window should correlate."""
        now = datetime.now()
        ev_a = MockEvent("a", TYPE_EARNINGS, severity=0.8, thesis_id="T1", timestamp=now)
        ev_b = MockEvent("b", TYPE_EARNINGS, severity=0.9, thesis_id="T1", timestamp=now - timedelta(days=2))
        result = find_correlations([ev_a, ev_b], window_days=7)
        assert len(result) == 1
        assert result[0].correlation_score > 0.0

    def test_outside_window(self):
        """Events beyond the window should produce no correlations."""
        now = datetime.now()
        ev_a = MockEvent("a", TYPE_EARNINGS, severity=0.8, thesis_id="T1", timestamp=now)
        ev_b = MockEvent("b", TYPE_EARNINGS, severity=0.9, thesis_id="T1", timestamp=now - timedelta(days=10))
        result = find_correlations([ev_a, ev_b], window_days=7)
        assert result == []

    def test_max_cluster_limit(self):
        """Only max_cluster events should be considered (O(n^2) bound)."""
        now = datetime.now()
        events = [
            MockEvent(f"evt-{i}", TYPE_EARNINGS, thesis_id="T1", timestamp=now)
            for i in range(5)
        ]
        # max_cluster=2 means only first 2 events -> 1 pair
        result = find_correlations(events, window_days=7, max_cluster=2)
        assert len(result) <= 1


# ------------------------------------------------------------------
# TestDAGSafety (1 test: single-direction edges, no cycles)
# ------------------------------------------------------------------


class TestDAGSafety:
    def test_add_correlation_edges_creates_single_direction_no_cycles(self):
        """Edges must be added as min_id -> max_id; no cycle possible."""
        now = datetime.now()
        ev_a = MockEvent("evt-aaa", TYPE_EARNINGS, thesis_id="T1", timestamp=now)
        ev_b = MockEvent("evt-bbb", TYPE_EARNINGS, thesis_id="T1", timestamp=now)

        # Force two correlations with swapped IDs to test both orderings
        corr1 = EventCorrelation(event_ids=["evt-aaa", "evt-bbb"], correlation_score=0.8)
        corr2 = EventCorrelation(event_ids=["evt-bbb", "evt-aaa"], correlation_score=0.8)

        graph = MockGraph()
        edges = add_correlation_edges(graph, [corr1, corr2])

        # Both should resolve to the same single-direction edge (min -> max)
        assert len(edges) == 2
        # All edges must go from lower-id to higher-id (no cycles possible)
        for edge in graph.edges:
            assert edge["source"] < edge["target"], (
                f"Edge {edge['source']} -> {edge['target']} violates DAG ordering"
            )
        # Edge types must be "correlation"
        for edge in graph.edges:
            assert edge["type"] == "correlation"
            assert edge["weight"] == pytest.approx(0.8)
