# Event Extensions Contract (F-007 / F-008 / F-009)

## Purpose

Define API contracts for the three P3 event-driven extension modules: sentiment viral propagation, capital flow divergence, and cross-event correlation. All modules are additive — no existing APIs are modified.

Source: `synapse/event/sentiment.py`, `synapse/event/divergence.py`, `synapse/event/correlation.py`

---

## F-007: Sentiment Viral Propagation

### Schema

```python
@dataclass
class SentimentPropagation:
    root_event_id: str = ""
    viral_coefficient: float = 0.0      # R0 value
    cascade_depth: int = 0              # Max BFS depth
    cascade_count: int = 0              # Direct children count
    intensity_at_source: float = 0.5    # Root event severity
    intensity_decay: dict[str, float]   # node_id -> decayed intensity
    propagation_window_hours: int = 24
    detected_at: Optional[datetime] = None
```

### API

```python
from synapse.event.sentiment import (
    SentimentPropagation,
    compute_viral_coefficient,
    detect_cascade,
    build_sentiment_propagation,
)

# Compute R0 via BFS on sentiment edges
r0 = compute_viral_coefficient(graph, root_event_id)

# Detect cascade: R0 > 1.0 AND depth >= 2
is_cascade = detect_cascade(propagation)

# Build from graph traversal (factory)
prop = build_sentiment_propagation(root_event, child_events, graph)
```

### Rules

- R0 formula: `(total_activated - 1) / direct_children`
- Cascade = `R0 > 1.0 AND cascade_depth >= 2`
- BFS traverses only edges with `edge_type="sentiment"`
- `CATEGORY_HALF_LIVES["sentiment"] = 2.0` for intensity decay

---

## F-008: Capital Flow Divergence

### Schema

```python
@dataclass
class CapitalFlowDivergence:
    divergence_id: str = ""
    ticker: str = ""
    sector: str = ""
    institutional_flow: float = 0.0
    retail_flow: float = 0.0
    divergence_score: float = 0.0       # [-1, 1]
    classification: str = "neutral"     # bullish_divergence / bearish_divergence / neutral
    magnitude: float = 0.5              # [0, 1]
    window_days: int = 5
    computed_at: Optional[datetime] = None
```

### API

```python
from synapse.event.divergence import (
    CapitalFlowDivergence,
    compute_divergence_score,
    classify_divergence,
    build_divergence_from_flows,
    settle_divergence_contract,
)

# Compute normalized divergence
score = compute_divergence_score(inst_flow, retail_flow)

# Classify direction
label = classify_divergence(score)  # "bullish_divergence" / "bearish_divergence" / "neutral"

# Build from event list (factory)
div = build_divergence_from_flows(events, ticker="600519", sector="白酒")

# Settle via EventContract
settle_divergence_contract(divergence, contract)
```

### Rules

- Formula: `(inst - retail) / (|inst| + |retail| + 1e-9)`
- Thresholds: `> 0.3` bullish, `< -0.3` bearish, else neutral
- Epsilon `1e-9` prevents division by zero
- Default rolling window: 5 trading days

---

## F-009: Cross-Event Correlation

### Schema

```python
@dataclass
class EventCorrelation:
    correlation_id: str = ""
    event_ids: list[str] = field(default_factory=list)
    thesis_id: str = ""
    correlation_score: float = 0.0      # [0, 1]
    combined_impact: float = 0.0
    amplification: str = "neutral"      # amplification / dampening / neutral
    correlation_window_days: int = 7
    detected_at: Optional[datetime] = None
```

### API

```python
from synapse.event.correlation import (
    EventCorrelation,
    EVENT_TYPE_AFFINITY,
    compute_correlation_score,
    classify_amplification,
    compute_combined_impact,
    find_correlations,
    add_correlation_edges,
)

# Score = type_affinity x temporal_proximity
score = compute_correlation_score(event_a, event_b, time_proximity=0.8)

# Classify impact
label = classify_amplification(score)  # "amplification" / "dampening" / "neutral"

# Aggregate cluster impact
impact = compute_combined_impact([ev1, ev2, ev3])

# Find correlations within time window
corrs = find_correlations(events, window_days=7, max_cluster=10)

# Add single-direction edges to PropagationGraph (DAG-safe)
edges = add_correlation_edges(graph, correlations)
```

### Rules

- `EVENT_TYPE_AFFINITY` is an 8x8 symmetric matrix (diagonal = 1.0)
- Thresholds: `> 0.6` amplification, `< 0.3` dampening
- Correlation edges are single-direction (`min_id -> max_id`) to preserve DAG
- Max cluster size 10 bounds O(n^2) pairwise comparison
- Events must share `thesis_id` to be correlated

---

## Integration Points

| Module | Uses Existing API | File |
|--------|-------------------|------|
| sentiment.py | `PropagationGraph.get_outgoing_edges()`, `CATEGORY_HALF_LIVES` | graph.py, lifecycle.py |
| divergence.py | `EventContract.settle()`, `EventType.CAPITAL_FLOW` | event_contract.py, taxonomy.py |
| correlation.py | `PropagationGraph.add_edge()` | graph.py |

## Constraints

1. All changes additive — no existing APIs modified
2. New schemas use `to_dict()`/`from_dict()` round-trip with Lazy Upcast defaults
3. Duck-typing with `hasattr` guards for cross-module imports (avoid circular deps)
4. DAG property enforced on all graph edges (no cycles)
