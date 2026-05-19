"""Tests for Sentiment Propagation -- schema, R0, cascade detection, build."""

import pytest

from synapse.event.sentiment import (
    SentimentPropagation,
    compute_viral_coefficient,
    detect_cascade,
    build_sentiment_propagation,
)


# ------------------------------------------------------------------
# Mock helpers
# ------------------------------------------------------------------


class MockEdge:
    """Duck-typed edge for testing without real PropagationGraph."""

    def __init__(self, target_id, edge_type="sentiment", weight=0.5):
        self.target_id = target_id
        self.edge_type = edge_type
        self.weight = weight


class MockGraph:
    """Duck-typed graph: node -> outgoing edges mapping."""

    def __init__(self, edges_map):
        self._edges = edges_map  # dict[str, list[MockEdge]]

    def has_node(self, node_id):
        if node_id in self._edges:
            return True
        return any(
            e.target_id == node_id
            for edges in self._edges.values()
            for e in edges
        )

    def get_outgoing_edges(self, node_id):
        return self._edges.get(node_id, [])


class MockEvent:
    """Duck-typed event for build_sentiment_propagation."""

    def __init__(self, event_id, severity=0.5):
        self.id = event_id
        self.severity = severity


# ------------------------------------------------------------------
# TestSentimentPropagation (3 tests: defaults, round-trip, validation)
# ------------------------------------------------------------------


class TestSentimentPropagation:
    def test_default_values(self):
        sp = SentimentPropagation()
        assert sp.viral_coefficient == 0.0
        assert sp.cascade_depth == 0
        assert sp.cascade_count == 0
        assert sp.intensity_at_source == 0.5
        assert sp.intensity_decay == {}
        assert sp.propagation_window_hours == 24
        assert sp.detected_at is not None  # auto-filled

    def test_to_dict_from_dict_roundtrip(self):
        sp = SentimentPropagation(
            root_event_id="evt-1",
            viral_coefficient=1.5,
            cascade_depth=3,
            cascade_count=5,
            intensity_at_source=0.8,
            intensity_decay={"child-a": 0.6, "child-b": 0.3},
            propagation_window_hours=48,
        )
        d = sp.to_dict()
        restored = SentimentPropagation.from_dict(d)

        assert restored.root_event_id == "evt-1"
        assert restored.viral_coefficient == 1.5
        assert restored.cascade_depth == 3
        assert restored.cascade_count == 5
        assert restored.intensity_at_source == 0.8
        assert restored.intensity_decay == {"child-a": 0.6, "child-b": 0.3}
        assert restored.propagation_window_hours == 48

    def test_validation_negative_viral_coefficient(self):
        with pytest.raises(ValueError, match="viral_coefficient must be >= 0"):
            SentimentPropagation(viral_coefficient=-0.1)

    def test_validation_intensity_out_of_range(self):
        with pytest.raises(ValueError, match="intensity_at_source must be <= 1"):
            SentimentPropagation(intensity_at_source=1.5)


# ------------------------------------------------------------------
# TestViralCoefficient (3 tests: normal, no edges, single node)
# ------------------------------------------------------------------


