# F-021: WatchlistEntry Schema Extension -- System Architect Analysis

## Overview

Extend `WatchlistEntry` with `priority_score` (float) and `reason` (str) fields to support the scoring pipeline output. This is the foundational schema change that enables all downstream scoring, ranking, and filtering features.

## Current State Analysis

The existing `WatchlistEntry` at `synapse/core/schemas/watchlist.py` (lines 62-124):
- Inherits from `BaseSchema` (provides id, schema_version, status, created_at, updated_at, market_context)
- Has 12 fields: ticker, symbol, market, headline, why_now, signals, research_angle, action, risk_hint, trigger_type, linked_thesis_id, linked_event_id
- Uses `to_dict()` / `from_dict()` round-trip serialization
- Schema version is inherited as "1.0" from BaseSchema

**Key Observation**: The `why_now` field already serves a purpose similar to `reason` -- it explains why the entry is relevant today. The new `reason` field MUST serve a distinct purpose: explaining the scoring rationale (why this priority score was assigned).

## Design Decisions

### D-021-1: Lazy Upcast for New Fields

The schema MUST use Lazy Upcast pattern (consistent with Event v2.0 -> v3.0 transition in `event.py`):

```python
# In from_dict():
priority_score=float(data.get("priority_score", 0.0)),
reason=data.get("reason", ""),
```

This ensures existing v1.0 WatchlistEntry dicts deserialized without error. The default `priority_score=0.0` means unscored entries naturally sort to the bottom.

**Rationale**: Aligns with ADR-005 (Weak Schema + Lazy Upcast). No migration script needed. Existing YAML files remain readable.

### D-021-2: Schema Version Bump to "2.0"

`WatchlistEntry.schema_version` MUST be set to "2.0" to distinguish scored entries from unscored ones. This enables:
- consumers to detect whether an entry has been through the scoring pipeline
- future schema evolution to branch on version

### D-021-3: Frozen Dataclass Preservation

The new fields MUST be added as regular dataclass fields (not `field(default=...)` with mutable defaults). `priority_score` is `float` (immutable). `reason` is `str` (immutable). No mutable default issue.

However, `WatchlistEntry` is NOT currently `frozen=True`. The guidance-specification says "Frozen Dataclass pattern" but existing code does not use `@dataclass(frozen=True)`. This is a discrepancy.

**Recommendation**: Do NOT make WatchlistEntry frozen in this change. The existing codebase creates entries imperatively in `_build_event_entries()`, `_build_signal_entries()`, `_build_portfolio_entries()`. Adding `frozen=True` would break all three functions. If immutability is desired, it should be a separate refactoring task (P2+).

### D-021-4: priority_score Range and Type

- Type: `float` (not Decimal, consistent with Event.severity and Event.confidence)
- Range: [0.0, 1.0] -- validated in `__post_init__` using the existing `_validate_range` pattern from Event
- Default: `0.0` (unscored entries)

### D-021-5: reason Field Semantics

The `reason` field MUST contain a human-readable explanation of why the entry received its priority score. Examples:
- "Event earnings surprise + strong signal (score: 0.85)"
- "Portfolio review: thesis weakened, attention rising (score: 0.72)"
- "Sector resonance with policy impact (score: 0.65)"

The scoring engine (F-022) is responsible for populating this field.

## Integration Points

- **F-022 (Signal Scoring Engine)**: Writes `priority_score` and `reason` after scoring
- **F-026 (Ranking and Filtering)**: Reads `priority_score` for sorting
- **F-028 (Tests)**: Round-trip serialization test for new fields
- **Existing `watchlist_generator.py`**: `generate_daily()` MUST return entries with `priority_score=0.0` and `reason=""` by default (scoring happens in a later pipeline stage)

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Existing YAML files lack new fields | LOW | Lazy Upcast with defaults handles this |
| `why_now` vs `reason` confusion | MEDIUM | Document distinct semantics clearly |
| Schema version bump breaks consumers | LOW | Existing consumers use `from_dict()` which handles unknown fields |
