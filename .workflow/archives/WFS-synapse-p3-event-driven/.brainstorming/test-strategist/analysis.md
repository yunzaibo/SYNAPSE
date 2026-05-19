# P3 Event-Driven Research Contracts: Test Strategy Analysis

## Role Perspective Overview

As test-strategist, this analysis evaluates testing strategies for P3's six event-driven components. The analysis extends SYNAPSE's existing 456-test foundation (pytest + factory helpers + YAML fixtures) with event-specific testing patterns for detection accuracy, graph correctness, propagation determinism, and integration completeness.

---

## 1. Testing Strategy Overview

### 1.1 Testing Vision

P3 testing must validate two fundamental invariants from the guidance specification:

- **Deterministic propagation**: Same event inputs MUST produce identical propagation graphs
- **Projection rebuildability**: Event contracts MUST be fully reconstructable from raw events

### 1.2 Test Pyramid Target for P3

| Layer | Target | P3 Scope |
|-------|--------|----------|
| Unit tests | 70% (~56 tests) | Schema validation, detector logic, graph algorithms, decay math |
| Integration tests | 20% (~16 tests) | Event-to-review linkage, propagation pipeline, CLI subcommands |
| Performance/edge tests | 10% (~8 tests) | Graph traversal at scale, concurrent propagation, cycle detection |

**Total P3 estimate**: ~80 new tests (bringing project total to ~536)

### 1.3 Risk Tolerance

- **Zero tolerance**: Circular reference infinite loops, schema migration data loss
- **Low tolerance**: Propagation determinism violations, event deduplication false negatives
- **Medium tolerance**: Detection precision/recall below configurable thresholds

---

## 2. Quality Requirements Analysis

### 2.1 Functional Quality Requirements

#### Event Detection Accuracy (Component #9)

Detection accuracy requires both precision and recall measurement against labeled ground truth:

| Metric | Definition | Target | Acceptable Floor |
|--------|-----------|--------|------------------|
| Precision | True positives / (True positives + False positives) | >= 0.85 | >= 0.70 |
| Recall | True positives / (True positives + False negatives) | >= 0.80 | >= 0.65 |
| F1 Score | Harmonic mean of precision and recall | >= 0.82 | >= 0.67 |

These metrics MUST be computed per event type (announcement, policy, sentiment, theme, capital_flow) because detection difficulty varies significantly across categories.

#### Propagation Graph Correctness (Component #10)

Graph correctness requires formal validation against DAG properties:

- The graph MUST remain acyclic after every edge insertion
- Every propagation path MUST terminate (no infinite cascades)
- Impact scores MUST be monotonically non-increasing along propagation paths (decay reduces impact)
- The graph MUST be deterministic: identical inputs MUST produce identical edge sets

#### Event-Review Integration (Component #12)

Integration correctness requires bidirectional referential integrity:

- Every EventContract MUST link to at least one valid Event
- Every review linkage MUST be bidirectional (Event links to Review, Review links to Event)
- Post-event thesis revision detection MUST not produce false positives from unrelated revisions

### 2.2 Non-Functional Quality Requirements

#### Performance (Component #10, #11)

| Operation | Target (100 nodes) | Target (1000 nodes) | Maximum |
|-----------|--------------------|--------------------|---------|
| Graph traversal (BFS/DFS) | < 10ms | < 100ms | < 500ms |
| Cycle detection | < 5ms | < 50ms | < 200ms |
| Impact score computation | < 15ms | < 150ms | < 1s |
| Full propagation build | < 50ms | < 500ms | < 2s |

#### Reliability

- Event decay calculations MUST be timezone-aware (CST/UTC consistent)
- Expired events MUST be gracefully excluded from propagation without side effects
- Concurrent propagation requests MUST NOT corrupt graph state

### 2.3 Compliance Requirements

Per guidance specification RFC 2119 constraints:

- Backward compatibility with Event schema v2.0 MUST be validated by round-trip tests
- Lazy Upcast from v2.0 to v3.0 MUST be lossless for all existing fields
- Event propagation determinism MUST be verified by property-based tests

---

## 3. Test Strategy Framework

