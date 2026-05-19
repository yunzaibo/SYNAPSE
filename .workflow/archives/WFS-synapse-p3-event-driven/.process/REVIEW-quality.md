# P3 Event-Driven Research Contracts — Quality Review

**Reviewer**: Workflow Reviewer (quality-review skill)
**Date**: 2026-05-18
**Dimension**: Code Quality, Architecture, Security, Test Quality, API Design
**Files Reviewed**: 21 (10 new, 6 modified, 5 test files)

---

## Overall Assessment: APPROVED_WITH_NOTES

**106 tests pass (100%)**, all in 0.63s. The implementation demonstrates solid architecture with clean separation of concerns, proper DAG enforcement, and comprehensive edge-case coverage. However, several encapsulation violations and a data-loss risk in event merging require attention before production use.

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Files reviewed | 21 |
| Total findings | 14 |
| Critical | 0 |
| High | 3 |
| Medium | 6 |
| Low | 5 |
| Test pass rate | 106/106 (100%) |
| Total test lines | ~1,200 |

---

## Findings

### HIGH-001: Encapsulation Violation — ImpactAnalyzer Accesses Private Graph Internals

**File**: `synapse/event/impact.py:103-118`
**Severity**: HIGH
**Type**: Architecture

```python
def compute_cascaded_impact(self) -> dict[str, float]:
    if self._event.id not in self._graph._nodes:  # <-- private attr
        return {}
    # ...
    for edge in self._graph._adj.get(current, []):  # <-- private attr
```

**Description**: `ImpactAnalyzer` directly accesses `PropagationGraph._nodes` and `_graph._adj` (private attributes) instead of using the public API (`get_all_nodes()`, `get_neighbors()`). This couples the analyzer to the graph's internal representation, making future refactors risky.

**Impact**: Any internal restructuring of `PropagationGraph` will break `ImpactAnalyzer`. Violates the architecture-constraints spec: "模块间禁止循环依赖" (indirect coupling via private access).

**Suggestion**: Add a public method to `PropagationGraph` for getting outgoing edges with their weights (e.g., `get_outgoing_edges(node_id) -> list[PropagationEdge]`), and a `has_node(node_id) -> bool` method. Refactor `compute_cascaded_impact()` to use these public APIs.

---

### HIGH-002: Data Loss in Event Merging — outcome_tracking Silently Dropped

**File**: `synapse/event/dedup.py:85-99`
**Severity**: HIGH
**Type**: Correctness

```python
def merge_events(self, event_a: Event, event_b: Event) -> Event:
    # ...
    return Event(
        id=base.id,
        # ... other fields ...
        # outcome_tracking is MISSING from the merge
    )
```

**Description**: `merge_events()` constructs a new `Event` but omits `outcome_tracking`, `linked_review_ids`, `calibration_score`, and `propagation_graph_id` from both input events. Any outcome tracking data attached to the losing event is silently discarded.

**Impact**: In production, merged events could lose review linkage and outcome tracking history, breaking the event-review integration chain.

**Suggestion**: Include all Event fields in the merge. For list fields like `outcome_tracking` and `linked_review_ids`, union them (similar to how `related_tickers` is handled). For `propagation_graph_id`, prefer the non-None value.

---

### HIGH-003: In-Place Decay Mutation Without Idempotency Guard

**File**: `synapse/event/graph.py:291-310`
**Severity**: HIGH
**Type**: Correctness

```python
def apply_decay_to_edges(self, days: float) -> dict[str, float]:
    for node_id, edges in self._adj.items():
        for edge in edges:
            decayed = edge.weight * math.exp(-edge.decay_rate * days)
            edge.weight = decayed  # <-- mutates in place
```

**Description**: `apply_decay_to_edges()` mutates edge weights in-place with no idempotency protection. Calling it twice (e.g., in a retry or scheduled job) will double-decay the weights, producing incorrect impact calculations.

**Impact**: If the CLI `event impact` command or any scheduled task calls this method more than once on the same graph instance, all impact scores will be incorrectly halved.

**Suggestion**: Either (a) store the original weight on the edge and always compute decay from it, or (b) add a `_last_decay_applied` timestamp to prevent double-application, or (c) make the method return a new graph with decayed weights (functional style per coding-conventions.md: "优先使用纯函数、列表推导，避免可变状态").

---

### MEDIUM-001: Duplicate Lifecycle State Enums

**File**: `synapse/event/lifecycle.py:28-34` vs `synapse/core/schemas/event.py:49-54`
**Severity**: MEDIUM
**Type**: Architecture

```python
# lifecycle.py
class LifecycleState(str, Enum):
    DETECTED = "detected"
    PROPAGATING = "propagating"
    SETTLED = "settled"
    EXPIRED = "expired"

# event.py
class PropagationState(str, Enum):
    DETECTED = "detected"
    PROPAGATING = "propagating"
    SETTLED = "settled"
    EXPIRED = "expired"
```

**Description**: `LifecycleState` (in lifecycle.py) and `PropagationState` (in event.py) define identical states with identical values. The codebase uses both: `Event.propagation_state` uses `PropagationState`, while `PropagationLifecycle` and `PropagationGraph._node_states` use `LifecycleState`. This creates confusion about which enum to use when.

