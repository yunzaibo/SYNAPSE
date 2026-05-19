# F-022: Signal Scoring Engine — Data Architect Analysis

## Feature Summary

Define the data structures for a composite scoring engine that calculates `priority_score` from Signal, Event, and Position data. The engine is a pure function: inputs in, scored WatchlistEntry out.

## Data Model: ScoreResult

### Definition

```python
@dataclass(frozen=True)
class ScoreResult:
    """Immutable scoring result for a single ticker."""
    ticker: str
    raw_score: float              # Intermediate sum before normalization
    normalized_score: float       # Final [0.0, 1.0] after normalization
    component_scores: dict[str, float]  # e.g. {"signal": 0.3, "event": 0.5, "portfolio": 0.2}
    reason: str                   # Human-readable scoring explanation
```

**Why frozen**: ScoreResult is a computed value, not a stored entity. Immutability prevents accidental mutation after scoring.

**Why no ID**: ScoreResult is ephemeral — computed during daily generation, written into WatchlistEntry.priority_score, then discarded. It MUST NOT be persisted independently.

### Component Scores

| Component | Source | Weight Config Key | Default Weight |
|-----------|--------|-------------------|----------------|
| `signal` | Signal.strength + SignalType | `signal_weight` | 0.3 |
| `event` | Event.decay_rate + Event.severity | `event_weight` | 0.4 |
| `portfolio` | Position.research_state | `portfolio_weight` | 0.3 |

Weights MUST sum to 1.0. The scoring engine MUST validate this constraint and raise `ValueError` if not.

### Normalization

```
normalized_score = clamp(raw_score, 0.0, 1.0)
```

`raw_score` is the weighted sum of component scores. Since each component is already in [0.0, 1.0] and weights sum to 1.0, `raw_score` SHOULD also be in [0.0, 1.0]. Clamping is a safety net, not the primary mechanism.

## Scoring Function Signature

```python
def compute_score(
    ticker: str,
    signals: list[Signal],
    events: list[Event],
    positions: list[Position],
    config: ScoringConfig,
    target_date: date,
) -> ScoreResult:
```

**Constraints**:
- MUST be a pure function — no I/O, no mutation of inputs
- MUST return ScoreResult for every ticker, even with empty inputs (all components 0.0)
- MUST NOT raise on missing data — missing signals/events/positions contribute 0.0

## Data Flow Integration

```
generate_daily() flow:
  1. Collect all tickers from events + signals + positions
  2. For each ticker: compute_score(ticker, ...)
  3. Build WatchlistEntry with priority_score = result.normalized_score
  4. Build WatchlistEntry with reason = result.reason
```

The existing `generate_daily` function MUST be extended to call `compute_score` for each entry. The current implementation builds entries without scores — P1-2 adds the scoring pass between entry construction and output.

## Storage Impact

- ScoreResult is NOT persisted — it is a pipeline intermediate
- The `reason` string from ScoreResult is written into `WatchlistEntry.reason`
- The `normalized_score` from ScoreResult is written into `WatchlistEntry.priority_score`
- Component scores are available for debugging via logging but MUST NOT be stored in WatchlistEntry

## Risks

- **Medium**: Weight configuration errors (weights not summing to 1.0) could produce scores outside [0.0, 1.0]. Mitigation: validate in ScoringConfig.__post_init__, clamp in ScoreResult.
- **Low**: Empty component scores produce priority_score = 0.0 for all entries. This is correct behavior — entries with no signals/events/positions should rank lowest.