class TestViralCoefficient:
    def test_no_edges_returns_zero(self):
        """Root with no outgoing sentiment edges -> R0 = 0."""
        graph = MockGraph({"root": []})
        assert compute_viral_coefficient(graph, "root") == 0.0

    def test_single_node_not_in_graph(self):
        """Root not present in graph -> R0 = 0."""
        graph = MockGraph({"other": []})
        assert compute_viral_coefficient(graph, "missing") == 0.0

    def test_linear_chain_r0_zero(self):
        """A -> B -> C: only 1 direct child, R0 = (2-1)/1 = 1.0."""
        graph = MockGraph({
            "A": [MockEdge("B")],
            "B": [MockEdge("C")],
        })
        r0 = compute_viral_coefficient(graph, "A")
        # total_activated = 2 (B, C), direct_children = 1 (B)
        # R0 = (2 - 1) / 1 = 1.0
        assert r0 == pytest.approx(1.0)

    def test_diamond_graph(self):
        """A -> B,C; B -> D; C -> D.  R0 = (3-1)/2 = 1.0."""
        graph = MockGraph({
            "A": [MockEdge("B"), MockEdge("C")],
            "B": [MockEdge("D")],
            "C": [MockEdge("D")],
        })
        r0 = compute_viral_coefficient(graph, "A")
        # total_activated = 3 (B, C, D), direct_children = 2 (B, C)
        # R0 = (3 - 1) / 2 = 1.0
        assert r0 == pytest.approx(1.0)

    def test_broad_spread_r0_high(self):
        """A -> B,C,D; each child has 2 children.  R0 = (9-1)/3 ~ 2.667."""
        graph = MockGraph({
            "A": [MockEdge("B"), MockEdge("C"), MockEdge("D")],
            "B": [MockEdge("E"), MockEdge("F")],
            "C": [MockEdge("G"), MockEdge("H")],
            "D": [MockEdge("I"), MockEdge("J")],
        })
        r0 = compute_viral_coefficient(graph, "A")
        # total_activated = 9 (B..J), direct_children = 3 (B, C, D)
        # R0 = (9 - 1) / 3 = 8/3
        assert r0 == pytest.approx(8 / 3)

    def test_non_sentiment_edges_ignored(self):
        """Only edges with edge_type='sentiment' are traversed."""
        graph = MockGraph({
            "A": [MockEdge("B", edge_type="causal")],
            "B": [MockEdge("C")],
        })
        r0 = compute_viral_coefficient(graph, "A")
        # B is not reached via sentiment edge, so total_activated = 0
        assert r0 == 0.0


# ------------------------------------------------------------------
# TestCascadeDetection (3 tests)
# ------------------------------------------------------------------


class TestCascadeDetection:
    def test_cascade_detected(self):
        """R0 > 1.0 AND depth >= 2 -> cascade."""
        sp = SentimentPropagation(
            root_event_id="evt-1",
            viral_coefficient=1.5,
            cascade_depth=3,
        )
        assert detect_cascade(sp) is True

    def test_no_cascade_low_r0(self):
        """R0 < 1.0 -> no cascade even with depth >= 2."""
        sp = SentimentPropagation(
            root_event_id="evt-2",
            viral_coefficient=0.8,
            cascade_depth=3,
        )
        assert detect_cascade(sp) is False

    def test_no_cascade_shallow_depth(self):
        """R0 > 1.0 but depth < 2 -> no cascade."""
        sp = SentimentPropagation(
            root_event_id="evt-3",
            viral_coefficient=2.0,
            cascade_depth=1,
        )
        assert detect_cascade(sp) is False

    def test_cascade_boundary_r0_exactly_one(self):
        """R0 == 1.0 (not >) and depth >= 2 -> no cascade."""
        sp = SentimentPropagation(
            root_event_id="evt-4",
            viral_coefficient=1.0,
            cascade_depth=2,
        )
        assert detect_cascade(sp) is False


# ------------------------------------------------------------------
# TestBuildSentimentPropagation (1 test)
# ------------------------------------------------------------------


class TestBuildSentimentPropagation:
    def test_build_with_mock_graph(self):
        """build_sentiment_propagation populates R0, depth, intensity decay."""
        root = MockEvent("root-1", severity=1.0)
        graph = MockGraph({
            "root-1": [MockEdge("child-a", weight=0.8), MockEdge("child-b", weight=0.6)],
            "child-a": [MockEdge("grandchild", weight=0.5)],
        })

        sp = build_sentiment_propagation(root, child_events=[], graph=graph)

        assert sp.root_event_id == "root-1"
        assert sp.intensity_at_source == 1.0
        assert sp.viral_coefficient > 0
        assert sp.cascade_depth >= 2
        assert "child-a" in sp.intensity_decay
        assert "child-b" in sp.intensity_decay
        assert 0.0 < sp.intensity_decay["child-a"] < 1.0