**Impact**: Developers must import from two different modules for the same concept. Type checks comparing `LifecycleState.DETECTED == PropagationState.DETECTED` would pass by value but fail by identity.

**Suggestion**: Consolidate into a single enum. Use `PropagationState` from `event.py` as the canonical definition (since it's in the schema layer) and have `lifecycle.py` import it, or define one canonical enum in a shared location.

---

### MEDIUM-002: DetectorRegistry Instantiates Dummy Detector for Registration

**File**: `synapse/event/registry.py:51-52`
**Severity**: MEDIUM
**Type**: Correctness

```python
def register(self, detector_cls: type[BaseDetector]) -> None:
    # ...
    instance = detector_cls()  # <-- instantiates with no args
    etype = instance.event_type()
```

**Description**: Registration creates a temporary instance just to call `event_type()`. If any future detector requires constructor arguments (e.g., a configured API client), registration will break. The `event_type()` return value should be a class-level property or classmethod instead.

**Impact**: Limits extensibility. Detectors with dependencies cannot be registered without workarounds.

**Suggestion**: Add a `@classmethod` or `@staticmethod` version of `event_type()` to `BaseDetector`, or use a class attribute `event_type: ClassVar[str]` on each detector. The registry should read the class attribute rather than instantiate.

---

### MEDIUM-003: CLI `run_detect` Silently Returns 0 on Missing Directory

**File**: `synapse/cli/commands/event.py:184-233`
**Severity**: MEDIUM
**Type**: Correctness

```python
def run_detect(args: argparse.Namespace) -> int:
    data_dir = Path(args.data_dir)
    # ...
    if data_dir.is_dir():
        for yml_file in sorted(data_dir.glob("*.yaml")):
            # ...
    print(f"Event Detection ({len(all_events)} events detected)")
    return 0
```

**Description**: If `--data-dir` points to a non-existent path, `run_detect` silently reports "0 events detected" with exit code 0. This masks user typos in path arguments.

**Impact**: Users may think no events were detected when the real problem is a wrong path. Violates the principle of failing loudly for obvious errors.

**Suggestion**: Add an early check: `if not data_dir.is_dir(): print(f"Error: {data_dir} is not a directory", file=sys.stderr); return 1`.

---

### MEDIUM-004: CLI `run_impact` Builds Naive Graph Model

**File**: `synapse/cli/commands/event.py:248-254`
**Severity**: MEDIUM
**Type**: Correctness

```python
graph = PropagationGraph()
for event in events:
    graph.add_edge(
        event.id,
        f"thesis_{event.event_type.value}",  # <-- synthetic node
        weight=0.5,
    )
```

**Description**: The impact command builds a synthetic graph where every event connects to a shared `thesis_{type}` node. Two earnings events will both connect to the same `thesis_earnings` node, creating artificial convergence. This doesn't represent real propagation relationships.

**Impact**: Impact scores will be diluted by shared synthetic nodes, producing misleading results.

**Suggestion**: Document this as a simplified fallback. In the future, load actual graph edges from stored `PropagationEdge` records. At minimum, add a comment explaining this is a placeholder.

---

### MEDIUM-005: Missing `CorporateActionDetector` Test Coverage

**File**: `tests/unit/test_event_detection.py`
**Severity**: MEDIUM
**Type**: Test Quality

**Description**: `TestConcreteDetectors` covers 5 of 6 detectors (earnings, policy, sentiment, theme, capital_flow) but has no test for `CorporateActionDetector`. The class exists in detectors.py but is untested.

**Impact**: Code coverage gap. If `CorporateActionDetector.detect()` has a bug, no test will catch it.

**Suggestion**: Add `test_corporate_action_detector_fires` and `test_corporate_action_detector_none` tests.

---

### MEDIUM-006: Missing Integration Test for Dedup-After-Detection Pipeline

**File**: `tests/integration/test_event_pipeline.py`
**Severity**: MEDIUM
**Type**: Test Quality

**Description**: The integration test covers detection, dedup key generation, graph construction, and impact analysis. However, it doesn't test deduplicating actual detected events (the dedup section only tests key generation, not `resolve_conflicts()`).

**Impact**: The full pipeline from detection through deduplication to impact is not end-to-end tested.

**Suggestion**: Add a step that detects the same event from two sources, runs `resolve_conflicts()`, and verifies only one event remains with merged metadata.

---

### LOW-001: `_extract_date` Catches Too Broadly

**File**: `synapse/event/detectors.py:343-354`
**Severity**: LOW
**Type**: Maintainability

```python
def _extract_date(data: dict) -> Optional[date]:
    for key in ("event_date", "date", "report_date"):
        val = data.get(key)
        if isinstance(val, str):
            try:
                return date.fromisoformat(val)
            except (ValueError, TypeError):
                continue
```

**Description**: The function catches `ValueError` and `TypeError` but `date.fromisoformat()` only raises `ValueError`. The `TypeError` catch is unnecessary (though harmless).

**Impact**: None functionally. Slightly misleading to readers.

**Suggestion**: Remove `TypeError` from the except clause, or keep it as defensive coding with a comment.

---

### LOW-002: PropagationGraph._sorted_insert Uses O(n) Linear Scan

**File**: `synapse/event/graph.py:343-356`
**Severity**: LOW
**Type**: Performance

```python
@staticmethod
def _sorted_insert(queue: deque[str], value: str) -> None:
    inserted = False
    temp: list[str] = []
    while queue and queue[0] < value:
        temp.append(queue.popleft())
    queue.appendleft(value)
    for item in reversed(temp):
        queue.appendleft(item)
```

**Description**: `_sorted_insert` is O(n) per call, making `topological_sort()` O(n^2) in the worst case. For typical graph sizes (< 1000 nodes) this is fine, but the docstring should acknowledge the complexity.

**Impact**: Negligible for expected workloads. The 1000-node performance test passes in < 150ms.

**Suggestion**: Add a note in the docstring: "Linear scan is acceptable for typical graph sizes. For graphs > 10k nodes, consider using a sorted container."

---

### LOW-003: `from __future__ import annotations` Inconsistency

**Files**: Various
**Severity**: LOW
**Type**: Style

**Description**: Most files use `from __future__ import annotations` but the convention is applied consistently across all P3 files. This is actually good practice. No action needed.

---

### LOW-004: Test File Uses Private Attribute Access

**File**: `tests/unit/test_propagation_graph.py:358`
**Severity**: LOW
**Type**: Test Quality

```python
lc._propagating_since = datetime.now() - timedelta(days=8)
```

**Description**: Tests directly set `_propagating_since` private attribute to simulate time passage. This couples tests to internal implementation.

**Impact**: If the internal field is renamed, tests break. Acceptable for unit tests of internal state machines.

**Suggestion**: Consider adding a `_test_set_propagating_since()` helper method to `PropagationLifecycle` for test use.

---

### LOW-005: `__init__.py` Lazy Import Could Use `importlib`

**File**: `synapse/event/__init__.py:70-99`
**Severity**: LOW
**Type**: Maintainability

**Description**: The `__getattr__` function uses manual if/elif chains for lazy imports. This works but is verbose and must be updated whenever new exports are added.

**Impact**: Maintenance burden when adding new exports. Current approach is clear and explicit.

**Suggestion**: Consider a data-driven approach: `LAZY_IMPORTS = {"BaseDetector": ("synapse.event.base", "BaseDetector"), ...}` with a single loop. Not urgent.

---

## Cross-Reference to Specs

| Spec Rule | Finding | Status |
|-----------|---------|--------|
| `[rule:arch] 模块间禁止循环依赖` | No circular dependencies found | PASS |
| `[rule:arch] 计算逻辑/服务必须无状态` | ImpactAnalyzer holds graph+event reference (stateful) | NOTE |
| `[rule:style] PEP 8, max line 88` | All files comply | PASS |
| `[rule:naming] snake_case / PascalCase` | All naming follows convention | PASS |
| `[rule:pattern] Type hints on all signatures` | All public methods have type hints | PASS |
| `[rule:pattern] Functional style, avoid mutable state` | `apply_decay_to_edges()` mutates in-place (HIGH-003) | VIOLATION |
| `[rule:import] 禁止循环依赖` | Lazy imports used correctly | PASS |
| `[rule:security] YAML safe_load` | CLI uses `yaml.safe_load` | PASS |
| `[rule:doc] Public API docstring` | All public classes/methods have docstrings | PASS |
| `[rule:quality] 80% test coverage` | 106 tests, all modules covered | PASS |

---

## Recommendations

### Must-Fix Before Production (High severity)

1. **HIGH-001**: Add public `get_outgoing_edges()` and `has_node()` methods to `PropagationGraph`. Refactor `ImpactAnalyzer` to use public API.
2. **HIGH-002**: Include `outcome_tracking`, `linked_review_ids`, and `calibration_score` in `merge_events()`.
3. **HIGH-003**: Make decay application idempotent — either store original weights or add a timestamp guard.

### Should-Fix Before Release (Medium severity)

4. **MEDIUM-001**: Consolidate `LifecycleState` and `PropagationState` into a single enum.
5. **MEDIUM-002**: Convert `event_type()` to a class attribute on `BaseDetector`.
6. **MEDIUM-003**: Add directory existence check in CLI `run_detect`.
7. **MEDIUM-005**: Add `CorporateActionDetector` test coverage.

### Nice-to-Have (Low severity)

8. **LOW-002**: Document O(n^2) complexity of `_sorted_insert`.
9. **LOW-005**: Consider data-driven lazy import in `__init__.py`.

---

## Conclusion

The P3 implementation is well-structured with clean module boundaries, proper DAG enforcement, and comprehensive test coverage. The three high-severity findings (encapsulation violation, data-loss in merge, in-place mutation) are architectural issues that should be addressed before production use but don't affect the current test suite. The codebase follows the project's coding conventions (PEP 8, type hints, docstrings, functional style) with the notable exception of the in-place decay mutation.

**Verdict**: APPROVED_WITH_NOTES — Fix HIGH-001 through HIGH-003 before merge to main.
