# System Architect Analysis: P1-2 Daily Watchlist Generator

## Role Perspective Overview

This analysis examines the P1-2 Daily Watchlist Generator from a system architecture perspective, focusing on technical architecture, scalability, integration patterns, error handling, and observability. The watchlist generator is a Projection that synthesizes Signal, Event, and Position data into a ranked daily research queue.

The existing codebase already provides a solid foundation: `watchlist_generator.py` implements the ADR-009 daily full regeneration pattern, `WatchlistEntry` schema follows the Weak Schema + Lazy Upcast strategy, and the event lifecycle module provides a mature decay model. P1-2 extends this foundation by introducing priority scoring, event-driven decay integration, portfolio-aware weighting, and market semantics validation.

**Key Architectural Insight**: The current `generate_daily()` function produces flat, unranked entries. P1-2 transforms this into a scored, ranked, and filtered pipeline -- a scoring engine layered on top of the existing entry-building functions.

## Feature Point Index

| Feature | Analysis File | Key Decisions |
|---------|--------------|---------------|
| F-021 watchlist-schema-extension | [analysis-F-021-watchlist-schema-extension.md](./analysis-F-021-watchlist-schema-extension.md) | Lazy Upcast for priority_score/reason; Frozen Dataclass immutability preserved |
| F-022 signal-scoring-engine | [analysis-F-022-signal-scoring-engine.md](./analysis-F-022-signal-scoring-engine.md) | Pipeline architecture with composable scoring functions; weighted sum model |
| F-023 event-driven-filtering | [analysis-F-023-event-driven-filtering.md](./analysis-F-023-event-driven-filtering.md) | Reuse existing `apply_category_decay()`; PropagationState as filter predicate |
| F-024 portfolio-aware-scoring | [analysis-F-024-portfolio-aware-scoring.md](./analysis-F-024-portfolio-aware-scoring.md) | ThesisStatus/AttentionState as scoring multipliers; position recency boost |
| F-025 market-semantics-validation | [analysis-F-025-market-semantics-validation.md](./analysis-F-025-market-semantics-validation.md) | TradingCalendar gate; NorthboundFlow/IndexConstituent as scoring signals |
| F-026 ranking-and-filtering | [analysis-F-026-ranking-and-filtering.md](./analysis-F-026-ranking-and-filtering.md) | Stable sort by priority_score; configurable top-N cutoff; dedup by ticker |
| F-027 personalization-config | [analysis-F-027-personalization-config.md](./analysis-F-027-personalization-config.md) | YAML config with schema validation; default weights with user override |
| F-028 watchlist-tests | [analysis-F-028-watchlist-tests.md](./analysis-F-028-watchlist-tests.md) | Extend test_projection.py; scoring determinism tests; round-trip serialization |

## Cross-Cutting Concerns

See [analysis-cross-cutting.md](./analysis-cross-cutting.md) for shared architectural decisions spanning multiple features, including data model design, error handling strategy, observability requirements, and configuration model.

## Key Recommendations

1. **Pipeline Architecture**: The scoring engine SHOULD be implemented as a pipeline of composable scoring functions, each returning a score contribution. This enables independent testing, easy extension, and clear separation of concerns (F-022).

2. **Reuse Existing Decay Model**: The `apply_category_decay()` function in `event/lifecycle.py` already implements exponential decay with category-specific half-lives. F-023 MUST reuse this rather than implementing a parallel decay mechanism (F-023).

3. **Graceful Degradation on Data Source Failure**: The scoring pipeline SHOULD produce partial scores when individual data sources are unavailable, rather than failing entirely. This aligns with the existing Graceful Degradation strategy decision (cross-cutting).

4. **Frozen Dataclass Immutability**: All new data structures MUST maintain the Frozen Dataclass pattern established by existing schemas. This ensures thread safety and cacheability for the scoring pipeline (F-021, F-022).

5. **Observability from Day One**: The scoring pipeline MUST emit structured metrics (score distribution, data source latency, filter pass rates) to enable performance tuning and debugging (cross-cutting).

## Framework Reference

This analysis addresses all discussion points from @../guidance-specification.md, specifically:
- Section 4 (System Architect Decisions): Projection architecture, Daily Full Regeneration, Dependency Injection, Graceful Degradation
- Section 5 (Data Architect Decisions): Schema design, YAML storage, Frozen Dataclass, ID generation, serialization
- Section 7 (Cross-Role Integration): Schema extension, market semantics integration, event-driven scoring, portfolio-aware scoring, data source integration
- Section 8 (Risks & Constraints): Schema breaking change, performance impact, data source availability, configuration complexity