### 3.1 Unit Test Categories

#### Category A: Schema Validation Tests (Component #8)

Purpose: Validate Event schema v3.0 extension and EventContract/PropagationEdge dataclasses.

```
Test patterns:
- Round-trip serialization (to_dict/from_dict) for all new fields
- Lazy Upcast: v2.0 Event -> v3.0 Event preserves all v2.0 fields
- Constraint validation: severity in [0.0, 1.0], confidence in [0.0, 1.0], decay_rate >= 0
- Required field enforcement: contract_id, event_id MUST be non-empty
- Propagation state machine: detected -> propagating -> settled -> expired transitions
```

Fixture example (Event v3.0):
```python
def _make_event_v3(
    event_id: str = "evt_p3_001",
    event_type: str = "policy",
    severity: float = 0.8,
    confidence: float = 0.9,
    decay_rate: float = 0.1,
    source: str = "data_feed",
    propagation_state: str = "detected",
) -> Event:
    return Event(
        id=event_id,
        event_type=EventType(event_type),
        severity=severity,
        confidence=confidence,
        decay_rate=decay_rate,
        source=source,
        propagation_state=propagation_state,
    )
```

#### Category B: Event Detection Tests (Component #9)

Purpose: Validate rule-based detectors produce correct event classifications.

**Precision/Recall Test Pattern**:

```python
class TestDetectionAccuracy:
    """Precision/recall measurement against labeled fixtures."""

    def test_policy_event_precision(self):
        """Policy detector correctly identifies policy events."""
        labeled_events = load_fixture("detection/policy_events.yaml")
        detector = PolicyEventDetector()
        detected = detector.detect(labeled_events["inputs"])

        tp = len(detected & labeled_events["expected_ids"])
        fp = len(detected - labeled_events["expected_ids"])

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        assert precision >= 0.85, f"Policy precision {precision:.2f} < 0.85"

    def test_policy_event_recall(self):
        """Policy detector finds all policy events."""
        labeled_events = load_fixture("detection/policy_events.yaml")
        detector = PolicyEventDetector()
        detected = detector.detect(labeled_events["inputs"])

        tp = len(detected & labeled_events["expected_ids"])
        fn = len(labeled_events["expected_ids"] - detected)

        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        assert recall >= 0.80, f"Policy recall {recall:.2f} < 0.80"
```

**Deduplication Test Pattern**:

```python
class TestEventDeduplication:
    def test_identical_events_merged(self):
        """Two identical events produce one contract."""
        events = [_make_event_v3("e1", "policy"), _make_event_v3("e2", "policy")]
        engine = EventDetectionEngine()
        contracts = engine.deduplicate(events)
        assert len(contracts) == 1

    def test_similar_events_within_threshold_merged(self):
        """Events within similarity threshold are merged."""
        e1 = _make_event_v3("e1", "policy", title="央行降息")
        e2 = _make_event_v3("e2", "policy", title="央行宣布降息")
        engine = EventDetectionEngine(threshold=0.85)
        contracts = engine.deduplicate([e1, e2])
        assert len(contracts) == 1

    def test_dissimilar_events_not_merged(self):
        """Events below similarity threshold remain separate."""
        e1 = _make_event_v3("e1", "policy", title="央行降息")
        e2 = _make_event_v3("e2", "earnings", title="茅台财报")
        engine = EventDetectionEngine()
        contracts = engine.deduplicate([e1, e2])
        assert len(contracts) == 2
```

#### Category C: Propagation Graph Tests (Component #10)

Purpose: Validate DAG construction, cycle detection, and deterministic traversal.

**Cycle Detection Tests**:

