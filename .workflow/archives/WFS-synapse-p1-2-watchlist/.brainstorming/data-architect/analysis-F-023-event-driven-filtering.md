# F-023: Event-Driven Filtering — Data Architect Analysis

## Feature Summary

Implement time-decay scoring based on Event lifecycle. Events lose relevance over time, and this decay MUST be captured as a numeric score that feeds into the composite scoring engine.

## Data Model: DecayScore

### Definition

```python
@dataclass(frozen=True)
class DecayScore:
    """Time-decay score for an event relative to a target date."""
    event_id: str
    decay_factor: float    # [0.0, 1.0] — 1.0 = fresh, 0.0 = fully decayed
    days_elapsed: int      # Days between event_date and target_date
    decay_rate: float      # Copied from Event.decay_rate for traceability
```

**Why frozen**: DecayScore is a computed value from a pure function. No mutation after creation.

### Decay Formula

```
decay_factor = max(0.0, 1.0 - (days_elapsed * decay_rate))
```

Where:
- `days_elapsed = (target_date - event_date).days` — MUST be >= 0 (events in the future are treated as day 0)
- `decay_rate` comes from `Event.decay_rate` (default 0.1)
- Result is clamped to [0.0, 1.0]

### Decay Function Signature

```python
def compute_decay(event: Event, target_date: date) -> DecayScore:
```

**Constraints**:
- MUST be a pure function
- MUST return DecayScore with decay_factor in [0.0, 1.0]
- MUST NOT raise on missing event_date — treat as target_date (days_elapsed = 0)
- If `event_date > target_date` (future event), `days_elapsed` MUST be 0

## Data Flow

```
compute_decay(Event, target_date) → DecayScore
    ↓
ScoreResult.component_scores["event"] = decay_score.decay_factor * event.severity
```

The event component score is the product of decay_factor and severity. This means:
- A high-severity event that happened 10 days ago may score lower than a medium-severity event from yesterday
- The decay_rate controls how fast events lose relevance

### Decay Rate Semantics

| Event Type | Suggested Decay Rate | Rationale |
|------------|---------------------|-----------|
| EARNINGS | 0.15 | Fast decay — relevance drops quickly after earnings |
| POLICY | 0.05 | Slow decay — policy impacts persist |
| SECTOR_ROTATION | 0.10 | Medium decay |
| MACRO_DATA | 0.20 | Very fast decay — data becomes stale quickly |
| Default | 0.10 | Conservative default |

These are suggestions for ScoringConfig defaults — NOT hardcoded values.

## Storage Impact

- DecayScore is ephemeral — NOT persisted
- The decay_factor feeds into ScoreResult.component_scores["event"]
- Event.decay_rate is already stored in Event schema — no new storage needed

## Edge Cases

1. **Event with no event_date**: Treated as "happened today" — decay_factor = 1.0
2. **Event with event_date in future**: Same treatment — decay_factor = 1.0
3. **Event with decay_rate = 0.0**: Never decays — decay_factor always 1.0
4. **Event with decay_rate = 1.0**: Fully decays after 1 day — decay_factor = 0.0 for any days_elapsed >= 1

All edge cases MUST be covered by unit tests in F-028.
