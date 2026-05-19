# F-008: Capital Flow Divergence Tracking

**Feature ID**: F-008
**Priority**: High
**Status**: Proposed
**Related Roles**: data-architect, subject-matter-expert
**Depends On**: F-001 (EventContract), F-003 (PropagationGraph)

## 1. Overview

Capital flow events (institutional vs retail) create divergence signals when institutional and retail flows move in opposite directions. This feature tracks capital flow events, computes divergence scores, and links divergence patterns to thesis impact via EventContract.

## 2. Concepts & Terminology

| Term | Definition |
|------|-----------|
| **Divergence Score** | Numeric measure of institutional/retail flow disagreement. Positive = institutional bullish, retail bearish. |
| **Flow Direction** | Net direction of capital flow: INFLOW, OUTFLOW, NEUTRAL |
| **Institutional Flow** | Mainforce/net big order flow, typically from龙虎榜 and 大单统计 |
| **Retail Flow** | Small order flow, margin trading changes, 散户资金 |
| **Divergence Window** | Time period over which divergence is measured (default: 5 trading days) |
| **Flow Magnitude** | Normalized [0,1] measure of flow strength relative to historical average |

## 3. Non-Goals

- **Real-time flow tracking**: Batch processing with daily granularity.
- **Individual stock flow decomposition**: Only aggregate sector/market-level flows.
- **Flow prediction**: Tracks observed patterns, not predictive.

## 4. Data Model

### CapitalFlowDivergence (new schema)

```python
@dataclass
class CapitalFlowDivergence:
    divergence_id: str
    ticker: str
    sector: str = ""
    institutional_flow: float = 0.0      # Positive = inflow
    retail_flow: float = 0.0             # Positive = inflow
    divergence_score: float = 0.0        # inst_flow - retail_flow (normalized)
    flow_direction: str = "neutral"       # bullish_divergence / bearish_divergence / neutral
    magnitude: float = 0.5               # Flow strength [0,1]
    window_days: int = 5
    computed_at: datetime = None
```

### Integration with EventContract

- Divergence events create EventContract with:
  - `settlement_result`: "bullish_divergence" | "bearish_divergence" | "no_divergence"
  - `settlement_metadata.divergence_score`: the computed score
  - `settlement_metadata.flow_magnitude`: strength measure

## 5. Divergence Detection Algorithm

### Score Computation

```
divergence_score = institutional_flow - retail_flow
normalized_score = divergence_score / (abs(institutional_flow) + abs(retail_flow) + epsilon)
```

### Classification

| Condition | Classification |
|-----------|---------------|
| normalized_score > 0.3 | bullish_divergence (institutional buying, retail selling) |
| normalized_score < -0.3 | bearish_divergence (institutional selling, retail buying) |
| abs(normalized_score) <= 0.3 | no_divergence |

## 6. Integration Points

- **F-002 CapitalFlowDetector**: Existing detector provides raw flow events
- **F-001 EventContract**: Divergence results stored via settle()
- **F-003 PropagationGraph**: Divergence events can propagate to related tickers
- **Watcher**: Divergence events trigger watchlist entries with TriggerType.FACTOR_SIGNAL

## 7. RFC 2119 Constraints

- The system MUST compute divergence score for every CapitalFlowDetector event
- The system MUST classify divergence as bullish/bearish/neutral using threshold 0.3
- The system SHOULD use 5-day rolling window for flow comparison
- The system MAY weight institutional flow 1.5x for significance

## 8. Testing Strategy

- Unit: Divergence score calculation, classification thresholds
- Integration: CapitalFlowDetector → divergence computation → EventContract settlement
- Edge cases: Zero flows (neutral), equal flows (neutral), single-sided flow