```python
class TestCycleDetection:
    def test_direct_self_loop_prevented(self):
        """Self-referencing edge is rejected."""
        graph = PropagationGraph()
        with pytest.raises(CycleDetectedError):
            graph.add_edge("thesis_1", "thesis_1", weight=0.5)

    def test_two_node_cycle_prevented(self):
        """A->B, B->A cycle is detected and rejected."""
        graph = PropagationGraph()
        graph.add_edge("thesis_1", "thesis_2", weight=0.5)
        with pytest.raises(CycleDetectedError):
            graph.add_edge("thesis_2", "thesis_1", weight=0.5)

    def test_three_node_cycle_prevented(self):
        """A->B->C->A cycle is detected on third edge."""
        graph = PropagationGraph()
        graph.add_edge("a", "b", weight=0.5)
        graph.add_edge("b", "c", weight=0.5)
        with pytest.raises(CycleDetectedError):
            graph.add_edge("c", "a", weight=0.5)

    def test_valid_dag_accepted(self):
        """Valid DAG with multiple paths is accepted."""
        graph = PropagationGraph()
        graph.add_edge("event_1", "thesis_1", weight=0.8)
        graph.add_edge("event_1", "thesis_2", weight=0.6)
        graph.add_edge("thesis_1", "position_1", weight=0.7)
        graph.add_edge("thesis_2", "position_1", weight=0.5)
        assert graph.node_count() == 4
        assert graph.edge_count() == 4
```

**Determinism Tests**:

```python
class TestPropagationDeterminism:
    def test_same_inputs_same_output(self):
        """Identical event sets produce identical graphs."""
        events = _make_event_sequence(10, seed=42)
        g1 = PropagationGraphBuilder().build(events)
        g2 = PropagationGraphBuilder().build(events)
        assert g1.to_edge_set() == g2.to_edge_set()

    def test_order_independence(self):
        """Event insertion order does not affect final graph."""
        events = _make_event_sequence(10, seed=42)
        g1 = PropagationGraphBuilder().build(events)
        g2 = PropagationGraphBuilder().build(reversed(events))
        assert g1.to_edge_set() == g2.to_edge_set()
```

#### Category D: Event Decay Tests (Component #10, #11)

Purpose: Validate temporal decay calculations and expired event handling.

```python
class TestEventDecay:
    def test_decay_at_zero_days(self):
        """Event at creation has full impact."""
        event = _make_event_v3(severity=0.8, decay_rate=0.1)
        impact = compute_decay_impact(event, days_elapsed=0)
        assert impact == pytest.approx(0.8)

    def test_decay_after_7_days(self):
        """7-day decay with rate 0.1: 0.8 * (1 - 0.1*7) = 0.24."""
        event = _make_event_v3(severity=0.8, decay_rate=0.1)
        impact = compute_decay_impact(event, days_elapsed=7)
        assert impact == pytest.approx(0.24)

    def test_decay_floor_at_zero(self):
        """Decay does not go below zero."""
        event = _make_event_v3(severity=0.8, decay_rate=0.1)
        impact = compute_decay_impact(event, days_elapsed=100)
        assert impact >= 0.0

    def test_expired_event_excluded_from_propagation(self):
        """Expired events are skipped during propagation."""
        graph = PropagationGraph()
        expired = _make_event_v3(propagation_state="expired")
        active = _make_event_v3("evt_2", propagation_state="detected")
        graph.add_event(expired)
        graph.add_event(active)
        active_events = graph.active_events()
        assert len(active_events) == 1
        assert active_events[0].id == "evt_2"
```

#### Category E: Impact Analyzer Tests (Component #11)

```python
class TestImpactAnalyzer:
    def test_impact_score_computation(self):
        """Impact score = severity * weight * decay_factor."""
        event = _make_event_v3(severity=0.8)
        edge = PropagationEdge(source_id="e1", target_id="t1", weight=0.7, decay=0.05)
        score = ImpactAnalyzer.compute_score(event, edge, days_elapsed=3)
        expected = 0.8 * 0.7 * (1 - 0.05 * 3)
        assert score == pytest.approx(expected, abs=0.01)

    def test_risk_adjusted_impact(self):
        """Risk adjustment reduces raw impact score."""
        raw_impact = 0.8
        risk_factor = 0.6
        adjusted = ImpactAnalyzer.risk_adjust(raw_impact, risk_factor)
        assert adjusted == pytest.approx(0.48)
```

### 3.2 Integration Test Categories

#### Category F: Event-Review Linkage Tests (Component #12)

