# Feature Spec: F-023 - Event-Driven Filtering

**Priority**: High
**Contributing Roles**: system-architect, data-architect, product-manager
**Status**: Final (conflicts resolved)

## 1. Requirements Summary

- Event-driven entries MUST receive time-decayed priority scores based on Event lifecycle
- The scoring engine MUST reuse the existing `apply_category_decay()` function from `event/lifecycle.py`
- DecayScore is a value object (frozen dataclass) representing time-decay for a single event
- Events in EXPIRED state MUST receive a score of 0.0 regardless of decay calculation
- Events with `event_date == target_date` SHOULD receive a freshness boost (configurable, default 1.2x)
- A single ticker linked to multiple events MUST use the max event score (not sum)
- The decay model MUST be deterministic: identical inputs produce identical outputs
- Non-trading-day events are gated by F-025 TradingCalendar integration
- Decay parameters SHOULD be configurable via YAML (deferred to F-027)

## 2. Design Decisions [CORE SECTION]

### D-023-1: Reuse Existing Decay Model

**Decision**: The scoring engine MUST use `apply_category_decay()` from `event/lifecycle.py` rather than implementing a parallel decay mechanism.

**Context**: The existing event lifecycle system provides exponential decay with category-specific half-lives via `CATEGORY_HALF_LIVES`. Duplicating this logic would violate DRY and risk inconsistency.

**Options Considered**:
- [system-architect] Reuse `apply_category_decay()` — well-tested, documented
- [data-architect] Reuse `apply_category_decay()` — same approach
- [product-manager] Decay model is domain-specific; reuse ensures consistency

**Chosen Approach**: Direct reuse of `apply_category_decay()`. The existing function implements `impact(t) = impact_0 * e^(-rate * t)` with category-specific half-lives. The scoring function wraps this call with additional logic for lifecycle state checks and multi-event aggregation. (All roles consensus)

**Trade-offs**: Zero duplication vs. coupling to existing decay API. The trade-off is strongly favorable because the existing model is well-tested and the API is stable.

**Source**: system-architect, data-architect, product-manager (consensus)

### D-023-2: DecayScore as Value Object

**Decision**: DecayScore MUST be a frozen dataclass representing time-decay for a single event relative to a target date.

**Context**: The data-architect defines DecayScore as an intermediate computed value. It is ephemeral — not persisted, used only during scoring.

**Options Considered**:
- [data-architect] Frozen dataclass with event_id, decay_factor, days_elapsed, decay_rate
- [system-architect] References DecayScore but does not define structure

**Chosen Approach**: Adopt data-architect's DecayScore definition. Frozen because it is a computed value from a pure function. No ID because it is ephemeral. (All roles consensus)

```python
@dataclass(frozen=True)
class DecayScore:
    event_id: str
    decay_factor: float    # [0.0, 1.0] — 1.0 = fresh, 0.0 = fully decayed
    days_elapsed: int      # Days between event_date and target_date
    decay_rate: float      # Copied from Event.decay_rate for traceability
```

**Trade-offs**: Clear, traceable decay computation vs. additional type to maintain. The trade-off is favorable because DecayScore makes decay logic inspectable and testable.

**Source**: data-architect (definition), system-architect (acceptance)

### D-023-3: Lifecycle State as Filter Predicate

**Decision**: Events in EXPIRED state MUST receive a score of 0.0 regardless of decay calculation. Events in SETTLED state use their final decayed impact. Events in DETECTED or PROPAGATING state use live decay calculation.

**Context**: The propagation lifecycle (`DETECTED -> PROPAGATING -> SETTLED -> EXPIRED`) provides a natural hierarchy. Expired events should never appear in the watchlist.

**Options Considered**:
- [system-architect] EXPIRED = 0.0; SETTLED = final decay; DETECTED/PROPAGATING = live decay
- [product-manager] Lifecycle awareness: active/developing score higher than resolved

**Chosen Approach**: Lifecycle state acts as a filter predicate before decay calculation. EXPIRED events are hard-filtered (score=0.0). This aligns with the product-manager's requirement that resolved events receive additional decay penalty.

**Trade-offs**: Clean separation of lifecycle filtering vs. decay calculation vs. combining both in one function. The separation is clearer and more testable.

**Source**: system-architect (architecture), product-manager (lifecycle mapping)

### D-023-4: Multi-Event Aggregation via Max

**Decision**: When a single ticker is linked to multiple events, the scoring function MUST use the maximum event score (not sum).

**Context**: Using max prevents a ticker with many minor events from dominating the watchlist. The most relevant event drives the entry's event component score.

**Options Considered**:
- [system-architect] Max of event scores
- [data-architect] Implicit in compute_decay — single event per call

**Chosen Approach**: The `score_event_decay()` function iterates over all events linked to a ticker and returns the maximum decayed score. This ensures one strong event is sufficient to boost an entry, while many weak events do not compound.

**Trade-offs**: Prevents score inflation from multiple weak events vs. potentially ignoring cumulative event impact. The max approach is simpler and more predictable.

**Source**: system-architect

### D-023-5: Freshness Boost for Today's Events

**Decision**: Events with `event_date == target_date` SHOULD receive a configurable freshness boost (default 1.2x, capped at 1.0).

