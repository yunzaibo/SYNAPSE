# F-022: Signal Scoring Engine -- System Architect Analysis

## Overview

Implement the core scoring engine that computes `priority_score` for each WatchlistEntry by combining contributions from signals, events, portfolio state, and market semantics. This is the central architectural component of P1-2.

## Current State Analysis

The existing `generate_daily()` in `watchlist_generator.py` produces flat, unranked entries. The scoring engine MUST be layered on top of this function, not replacing it. The pipeline flow:

```
generate_daily() -> [unscored entries] -> score_entries() -> [scored entries] -> rank/filter -> [final watchlist]
```

## Architecture: Pipeline Pattern

The scoring engine MUST be implemented as a pipeline of composable scoring functions:

```python
ScoringFunction = Callable[[WatchlistEntry, ScoringContext], tuple[float, str]]
# Returns (score_contribution, reason_text)

@dataclass(frozen=True)
class ScoringContext:
    events: list[Event]
    signals: list[Signal]
    positions: list[Position]
    target_date: date
    config: ScoringConfig
    market_data: Optional[MarketSemanticsData] = None
```

### Pipeline Stages

| Stage | Function | Input | Output | Weight Source |
|-------|----------|-------|--------|---------------|
| 1 | `score_signal_contribution()` | Entry + Signals | 0.0-1.0 + reason | config.signal_weights |
| 2 | `score_event_decay()` | Entry + Events | 0.0-1.0 + reason | Event.decay_rate + lifecycle |
| 3 | `score_portfolio_boost()` | Entry + Positions | 0.0-1.0 + reason | config.portfolio_boost |
| 4 | `score_market_context()` | Entry + MarketData | 0.0-1.0 + reason | config.market_filter |
| 5 | `aggregate_scores()` | All component scores | final 0.0-1.0 + reason | Weighted sum |

### Aggregation Formula

```
priority_score = (
    w_signal * signal_score +
    w_event * event_score +
    w_portfolio * portfolio_score +
    w_market * market_score
)
```

Where `w_*` are configurable weights from `ScoringConfig.signal_weights` (for signal) and fixed weights for other components.

**Default Weights** (MAY be overridden by F-027 personalization):
- signal: 0.35
- event: 0.30
- portfolio: 0.20
- market: 0.15

**Normalization**: The aggregated score MUST be clamped to [0.0, 1.0]. If weights do not sum to 1.0, the engine MUST auto-normalize.

## Design Decisions

### D-022-1: Composability Over Monolithic Function

Each scoring function is independently testable and replaceable. This follows the Single Responsibility Principle and enables:
- Unit testing each scoring dimension in isolation
- Future addition of new scoring dimensions without modifying existing ones
- Debugging which dimension contributed most to a score

### D-022-2: ScoredEntry as Intermediate Value

The pipeline produces `ScoredEntry` objects (not persisted) that contain the full scoring breakdown. Only the final `WatchlistEntry` with `priority_score` and `reason` is persisted. This enables:
- Debug logging of component scores
- Score explanation in the `reason` field
- Future score audit trail if needed

### D-022-3: reason Field Composition

The `reason` field MUST be composed from the highest-contributing scoring dimensions. Format:

```
"{top_dimension}: {brief_explanation} (score: {total_score:.2f})"
```

Examples:
- "Event: earnings surprise with 2-day decay (score: 0.85)"
- "Signal: attention_spike strong (score: 0.72)"
- "Portfolio: thesis weakened + attention rising (score: 0.68)"

### D-022-4: Graceful Degradation

Each scoring function MUST handle missing data gracefully:
- If no matching signals found: return `signal_score = 0.0`, reason = "No signal triggers"
- If no matching events found: return `event_score = 0.0`, reason = "No event triggers"
- If no matching positions found: return `portfolio_score = 0.0`, reason = "Not in portfolio"
- If market data unavailable: return `market_score = 0.5` (neutral), reason = "Market data unavailable"

The pipeline MUST NOT raise exceptions for missing data. It MUST log warnings and continue.

### D-022-5: Determinism

Given the same inputs, the scoring engine MUST produce identical outputs. This is critical for:
- Testing (assertions on exact scores)
- Debugging (reproduce score by re-running with same data)
- ADR-009 daily regeneration (re-running produces same watchlist)

## Integration Points

- **F-021**: Writes `priority_score` and `reason` to WatchlistEntry
- **F-023**: Uses `apply_category_decay()` from `event/lifecycle.py` for event scoring
- **F-024**: Reads Position.thesis_status and attention_state for portfolio scoring
- **F-025**: Uses TradingCalendar, NorthboundFlow, IndexConstituent for market scoring
- **F-027**: Reads ScoringConfig for weight customization

## Performance Considerations

- Expected input: 50-200 entries, each with up to 10 signals, 5 events, 3 positions
- The pipeline is O(n * m) where n = entries and m = scoring stages
- No optimization needed at current scale
- Future: if scale exceeds 1000 entries, consider vectorized scoring with numpy

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Weight tuning complexity | MEDIUM | Start with fixed defaults, expose via F-027 |
| Score explanation verbosity | LOW | Truncate reason to 200 chars max |
| Non-deterministic scoring | HIGH | Use deterministic data sources, no random factors |