```python
class TestEventReviewIntegration:
    def test_event_to_review_bidirectional_link(self):
        """Event links to Review and Review links back to Event."""
        event = _make_event_v3("evt_1", linked_review_ids=["rev_1"])
        review = Review(id="rev_1", linked_event_id="evt_1")
        contract = EventReviewIntegrator.link(event, review)
        assert "rev_1" in contract.affected_reviews
        assert contract.event_id == "evt_1"

    def test_post_event_revision_detection(self):
        """Thesis revision within N days of event is flagged as event-driven."""
        event = _make_event_v3("evt_1", event_date=date(2026, 5, 1))
        thesis = _make_thesis("ths_1", created_at=datetime(2026, 5, 3))
        detector = PostEventRevisionDetector(window_days=7)
        result = detector.detect(event, [thesis])
        assert result.is_event_driven is True

    def test_unrelated_revision_not_flagged(self):
        """Thesis revision outside window is NOT flagged."""
        event = _make_event_v3("evt_1", event_date=date(2026, 5, 1))
        thesis = _make_thesis("ths_1", created_at=datetime(2026, 5, 20))
        detector = PostEventRevisionDetector(window_days=7)
        result = detector.detect(event, [thesis])
        assert result.is_event_driven is False
```

#### Category G: CLI Integration Tests (Component #13)

```python
class TestEventCLI:
    def test_event_detect_subcommand(self):
        """`synapse event detect` registers correctly."""
        import argparse
        from synapse.cli.commands.event import register
        parser = argparse.ArgumentParser(prog="synapse")
        subparsers = parser.add_subparsers(dest="command")
        register(subparsers)
        args = parser.parse_args(["event", "detect", "--data-dir", "/tmp"])
        assert args.event_command == "detect"
        assert hasattr(args, "func")

    def test_event_impact_subcommand(self):
        """`synapse event impact --event-id ID` parses correctly."""
        args = parser.parse_args(["event", "impact", "--event-id", "evt_1"])
        assert args.event_command == "impact"
        assert args.event_id == "evt_1"

    def test_event_graph_subcommand(self):
        """`synapse event graph --position-id ID` parses correctly."""
        args = parser.parse_args(["event", "graph", "--position-id", "pos_1"])
        assert args.event_command == "graph"
        assert args.position_id == "pos_1"
```

### 3.3 Performance Test Categories

#### Category H: Graph Traversal Performance

```python
class TestGraphPerformance:
    def test_traversal_100_nodes(self):
        """BFS on 100-node graph completes in < 10ms."""
        graph = _build_graph(node_count=100, edge_density=0.3)
        start = time.perf_counter()
        graph.bfs("root")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 10, f"BFS took {elapsed_ms:.1f}ms"

    def test_traversal_1000_nodes(self):
        """BFS on 1000-node graph completes in < 100ms."""
        graph = _build_graph(node_count=1000, edge_density=0.1)
        start = time.perf_counter()
        graph.bfs("root")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100, f"BFS took {elapsed_ms:.1f}ms"

    def test_cycle_detection_500_nodes(self):
        """Cycle detection on 500-node graph completes in < 50ms."""
        graph = _build_dag(node_count=500, edge_density=0.2)
        start = time.perf_counter()
        graph.detect_cycles()
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50, f"Cycle detection took {elapsed_ms:.1f}ms"
```

---

## 4. Edge Case Test Strategy

### 4.1 Circular Reference Edge Cases

```python
class TestCircularEdgeCases:
    def test_self_loop_rejection(self):
        """Self-referencing edge MUST be rejected."""
        ...

    def test_indirect_cycle_detection(self):
        """Cycle of length N detected on Nth edge insertion."""
        ...

    def test_cycle_detection_does_not_mutate_graph(self):
        """Failed cycle check leaves graph unchanged."""
        graph = PropagationGraph()
        graph.add_edge("a", "b", weight=0.5)
        with pytest.raises(CycleDetectedError):
            graph.add_edge("b", "a", weight=0.5)
        assert graph.edge_count() == 1  # original edge preserved
```

### 4.2 Expired Event Edge Cases

