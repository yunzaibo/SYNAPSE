# F-009: Cross-Event Correlation Engine

**Feature ID**: F-009
**Priority**: Medium
**Status**: Proposed
**Related Roles**: system-architect, data-architect, subject-matter-expert
**Depends On**: F-001 (EventContract), F-003 (PropagationGraph), F-007, F-008

## 1. Overview

Multiple events (earnings, policy, sentiment, capital flow) can impact the same thesis. This feature correlates events that affect overlapping theses/positions, computes combined impact, and identifies event clusters that amplify or dampen each other.

## 2. Concepts & Terminology

| Term | Definition |
|------|-----------|
| **Event Cluster** | Group of events affecting the same thesis within a time window. |
| **Correlation Score** | Numeric [0,1] measure of how strongly two events are related. |
| **Combined Impact** | Aggregated impact score from multiple events on the same thesis. |
| **Impact Amplification** | When correlated events increase each other's impact (positive correlation). |
| **Impact Dampening** | When correlated events reduce each other's impact (negative correlation). |
| **Correlation Window** | Time period within which events are considered correlated (default: 7 days). |

## 3. Non-Goals

- **Causal inference**: Correlation does not imply causation; we track co-occurrence, not cause-effect.
- **Cross-asset correlation**: Only within same market (CN_A), not cross-market.
- **Statistical significance testing**: Use heuristic thresholds, not p-values.

## 4. Data Model

### EventCorrelation (new schema)

```python
@dataclass
class EventCorrelation:
    correlation_id: str
    event_ids: list[str]                  # Correlated event IDs
    thesis_id: str                        # Shared thesis
    correlation_score: float = 0.0        # [0,1] strength
    combined_impact: float = 0.0          # Aggregated impact
    amplification: bool = False           # True if events amplify each other
    correlation_window_days: int = 7
    detected_at: datetime = None
```

### CorrelationGraph (extension of PropagationGraph)

- Additional edge type: `edge_type="correlation"`
- Edge weight = correlation_score
- Edges are bidirectional (correlation is symmetric)

## 5. Correlation Detection Algorithm

### Step 1: Find Overlapping Theses

For each pair of events (A, B) within correlation_window_days:
```
shared_theses = set(A.affected_theses) & set(B.affected_theses)
if shared_theses:
    candidate_pairs.append((A, B, shared_theses))
```

### Step 2: Compute Correlation Score

```
type_affinity = EVENT_TYPE_AFFINITY[A.event_type][B.event_type]
temporal_proximity = 1.0 - (days_between / correlation_window)
correlation_score = type_affinity * temporal_proximity
```

### Step 3: Classify Amplification vs Dampening

```
if A.impact_level == B.impact_level:
    amplification = True   # Same direction = amplify
else:
    amplification = False  # Different direction = dampen
```

### Step 4: Compute Combined Impact

```
if amplification:
    combined = max(A.severity, B.severity) * (1 + correlation_score * 0.5)
else:
    combined = max(A.severity, B.severity) * (1 - correlation_score * 0.3)
```

## 6. Event Type Affinity Matrix

| | earnings | policy | sentiment | theme | capital_flow | policy_change | macro_shift |
|---|---------|--------|-----------|-------|-------------|---------------|-------------|
| **earnings** | 1.0 | 0.3 | 0.5 | 0.4 | 0.4 | 0.2 | 0.3 |
| **policy** | 0.3 | 1.0 | 0.4 | 0.6 | 0.3 | 0.8 | 0.5 |
| **sentiment** | 0.5 | 0.4 | 1.0 | 0.5 | 0.7 | 0.3 | 0.4 |
| **theme** | 0.4 | 0.6 | 0.5 | 1.0 | 0.4 | 0.5 | 0.3 |
| **capital_flow** | 0.4 | 0.3 | 0.7 | 0.4 | 1.0 | 0.2 | 0.5 |
| **policy_change** | 0.2 | 0.8 | 0.3 | 0.5 | 0.2 | 1.0 | 0.6 |
| **macro_shift** | 0.3 | 0.5 | 0.4 | 0.3 | 0.5 | 0.6 | 1.0 |

## 7. Integration Points

- **F-001 EventContract**: Correlation results stored as separate EventCorrelation objects
- **F-003 PropagationGraph**: Correlation edges added to existing DAG
- **F-007 Sentiment**: Sentiment cascades can correlate with other event types
- **F-008 Capital Flow**: Divergence events correlate with policy/sentiment events
- **Watchlist**: Correlated event clusters generate aggregated watchlist entries

## 8. RFC 2119 Constraints

- The system MUST detect correlations within configurable window (default 7 days)
- The system MUST use EVENT_TYPE_AFFINITY matrix for type-based scoring
- The system SHOULD flag correlation_score > 0.7 as "high-correlation" for priority review
- The system MUST NOT create cycles in the correlation graph (DAG property enforced)
- The system MAY limit maximum cluster size to 10 events for performance

## 9. Testing Strategy

- Unit: Correlation score calculation, affinity matrix lookups, combined impact formula
- Integration: Multiple events → correlation detection → EventCorrelation creation
- Edge cases: Single event (no correlation), all-same-type events, window boundary
- Performance: 100+ events in window, cluster size limits
