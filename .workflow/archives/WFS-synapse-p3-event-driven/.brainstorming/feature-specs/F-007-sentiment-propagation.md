# F-007: Sentiment Viral Propagation

**Feature ID**: F-007
**Priority**: High
**Status**: Proposed
**Related Roles**: system-architect, data-architect, subject-matter-expert
**Depends On**: F-003 (PropagationGraph), F-001 (EventContract)

## 1. Overview

Sentiment events (margin changes, northbound flows, block trades) propagate through the market with viral dynamics. This feature models sentiment propagation as a graph problem with viral coefficient (R₀) and cascade detection, enabling early identification of sentiment-driven market moves.

## 2. Concepts & Terminology

| Term | Definition |
|------|-----------|
| **Viral Coefficient (R₀)** | Average number of downstream nodes activated by one sentiment event. R₀ > 1 means expanding cascade. |
| **Cascade** | A chain of sentiment propagation where activation spreads through multiple graph hops. |
| **Cascade Depth** | Maximum hop count from original sentiment event to furthest affected node. |
| **Sentiment Intensity** | Normalized [0,1] measure of sentiment strength, derived from margin/northbound/block trade magnitudes. |
| **Propagation Wave** | Time-bounded group of cascades originating from the same root event. |

## 3. Non-Goals

- **Real-time streaming**: Batch processing is sufficient for P3; real-time is P4 scope.
- **Social media sentiment**: Only market-data signals (margin, northbound, block trades), not news/social NLP.
- **Predictive modeling**: This feature tracks observed propagation, not predicts future sentiment.

## 4. Data Model

### SentimentPropagation (new schema)

```python
@dataclass
class SentimentPropagation:
    root_event_id: str                     # Originating sentiment event
    viral_coefficient: float = 0.0         # R₀ value
    cascade_depth: int = 0                 # Max hops
    cascade_count: int = 0                 # Number of activated downstream nodes
    intensity_at_source: float = 0.5       # Sentiment intensity at root
    intensity_decay: dict[str, float]      # Per-node intensity after decay
    propagation_window_hours: int = 24     # Time window for cascade detection
    detected_at: datetime = None
```

### Integration with PropagationGraph

- Sentiment events create edges with `edge_type="sentiment"`
- Edge weight = sentiment intensity * source confidence
- Decay uses CATEGORY_HALF_LIVES["sentiment"] = 2.0 days

## 5. State Machine

```
Sentiment Detected → Measuring R₀ → Cascade Confirmed
                        ↓                  ↓
                   No Cascade         Settled (impact absorbed)
```

## 6. Algorithms

### Viral Coefficient Calculation

```
R₀ = (total_activated_nodes - 1) / cascade_count
```

Where:
- `total_activated_nodes`: All nodes that received sentiment propagation
- `cascade_count`: Direct children of root event that activated

### Cascade Detection

1. BFS from root sentiment event
2. Count nodes activated within `propagation_window_hours`
3. If R₀ > 1.0 AND cascade_depth >= 2 → cascade confirmed
4. Record cascade metrics for settlement

## 7. Integration Points

- **F-003 PropagationGraph**: Reuses DAG structure, adds sentiment-specific edge weights
- **F-001 EventContract**: Settlement records cascade metrics in `settlement_metadata`
- **F-002 SentimentDetector**: Existing detector provides input events
- **Lifecycle**: Cascade detection triggers on PROPAGATING state

## 8. RFC 2119 Constraints

- The system MUST calculate R₀ for every sentiment event that reaches PROPAGATING state
- The system MUST detect cascades within `propagation_window_hours` of root event
- The system SHOULD flag R₀ > 2.0 as "high-virality" for priority review
- The system MAY use configurable propagation window (default 24h)

## 9. Testing Strategy

- Unit: R₀ calculation, cascade detection logic, intensity decay
- Integration: Full propagation chain from SentimentDetector → graph → cascade metrics
- Edge cases: Single-node propagation (R₀=0), circular rejection (DAG property), window expiry