```python
class TestExpiredEventEdgeCases:
    def test_expired_event_not_propagated(self):
        """Expired events are excluded from propagation."""
        ...

    def test_expired_event_preserved_in_history(self):
        """Expired events remain in event store for audit."""
        ...

    def test_transition_to_expired_at_boundary(self):
        """Event at exact expiry time is marked expired."""
        event = _make_event_v3(decay_rate=0.1, severity=0.5)
        # At day 10: 0.5 * (1 - 0.1*10) = 0.0 -> expired
        state = compute_propagation_state(event, days_elapsed=10)
        assert state == "expired"
```

### 4.3 Concurrent Propagation Edge Cases

```python
class TestConcurrentPropagation:
    def test_concurrent_add_edge_no_corruption(self):
        """Parallel edge additions do not corrupt graph."""
        graph = PropagationGraph()
        edges = [(f"n{i}", f"n{i+1}", 0.5) for i in range(50)]

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(graph.add_edge, *e) for e in edges]
            results = [f.result() for f in futures]

        assert graph.edge_count() == 50
        assert graph.is_dag()

    def test_concurrent_read_during_write(self):
        """Read during write returns consistent snapshot."""
        graph = _build_graph(node_count=20)
        snapshots = []

        def reader():
            snapshots.append(graph.node_count())

        def writer():
            graph.add_edge("new_1", "new_2", 0.5)

        with ThreadPoolExecutor(max_workers=2) as pool:
            pool.submit(reader)
            pool.submit(writer)
            pool.shutdown(wait=True)

        # All snapshots should be valid integers
        assert all(isinstance(s, int) for s in snapshots)
```

### 4.4 Schema Migration Edge Cases

```python
class TestLazyUpcast:
    def test_v2_event_to_v3_preserves_fields(self):
        """v2.0 Event round-trips through v3.0 without data loss."""
        v2_dict = _make_v2_event_dict()
        v3_event = Event.from_dict(v2_dict)
        assert v3_event.schema_version == "3.0"
        # v2 fields preserved
        assert v3_event.event_type.value == v2_dict["event_type"]
        assert v3_event.impact_level.value == v2_dict["impact_level"]
        # v3 fields have defaults
        assert v3_event.severity == 0.0
        assert v3_event.confidence == 0.0
        assert v3_event.propagation_state == "detected"

    def test_v3_event_to_v2_dict_omits_v3_fields(self):
        """v3.0 Event can produce v2-compatible dict."""
        v3_event = _make_event_v3(severity=0.8, confidence=0.9)
        v2_dict = v3_event.to_v2_dict()
        assert "severity" not in v2_dict
        assert "confidence" not in v2_dict
```

---

## 5. Mock Strategy for External Event Sources

### 5.1 Mock Architecture

External event sources (data feeds, news APIs, AI detection) MUST be mocked at the boundary:

```python
# tests/unit/test_detection.py

class MockDataFeed:
    """Simulates external data feed with configurable responses."""

    def __init__(self, events: list[Event]):
        self._events = events
        self._call_count = 0

    def fetch(self, since: datetime) -> list[Event]:
        self._call_count += 1
        return [e for e in self._events if e.created_at >= since]

    @property
    def call_count(self):
        return self._call_count


class MockNewsSource:
    """Simulates news API with latency simulation."""

    def __init__(self, articles: list[dict], latency_ms: int = 0):
        self._articles = articles
        self._latency_ms = latency_ms

    def search(self, query: str) -> list[dict]:
        if self._latency_ms > 0:
            time.sleep(self._latency_ms / 1000)
        return [a for a in self._articles if query in a.get("title", "")]
```

### 5.2 Mock Usage Pattern

```python
class TestEventDetectionWithMockFeed:
    def test_detection_from_mock_feed(self):
        feed = MockDataFeed(events=[
            _make_event_v3("e1", "policy", title="央行降息"),
            _make_event_v3("e2", "earnings", title="茅台Q1财报"),
        ])
        engine = EventDetectionEngine(feed=feed)
        contracts = engine.run()
        assert len(contracts) == 2
        assert feed.call_count == 1

    def test_empty_feed_produces_no_contracts(self):
        feed = MockDataFeed(events=[])
        engine = EventDetectionEngine(feed=feed)
        contracts = engine.run()
        assert len(contracts) == 0
```

