"""Tests for PropagationGraph -- DAG, cycle detection, topological sort, traversal."""

import pytest

from synapse.event.graph import PropagationGraph, PropagationEdge, TraversalNode


# ------------------------------------------------------------------
# TestGraphStructure (2 tests)
# ------------------------------------------------------------------


class TestGraphStructure:
    def test_add_edge_and_get_neighbors(self):
        g = PropagationGraph()
        g.add_edge("A", "B", weight=0.8)
        g.add_edge("A", "C", weight=0.6)
        g.add_edge("B", "D", weight=0.5)

        assert set(g.get_neighbors("A")) == {"B", "C"}
        assert set(g.get_neighbors("B")) == {"D"}
        assert g.get_neighbors("D") == []
        assert set(g.get_all_nodes()) == {"A", "B", "C", "D"}

    def test_remove_edge(self):
        g = PropagationGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "C")

        assert g.remove_edge("A", "B") is True
        assert g.get_neighbors("A") == ["C"]
        # Remove non-existent edge
        assert g.remove_edge("X", "Y") is False

    def test_get_edge(self):
        g = PropagationGraph()
        e = g.add_edge("A", "B", weight=0.9, edge_type="causal")
        found = g.get_edge("A", "B")
        assert found is not None
        assert found.weight == 0.9
        assert found.edge_type == "causal"
        assert found is e
        assert g.get_edge("B", "A") is None


# ------------------------------------------------------------------
# TestCycleDetection (3 tests)
# ------------------------------------------------------------------


class TestCycleDetection:
    def test_self_loop_rejected(self):
        g = PropagationGraph()
        g.add_edge("A", "B")  # need A in graph
        with pytest.raises(ValueError, match="Self-loop"):
            g.add_edge("A", "A")

    def test_two_node_cycle_rejected(self):
        g = PropagationGraph()
        g.add_edge("A", "B")
        with pytest.raises(ValueError, match="cycle"):
            g.add_edge("B", "A")

    def test_three_node_cycle_rejected(self):
        g = PropagationGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        # A -> B -> C, adding C -> A creates cycle
        with pytest.raises(ValueError, match="cycle"):
            g.add_edge("C", "A")

    def test_rejected_edges_audit_trail(self):
        g = PropagationGraph()
        g.add_edge("A", "B")
        with pytest.raises(ValueError):
            g.add_edge("B", "A")
        with pytest.raises(ValueError):
            g.add_edge("A", "A")

        rejected = g.get_rejected_edges()
        assert len(rejected) == 2
        assert rejected[0] == ("B", "A", "cycle")
        assert rejected[1] == ("A", "A", "self-loop")


# ------------------------------------------------------------------
# TestTopologicalSort (2 tests)
# ------------------------------------------------------------------


class TestTopologicalSort:
    def test_basic_topological_sort(self):
        g = PropagationGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "D")
        g.add_edge("C", "D")

        order = g.topological_sort()
        # A must come before B and C; B and C must come before D
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_topological_sort_deterministic(self):
        """Same graph structure always produces the same sorted order."""
        g1 = PropagationGraph()
        g1.add_edge("E", "D")
        g1.add_edge("E", "C")
        g1.add_edge("D", "B")
        g1.add_edge("C", "B")
        g1.add_edge("B", "A")

        g2 = PropagationGraph()
        g2.add_edge("E", "D")
        g2.add_edge("E", "C")
        g2.add_edge("D", "B")
        g2.add_edge("C", "B")
        g2.add_edge("B", "A")

        assert g1.topological_sort() == g2.topological_sort()

    def test_get_roots(self):
        g = PropagationGraph()
        g.add_edge("A", "B")
        g.add_edge("C", "B")
        g.add_edge("C", "D")

        roots = g.get_roots()
        assert roots == ["A", "C"]


# ------------------------------------------------------------------
# TestTraversal (2 tests)
# ------------------------------------------------------------------


