# Cross-Cutting Analysis: Data Model Decisions Across Features

## 1. Storage Strategy Decision

### Current State

The existing codebase uses YAML for WatchlistEntry storage (`save_watchlist` in `watchlist_generator.py`). Files are organized as `workspace/watchlists/{YYYY-MM-DD}/wl_{ticker}_{reason}.yaml`. Each file contains one serialized WatchlistEntry.

### Recommendation

P1-2 MUST continue YAML storage for WatchlistEntry files. The scoring configuration (weights, thresholds) SHOULD be stored in a separate YAML file at `workspace/config/scoring.yaml`. Parquet storage is NOT recommended for P1-2 because:
- WatchlistEntry count per day is small (< 100 entries typical)
- YAML readability aligns with the "boring solutions" coding philosophy
- Parquet adds dependency complexity without measurable performance gain at this scale

### Impact on Features

- F-021: New fields (`priority_score`, `reason`) serialize naturally into YAML
- F-026: Ranked output is the same WatchlistEntry list, just sorted — no new storage format needed
- F-027: ScoringConfig YAML file is the single new storage artifact

## 2. Schema Evolution Strategy

### Lazy Upcast Pattern

The codebase already uses Lazy Upcast (ADR-005) for Event v2.0 to v3.0 migration. P1-2 MUST follow the same pattern for WatchlistEntry schema version upgrade.

**WatchlistEntry v1.0 to v2.0 migration**:

```
v1.0 dict (no priority_score, no reason)
  → from_dict() applies defaults: priority_score=0.0, reason=""
  → Runtime object: valid v2.0 WatchlistEntry
  → to_dict() writes v2.0 with all fields
```

**Constraints**:
- `from_dict` MUST NOT raise on missing new fields — defaults MUST be supplied
- `to_dict` MUST always write the latest schema version (v2.0)
- `schema_version` field MUST be updated to "2.0" in the WatchlistEntry class definition

### Impact on Features

- F-021: Defines the schema version bump and Lazy Upcast contract
- F-028: Round-trip tests MUST cover v1.0 dict → v2.0 object → v2.0 dict path

## 3. Data Model Naming Conventions

### Existing Patterns

| Pattern | Example | Usage |
|---------|---------|-------|
| Frozen dataclass | `@dataclass frozen` is NOT used — current dataclasses are mutable | Existing code |
| to_dict/from_dict | All schemas implement this pair | Serialization |
| generate_id('wl') | WatchlistEntry ID prefix | Identity |
| Enum(str, Enum) | All enums inherit from str | YAML compatibility |

### P1-2 Additions

- **ScoreResult**: New frozen dataclass for scoring output. SHOULD use `@dataclass(frozen=True)` because scoring results are computed values that MUST NOT be mutated after creation.
- **DecayScore**: Value object wrapping a float decay factor. SHOULD be a simple dataclass or NamedTuple, not an enum.
- **ThesisAttentionMap**: Not a schema — it is a lookup dict derived from Position data. SHOULD be `dict[str, tuple[ThesisStatus, AttentionState]]` keyed by ticker.

## 4. Scoring Pipeline Data Flow

### Architecture

```
Input Layer:          Event[] + Signal[] + Position[]
                           |
                           v
Enrichment Layer:     Market Semantics validation (F-025)
                           |
                           v
Scoring Layer:        Event Decay (F-023) + Portfolio Awareness (F-024)
                           |
                           v
Composite Scoring:    Signal Scoring Engine (F-022)
                           |
                           v
Output Layer:         WatchlistEntry with priority_score + reason (F-021)
                           |
                           v
Ranking/Filtering:    Sorted + filtered output (F-026)
```

### Data Transformations

| Stage | Input Type | Output Type | Mutation? |
|-------|-----------|-------------|-----------|
| Event Decay | Event | DecayScore(float) | No — new value object |
| Portfolio Map | Position[] | ThesisAttentionMap | No — derived lookup |
| Signal Score | Signal + DecayScore + ThesisAttentionMap | ScoreResult | No — immutable |
| Composite | ScoreResult[] | WatchlistEntry.priority_score | No — writes to new field |
| Ranking | WatchlistEntry[] | WatchlistEntry[] (sorted) | No — new sorted list |

**All stages MUST be pure functions** — no side effects, no mutation of input objects. This aligns with the frozen dataclass pattern and enables deterministic testing.

## 5. Shared Data Constraints

### Float Range Convention

All probability-like floats in the system MUST be in [0.0, 1.0]:
- `Event.severity` — already validated in `__post_init__`
- `Event.confidence` — already validated
- `WatchlistEntry.priority_score` — MUST add same validation (F-021)
- `DecayScore.value` — MUST be in [0.0, 1.0]
- `ScoreResult.raw_score` — intermediate, MAY exceed [0.0, 1.0] before normalization

### ID Generation Convention

All new IDs MUST use `generate_id(prefix)`:
- WatchlistEntry: `generate_id('wl')` (existing)
- ScoringConfig: `generate_id('cfg')` (new, F-027)
- ScoreResult: No persistent ID — computed values, not stored entities

## 6. Error Handling Data Contract

### Graceful Degradation (system-architect decision)

When a data source is unavailable:
- Missing Event data: `Event.decay_rate` defaults to 0.1 (existing default), `DecayScore` returns neutral 0.5
- Missing Position data: `ThesisAttentionMap` returns empty dict, portfolio scoring skips (no boost, no penalty)
- Missing Signal data: `ScoreResult` returns 0.0 for signal component
- Overall: `priority_score` is computed from available components only; missing components contribute 0.0

**This MUST NOT raise exceptions** — the scoring pipeline MUST be resilient to partial data.