---

## 6. Test Data Fixtures

### 6.1 Fixture Directory Structure

```
tests/fixtures/p3_events/
  detection/
    policy_events.yaml        # 10 labeled policy events
    earnings_events.yaml      # 10 labeled earnings events
    mixed_events.yaml         # 20 mixed-type events
    edge_cases.yaml           # boundary conditions
  propagation/
    simple_chain.yaml         # A -> B -> C
    diamond.yaml              # A -> B,C; B,C -> D
    wide_graph.yaml           # 1 event -> 50 theses
    deep_chain.yaml           # 10-level chain
    cycle_attempt.yaml        # intentionally cyclic (for rejection tests)
  integration/
    event_review_pairs.yaml   # 20 event-review linkages
    full_pipeline.yaml        # event -> detection -> propagation -> review
  performance/
    graph_100.yaml            # 100-node graph definition
    graph_1000.yaml           # 1000-node graph definition
```

### 6.2 Fixture Examples

**propagation/simple_chain.yaml**:
```yaml
description: "Simple 3-level propagation chain"
events:
  - id: "evt_1"
    event_type: "policy"
    severity: 0.9
    confidence: 0.85
    decay_rate: 0.05
    propagation_state: "detected"

theses:
  - id: "ths_1"
    title: "利率敏感性"
    related_tickers: ["600519"]
  - id: "ths_2"
    title: "消费信贷传导"
    related_tickers: ["000858"]

positions:
  - id: "pos_1"
    ticker: "600519"
    linked_thesis_id: "ths_1"

expected_edges:
  - source: "evt_1"
    target: "ths_1"
    weight: 0.8
  - source: "ths_1"
    target: "pos_1"
    weight: 0.7

expected_impact_scores:
  "ths_1": 0.72
  "pos_1": 0.504
```

**propagation/cycle_attempt.yaml**:
```yaml
description: "Intentionally cyclic graph for rejection testing"
edges:
  - source: "a"
    target: "b"
    weight: 0.5
  - source: "b"
    target: "c"
    weight: 0.5
  - source: "c"
    target: "a"  # This edge creates a cycle
    weight: 0.5
expected_result: "CycleDetectedError on edge 3"
```

---

## 7. Coverage Targets

### 7.1 Per-Component Coverage

