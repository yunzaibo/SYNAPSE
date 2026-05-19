# Data Architect Analysis: P1-2 Daily Watchlist Generator

## Role Perspective Overview

Data-architect perspective on P1-2 focuses on the data model evolution, storage strategy, serialization contracts, and schema versioning for the Daily Watchlist Generator. The analysis covers how `WatchlistEntry` extends with `priority_score` and `reason` fields, how scoring data flows through the system, how event decay and portfolio awareness translate into data structures, and how the YAML/Parquet storage strategy holds up under daily full regeneration (ADR-009).

Key principles guiding this analysis:
- **Frozen Dataclass consistency** — all entities MUST follow existing `BaseSchema` + `to_dict/from_dict` pattern
- **Lazy Upcast** — new fields MUST carry defaults so existing v1.0 dicts remain valid (ADR-005)
- **Daily Full Regeneration** — storage MUST support overwrite semantics, not incremental patches
- **Dependency Injection** — data access through function parameters, not global state

## Feature Point Index

| Feature | Analysis File | Key Decisions |
|---------|--------------|---------------|
| F-021 watchlist-schema-extension | [analysis-F-021-watchlist-schema-extension.md](./analysis-F-021-watchlist-schema-extension.md) | priority_score float range [0.0,1.0], reason str, Lazy Upcast defaults |
| F-022 signal-scoring-engine | [analysis-F-022-signal-scoring-engine.md](./analysis-F-022-signal-scoring-engine.md) | ScoreResult immutable dataclass, composite scoring from Signal/Event/Position |
| F-023 event-driven-filtering | [analysis-F-023-event-driven-filtering.md](./analysis-F-023-event-driven-filtering.md) | DecayScore value object, exponential decay from Event.decay_rate |
| F-024 portfolio-aware-scoring | [analysis-F-024-portfolio-aware-scoring.md](./analysis-F-024-portfolio-aware-scoring.md) | ThesisAttentionMap lookup, Position.research_state scoring multipliers |
| F-025 market-semantics-validation | [analysis-F-025-market-semantics-validation.md](./analysis-F-025-market-semantics-validation.md) | TradingCalendar gate, NorthboundFlow/IndexConstituent enrichment |
| F-026 ranking-and-filtering | [analysis-F-026-ranking-and-filtering.md](./analysis-F-026-ranking-and-filtering.md) | RankedWatchlist immutable output, top-N selection with tie-breaking |
| F-027 personalization-config | [analysis-F-027-personalization-config.md](./analysis-F-027-personalization-config.md) | ScoringConfig YAML schema, weight/floor/ceiling constraints |
| F-028 watchlist-tests | [analysis-F-028-watchlist-tests.md](./analysis-F-028-watchlist-tests.md) | Round-trip serialization tests, scoring determinism tests |

## Cross-Cutting Concerns

See [analysis-cross-cutting.md](./analysis-cross-cutting.md) for shared decisions spanning multiple features: storage strategy, schema evolution, data model naming conventions, and scoring pipeline data flow.

## Key Recommendations

1. **priority_score MUST be float [0.0, 1.0] with __post_init__ validation** — consistent with Event.severity/confidence range pattern already in codebase
2. **ScoreResult MUST be a separate frozen dataclass, not embedded in WatchlistEntry** — keeps scoring logic decoupled from storage schema, enables testing without serialization overhead
3. **Daily full regeneration storage MUST use date-directory overwrite** — existing `save_watchlist` already follows this pattern; scoring output SHOULD write alongside watchlist entries in the same directory
4. **ScoringConfig MUST live in YAML** — consistent with existing config strategy, enables user editing without code changes
5. **Lazy Upcast for new fields** — `from_dict` MUST supply `priority_score=0.0` and `reason=""` defaults so existing v1.0 WatchlistEntry dicts remain parseable
