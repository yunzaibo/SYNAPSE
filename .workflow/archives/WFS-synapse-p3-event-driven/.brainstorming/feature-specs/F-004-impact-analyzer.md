# F-004: Event Impact Analyzer

## Component #11: Quantify Event Impact on Positions and Theses

### Overview
Calculates impact scores for events propagated through the graph. Computes before/after comparison metrics and risk-adjusted impact scores.

### Impact Score Formula
```
impact_score = severity * confidence * decay_factor * path_weight
```

Where:
- `severity`: 0.0-1.0 (from event)
- `confidence`: 0.0-1.0 (from event)
- `decay_factor`: e^(-decay_rate * days_since_event)
- `path_weight`: product of edge weights along propagation path

### Impact Metrics
| Metric | Description |
|--------|-------------|
| Direct Impact | Event → thesis (single hop) |
| Cascaded Impact | Event → thesis → position (multi-hop) |
| Aggregate Impact | Sum of all impacts on a position |
| Risk-Adjusted Impact | Impact / portfolio_volatility |

### Output: ImpactReport
```python
@dataclass
class ImpactReport:
    event_id: str
    direct_impacts: dict[str, float]      # thesis_id → score
    cascaded_impacts: dict[str, float]    # position_id → score
    aggregate_by_position: dict[str, float]
    max_impact_entity: str
    total_impact: float
    computed_at: str
```

### Tests (~8 tests)
- Direct impact calculation
- Cascaded impact calculation
- Decay factor accuracy over time
- Aggregate impact computation
- Risk-adjusted impact
- Edge case: expired event (impact = 0)
- Edge case: zero-weight path
- Performance: 1000-node graph < 150ms