| Component | Line Coverage Target | Branch Coverage Target | Critical Paths |
|-----------|---------------------|----------------------|----------------|
| Event Schema Registry (#8) | >= 95% | >= 90% | to_dict/from_dict, Lazy Upcast |
| Event Detection Engine (#9) | >= 90% | >= 85% | detect(), deduplicate() |
| Propagation Graph (#10) | >= 95% | >= 90% | add_edge(), bfs(), detect_cycles() |
| Impact Analyzer (#11) | >= 90% | >= 85% | compute_score(), risk_adjust() |
| Event-Review Integration (#12) | >= 85% | >= 80% | link(), detect_revision() |
| Event CLI (#13) | >= 80% | >= 75% | register(), all subcommands |

### 7.2 Cross-Cutting Coverage

| Category | Coverage Target | Justification |
|----------|----------------|---------------|
| Error paths | >= 80% | All RFC 2119 error conditions MUST be tested |
| Edge cases | >= 70% | Boundary conditions for decay, cycle, expiry |
| Schema round-trip | 100% | Every schema MUST have round-trip test |
| CLI registration | 100% | Every subcommand MUST register correctly |

### 7.3 Coverage Gaps to Monitor

- Propagation edge weight normalization (if implemented)
- Concurrent graph mutation race conditions
- Schema v3.0 -> v2.0 backward compatibility dict generation
- Event deduplication similarity threshold tuning

---

## 8. Test Execution Strategy

### 8.1 Test Groups

| Group | Tests | Execution | Timeout |
|-------|-------|-----------|---------|
| Unit: Schema | ~15 | `pytest tests/unit/test_event_schema.py` | 30s |
| Unit: Detection | ~12 | `pytest tests/unit/test_event_detection.py` | 30s |
| Unit: Graph | ~18 | `pytest tests/unit/test_propagation_graph.py` | 60s |
| Unit: Impact | ~8 | `pytest tests/unit/test_impact_analyzer.py` | 30s |
| Integration: Review | ~6 | `pytest tests/integration/test_event_review.py` | 60s |
| Integration: CLI | ~4 | `pytest tests/integration/test_event_cli.py` | 30s |
| Performance | ~5 | `pytest tests/performance/test_graph_perf.py -m slow` | 120s |

### 8.2 CI/CD Quality Gates

1. **Gate 1**: All unit tests pass (0 failures)
2. **Gate 2**: Coverage >= 85% overall for P3 components
3. **Gate 3**: No performance regression > 20% from baseline
4. **Gate 4**: All RFC 2119 constraint tests pass

### 8.3 Pre-Commit Checks

- Schema round-trip tests MUST pass before any schema file commit
- Graph algorithm tests MUST pass before any propagation code commit
- CLI registration tests MUST pass before any CLI code commit

---

## 9. Risk-Based Testing Prioritization

### 9.1 High-Risk Areas (Must Test First)

1. **Cycle detection** -- Infinite loops in propagation graph would hang the system
2. **Lazy Upcast** -- Schema migration failure would lose existing data
3. **Propagation determinism** -- Non-deterministic behavior violates RFC 2119

### 9.2 Medium-Risk Areas

4. **Event deduplication accuracy** -- False merges lose event fidelity
5. **Decay calculation precision** -- Floating point drift over long chains
6. **Concurrent graph access** -- Race conditions in multi-threaded scenarios

### 9.3 Lower-Risk Areas

7. **CLI argument parsing** -- Standard argparse validation
8. **Report formatting** -- Output cosmetic issues
9. **Fixture loading** -- Test infrastructure, not production code

---

## 10. Recommendations

### 10.1 Immediate Actions (Before P3 Implementation)

1. Create fixture directory structure under `tests/fixtures/p3_events/`
2. Write schema round-trip tests first (Category A) -- these are cheap and catch migration bugs early
3. Establish performance baselines with empty/minimal graphs

### 10.2 During Implementation

4. Write cycle detection tests (Category C) alongside graph implementation -- these are the highest-risk tests
5. Use property-based testing (Hypothesis) for propagation determinism verification
6. Mock all external sources at boundary -- never call real APIs in unit tests

### 10.3 Post-Implementation

7. Run full integration suite with YAML fixtures loaded from disk
8. Verify CLI subcommands register and parse correctly
9. Benchmark graph traversal at 100/500/1000 node scales

### 10.4 Tool Recommendations

- **pytest** -- continue existing framework (no change)
- **pytest-benchmark** -- for performance test baselines
- **Hypothesis** -- for property-based testing of graph algorithms
- **pytest-timeout** -- prevent infinite loops from hanging test suite
- **pytest-xdist** -- parallel test execution for faster feedback

---

## 11. Detailed Analysis References

- Guidance specification: `@guidance-specification.md` (RFC 2119 constraints, component breakdown)
- P2 test patterns: `@tests/unit/test_analytics.py` (factory helpers, round-trip tests, YAML integration)
- P2 correlation: `@synapse/analytics/correlation.py` (existing event-review linkage)
- Event schema v2.0: `@synapse/core/schemas/event.py` (current Event dataclass)

---

## 12. Cross-Feature Dependencies

| P3 Feature | Depends On | Provides To |
|-----------|-----------|-------------|
| Event Schema Registry (#8) | Event schema v2.0 (P1) | All P3 components |
| Event Detection Engine (#9) | Event Schema Registry (#8) | Propagation Graph (#10) |
| Propagation Graph (#10) | Event Detection Engine (#9), Thesis/Position schemas (P1) | Impact Analyzer (#11) |
| Impact Analyzer (#11) | Propagation Graph (#10) | Event-Review Integration (#12) |
| Event-Review Integration (#12) | Impact Analyzer (#11), Review schema (P1) | Event CLI (#13) |
| Event CLI (#13) | All above components | User-facing interface |

---

*Analysis generated by test-strategist for P3 Event-Driven Research Contracts brainstorming.*
*Word count: ~2800*