**Context**: The decay model alone gives today's events full impact (days=0). A configurable boost emphasizes "today's events" beyond the baseline decay.

**Options Considered**:
- [system-architect] Configurable freshness boost, default 1.2
- [product-manager] Events within 24 hours receive decay factor >= 0.8

**Chosen Approach**: Freshness boost is configurable via `ScoringConfig.event_decay.freshness_boost` (default 1.2). Applied only when `days_since == 0`. Capped at 1.0 to maintain the [0.0, 1.0] range.

**Trade-offs**: Emphasizes today's events vs. additional configuration surface. The default 1.2x is conservative enough to be safe without configuration.

**Source**: system-architect (implementation), product-manager (validation criteria)

## 3. Interface Contract

### Scoring Function

```python
def score_event_decay(
    entry: WatchlistEntry,
    context: ScoringContext,
) -> tuple[float, str]:
    """Score event-driven entries using lifecycle decay model."""
```

### DecayScore Value Object

```python
@dataclass(frozen=True)
class DecayScore:
    event_id: str
    decay_factor: float    # [0.0, 1.0]
    days_elapsed: int
    decay_rate: float
```

### Decay Function

```python
def compute_decay(event: Event, target_date: date) -> DecayScore:
    """Pure function: compute time-decay for a single event."""
```

### Data Flow

```
score_event_decay(entry, context):
  1. Find linked event by entry.linked_event_id
  2. Check lifecycle state: EXPIRED -> return (0.0, "Event expired")
  3. Compute days_elapsed = (target_date - event.event_date).days
  4. Apply apply_category_decay(event_type, severity, days_elapsed)
  5. Apply freshness boost if days_elapsed == 0
  6. Factor in event.confidence
  7. Clamp to [0.0, 1.0]
  8. Return (score, reason)
```

### Decay Rate Semantics

| Event Type | Suggested Decay Rate | Rationale |
|------------|---------------------|-----------|
| EARNINGS | 0.15 | Fast decay — relevance drops quickly after earnings |
| POLICY | 0.05 | Slow decay — policy impacts persist |
| SECTOR_ROTATION | 0.10 | Medium decay |
| MACRO_DATA | 0.20 | Very fast decay — data becomes stale quickly |
| Default | 0.10 | Conservative default |

## 4. Constraints & Risks

| Constraint | Type | Mitigation |
|------------|------|------------|
| Reuse existing decay model | MUST | Use apply_category_decay() from event/lifecycle.py |
| EXPIRED events score 0.0 | MUST | Lifecycle state check before decay calculation |
| Deterministic decay | MUST | Pure function of event timestamp and current time |
| Multi-event aggregation via max | MUST | Prevents score inflation from multiple weak events |
| Non-trading-day exclusion | MUST | Gated by TradingCalendar from F-025 (P1-1) |
| Freshness boost configurable | SHOULD | ScoringConfig.event_decay.freshness_boost |

| Risk | Severity | Mitigation |
|------|----------|------------|
| Event not found for linked_event_id | LOW | Return 0.0 score, log warning |
| Unknown event type not in CATEGORY_HALF_LIVES | LOW | Falls back to DEFAULT_HALF_LIFE (5.0 days) |
| Event date in future (relative to target_date) | LOW | Clamp days_since to 0 |
| P1-1 TradingCalendar unavailable | MEDIUM | Graceful degradation: all days treated as trading days |

## 5. Acceptance Criteria

- [ ] score_event_decay() returns (0.0, "Event expired") for EXPIRED lifecycle state
- [ ] score_event_decay() uses apply_category_decay() for exponential decay
- [ ] Fresh events (days=0) receive freshness boost (default 1.2x, capped at 1.0)
- [ ] Multiple events for same ticker use max score
- [ ] Missing linked_event_id returns (0.0, "No linked event")
- [ ] Missing event for linked_event_id returns (0.0, "Linked event not found")
- [ ] DecayScore is a frozen dataclass with event_id, decay_factor, days_elapsed, decay_rate
- [ ] compute_decay() is a pure function (no I/O, no mutation)
- [ ] Decay computation is deterministic for identical inputs
- [ ] Future events (event_date > target_date) treated as days_elapsed=0

## 6. Detailed Analysis References

- @../system-architect/analysis-F-023-event-driven-filtering.md — Decay integration, lifecycle state filtering, multi-event aggregation, freshness boost
- @../data-architect/analysis-F-023-event-driven-filtering.md — DecayScore value object, decay formula, decay rate semantics
- @../product-manager/analysis-F-023-event-driven-filtering.md — Temporal relevance, lifecycle awareness, non-trading-day handling
- @../guidance-specification.md#feature-decomposition — F-023 definition and related roles

## 7. Cross-Feature Dependencies

- **Depends on**: Existing `apply_category_decay()` from event/lifecycle.py, Event schema (decay_rate, severity, confidence, propagation_state)
- **Required by**: F-022 (event component of scoring pipeline)
- **Shared patterns**: Pure function pattern, DecayScore as value object
- **Integration points**:
  - F-022: `score_event_decay()` is stage 2 in the scoring pipeline
  - F-025: TradingCalendar validation ensures event_date is a valid trading day
  - F-027: Decay parameters (freshness_boost, decay rates) configurable via YAML (deferred)