class TestTraversal:
    def test_bfs_downstream(self):
        g = PropagationGraph()
        g.add_edge("A", "B", weight=0.8)
        g.add_edge("A", "C", weight=0.6)
        g.add_edge("B", "D", weight=0.5)
        g.add_edge("C", "D", weight=0.4)

        downstream = g.bfs_downstream("A")
        node_ids = {n.node_id for n in downstream}
        assert node_ids == {"B", "C", "D"}
        # B and C are at depth 1, D is at depth 2
        b_node = next(n for n in downstream if n.node_id == "B")
        assert b_node.depth == 1
        assert b_node.edge_weight == 0.8
        d_node = next(n for n in downstream if n.node_id == "D")
        assert d_node.depth == 2

    def test_bfs_upstream(self):
        g = PropagationGraph()
        g.add_edge("A", "C", weight=0.7)
        g.add_edge("B", "C", weight=0.6)
        g.add_edge("B", "D", weight=0.5)

        upstream = g.bfs_upstream("C")
        node_ids = {n.node_id for n in upstream}
        assert node_ids == {"A", "B"}
        a_node = next(n for n in upstream if n.node_id == "A")
        assert a_node.depth == 1
        assert a_node.edge_weight == 0.7

    def test_bfs_upstream_chain(self):
        g = PropagationGraph()
        g.add_edge("A", "B", weight=0.9)
        g.add_edge("B", "C", weight=0.8)
        g.add_edge("C", "D", weight=0.7)

        upstream = g.bfs_upstream("D")
        node_ids = [n.node_id for n in upstream]
        assert "C" in node_ids
        assert "B" in node_ids
        assert "A" in node_ids
        # Depths: C=1, B=2, A=3
        c_node = next(n for n in upstream if n.node_id == "C")
        b_node = next(n for n in upstream if n.node_id == "B")
        a_node = next(n for n in upstream if n.node_id == "A")
        assert c_node.depth == 1
        assert b_node.depth == 2
        assert a_node.depth == 3


# ------------------------------------------------------------------
# TestDepthLimit (1 test)
# ------------------------------------------------------------------


class TestDepthLimit:
    def test_depth_limit_enforced(self):
        g = PropagationGraph()
        # Build a chain of 6 edges: A -> B -> C -> D -> E -> F -> G
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("C", "D")
        g.add_edge("D", "E")
        g.add_edge("E", "F")
        g.add_edge("F", "G")

        # With max_depth=5, downstream from A should reach B..F but not G
        downstream = g.bfs_downstream("A", max_depth=5)
        node_ids = {n.node_id for n in downstream}
        assert "B" in node_ids
        assert "C" in node_ids
        assert "D" in node_ids
        assert "E" in node_ids
        assert "F" in node_ids
        assert "G" not in node_ids  # depth 6 exceeds limit


# ------------------------------------------------------------------
# TestDeterminism (1 test)
# ------------------------------------------------------------------


class TestDeterminism:
    def test_same_inputs_same_graph(self):
        """Adding edges in different orders yields the same graph structure."""
        g1 = PropagationGraph()
        g1.add_edge("A", "B", weight=0.5)
        g1.add_edge("B", "C", weight=0.6)
        g1.add_edge("A", "C", weight=0.7)

        g2 = PropagationGraph()
        g2.add_edge("A", "C", weight=0.7)
        g2.add_edge("A", "B", weight=0.5)
        g2.add_edge("B", "C", weight=0.6)

        # Same nodes
        assert g1.get_all_nodes() == g2.get_all_nodes()
        # Same neighbor sets (order may differ due to insertion order)
        assert set(g1.get_neighbors("A")) == set(g2.get_neighbors("A"))
        assert set(g1.get_neighbors("B")) == set(g2.get_neighbors("B"))
        # Same topological order (deterministic)
        assert g1.topological_sort() == g2.topological_sort()


# ------------------------------------------------------------------
# TestLifecycle (3 tests)
# ------------------------------------------------------------------


