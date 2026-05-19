# F-023: Event-Driven Filtering -- System Architect Analysis

## Overview

Integrate the Event lifecycle decay model into the scoring pipeline so that event-driven entries receive time-decayed priority scores. This leverages the existing `apply_category_decay()` function in `event/lifecycle.py` rather than implementing a parallel mechanism.

## Current State Analysis

The existing event lifecycle system provides:
- `PropagationLifecycle` state machine: DETECTED -> PROPAGATING -> SETTLED -> EXPIRED
- `apply_category_decay(event_type, impact_0, days)` -- exponential decay with category-specific half-lives
- `CATEGORY_HALF_LIVES` dict mapping event types to half-life in days
- `Event.decay_rate`, `Event.severity`, `Event.confidence` fields

The current `_build_event_entries()` in `watchlist_generator.py` creates entries for events matching `target_date` but does NOT apply any decay or time-based scoring.

## Architecture: Decay Integration

### Scoring Function: `score_event_decay()`

```python
def score_event_decay(
    entry: WatchlistEntry,
    context: ScoringContext,
) -> tuple[float, str]:
    """Score event-driven entries using lifecycle decay model."""
    if entry.linked_event_id is None:
        return 0.0, "No linked event"

    event = _find_event(context.events, entry.linked_event_id)
    if event is None:
        return 0.0, "Linked event not found"

    # Calculate days since event
    days_since = (context.target_date - event.event_date).days if event.event_date else 0

    # Apply category-specific decay
    decayed_impact = apply_category_decay(
        event_type=event.event_type.value,
        impact_0=event.severity,
        days=float(days_since),
    )

    # Factor in confidence
    score = decayed_impact * event.confidence

    # Clamp to [0.0, 1.0]
    score = max(0.0, min(1.0, score))

    reason = (
        f"Event: {event.title} ({event.event_type.value}) "
        f"decayed {days_since}d -> {score:.2f}"
    )
    return score, reason
```

### Lifecycle State as Filter Predicate

Events in EXPIRED state SHOULD receive a score of 0.0 regardless of decay calculation. This prevents expired events from polluting the watchlist:

```python
if event.propagation_state == PropagationState.EXPIRED:
    return 0.0, "Event expired"
```

Events in SETTLED state SHOULD use their final decayed impact (decay already applied by lifecycle module).

Events in DETECTED or PROPAGATING state SHOULD use the live decay calculation.

## Design Decisions

### D-023-1: Reuse Existing Decay Model

The scoring engine MUST use `apply_category_decay()` from `event/lifecycle.py` (line 165-180). This function already implements:
- Exponential decay: `impact(t) = impact_0 * e^(-rate * t)`
- Category-specific half-lives via `CATEGORY_HALF_LIVES`
- Default half-life fallback

**Rationale**: Duplicating decay logic would violate DRY and risk inconsistency. The existing model is well-tested and documented.

### D-023-2: Event Freshness Boost

Events with `event_date == target_date` (happening today) SHOULD receive a freshness boost. The decay model alone would give them full impact (days=0), but a configurable boost factor can emphasize "today's events":

```python
if days_since == 0:
    score = min(1.0, score * 1.2)  # 20% freshness boost
```

This boost SHOULD be configurable via `ScoringConfig.event_decay.freshness_boost` (default 1.2).

### D-023-3: Multi-Event Aggregation

A single ticker may be linked to multiple events. The scoring function MUST aggregate multiple event scores:

```python
event_scores = [_score_single_event(entry, event, context) for event in related_events]
# Use max score (most relevant event drives the entry)
score = max(event_scores, key=lambda x: x[0])[0]
```

**Rationale**: Using max rather than sum prevents a ticker with many minor events from dominating the watchlist.

### D-023-4: Decay Rate Override

The `Event.decay_rate` field (default 0.1) is separate from the category-based decay. The scoring function SHOULD prefer category-based decay when available, falling back to `event.decay_rate` only for unknown event types.

## Integration Points

- **F-022**: `score_event_decay()` is one stage in the scoring pipeline
- **F-025**: TradingCalendar validation ensures `event_date` is a valid trading day
- **Existing `event/lifecycle.py`**: Direct reuse of `apply_category_decay()`, `CATEGORY_HALF_LIVES`
- **Existing `event.py`**: Reads `Event.decay_rate`, `Event.severity`, `Event.confidence`, `Event.propagation_state`

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Event not found for linked_event_id | LOW | Return 0.0 score, log warning |
| Unknown event type not in CATEGORY_HALF_LIVES | LOW | Falls back to DEFAULT_HALF_LIFE (5.0 days) |
| Event date in future (relative to target_date) | LOW | Clamp days_since to 0 |