class TestLifecycle:
    def test_valid_transition(self):
        """DETECTED -> PROPAGATING -> SETTLED is a valid path."""
        from synapse.event.lifecycle import PropagationState, PropagationLifecycle

        lc = PropagationLifecycle("evt-1")
        assert lc.get_state() == PropagationState.DETECTED

        lc.transition(PropagationState.PROPAGATING)
        assert lc.get_state() == PropagationState.PROPAGATING

        lc.transition(PropagationState.SETTLED)
        assert lc.get_state() == PropagationState.SETTLED

    def test_invalid_transition_raises(self):
        """DETECTED -> SETTLED is not allowed; must go through PROPAGATING."""
        from synapse.event.lifecycle import PropagationState, PropagationLifecycle

        lc = PropagationLifecycle("evt-2")
        with pytest.raises(ValueError, match="Invalid transition"):
            lc.transition(PropagationState.SETTLED)

    def test_state_history_tracked(self):
        """After 3 transitions, history contains 3 entries (plus the initial)."""
        from synapse.event.lifecycle import PropagationState, PropagationLifecycle

        lc = PropagationLifecycle("evt-3")
        lc.transition(PropagationState.PROPAGATING)
        lc.transition(PropagationState.SETTLED)
        lc.transition(PropagationState.EXPIRED)

        history = lc.get_state_history()
        # Initial DETECTED + 3 transitions = 4 entries
        assert len(history) == 4
        assert history[0][0] == PropagationState.DETECTED
        assert history[1][0] == PropagationState.PROPAGATING
        assert history[2][0] == PropagationState.SETTLED
        assert history[3][0] == PropagationState.EXPIRED


# ------------------------------------------------------------------
# TestDecayModel (3 tests)
# ------------------------------------------------------------------


class TestDecayModel:
    def test_decay_formula_accuracy(self):
        """compute_decay(1.0, 0.1, 10) should equal e^(-1) ~ 0.367879."""
        import math
        from synapse.event.lifecycle import compute_decay

        result = compute_decay(1.0, 0.1, 10)
        expected = math.exp(-1.0)
        assert result == pytest.approx(expected, abs=1e-6)

    def test_zero_days_no_decay(self):
        """At t=0, decayed impact equals initial impact."""
        from synapse.event.lifecycle import compute_decay

        assert compute_decay(1.0, 0.5, 0) == 1.0
        assert compute_decay(5.0, 0.3, 0) == 5.0

    def test_large_days_approaches_zero(self):
        """After many half-lives, impact approaches zero."""
        from synapse.event.lifecycle import compute_decay

        result = compute_decay(1.0, 0.5, 100)
        assert result < 0.01


# ------------------------------------------------------------------
# TestCategoryDecay (1 test)
# ------------------------------------------------------------------


class TestCategoryDecay:
    def test_category_specific_half_lives(self):
        """Each event type applies the correct category half-life."""
        import math
        from synapse.event.lifecycle import apply_category_decay, CATEGORY_HALF_LIVES

        for event_type, half_life in CATEGORY_HALF_LIVES.items():
            expected_rate = math.log(2) / half_life
            # After 1 day, impact should be impact_0 * e^(-expected_rate)
            result = apply_category_decay(event_type, 1.0, 1.0)
            expected = math.exp(-expected_rate)
            assert result == pytest.approx(expected, abs=1e-6), (
                f"Mismatch for {event_type}: got {result}, expected {expected}"
            )


# ------------------------------------------------------------------
# TestStuckProtection (1 test)
# ------------------------------------------------------------------


class TestStuckProtection:
    def test_stuck_protection_fires(self):
        """is_stuck() returns True when PROPAGATING for > 7 days."""
        from datetime import datetime, timedelta
        from synapse.event.lifecycle import (
            PropagationState,
            PropagationLifecycle,
            STUCK_TIMEOUT_DAYS,
        )

        lc = PropagationLifecycle("evt-stuck", initial_state=PropagationState.PROPAGATING)
        # Simulate that propagation started 8 days ago
        lc._propagating_since = datetime.now() - timedelta(days=8)

        assert lc.is_stuck() is True

        # Not stuck if only 6 days
        lc._propagating_since = datetime.now() - timedelta(days=6)
        assert lc.is_stuck() is False

        # Not stuck if not in PROPAGATING state
        lc._state = PropagationState.SETTLED
        assert lc.is_stuck() is False
