# TODO List: P1-2 Daily Watchlist Generator

**Session**: WFS-synapse-p1-2-watchlist
**Generated**: 2026-05-19T22:45:00+08:00

## Execution Summary

- **Total Tasks**: 7
- **Completed**: 5
- **In Progress**: 0
- **Pending**: 2
- **Execution Model**: Phased (sequential with parallel opportunities)
- **Critical Path**: IMPL-1 → IMPL-2 → IMPL-6 → IMPL-7

## Phase 1: Schema Extension

- [x] **IMPL-1**: WatchlistEntry Schema Extension (F-021) [High]
  - Add priority_score and reason fields
  - Add validation, update serialization
  - Add round-trip tests
  - Dependencies: None

## Phase 2: Scoring Engine Core

- [x] **IMPL-2**: Scoring Engine Core (F-022) [High]
  - Implement 4-dimension weighted sum model
  - Pipeline architecture
  - generate_daily() integration
  - Dependencies: IMPL-1

## Phase 3: Scoring Components (Parallel)

- [x] **IMPL-3**: Event-Driven Scoring (F-023) [High]
  - score_event_decay() using apply_category_decay()
  - Dependencies: IMPL-2

- [ ] **IMPL-4**: Portfolio-Aware Scoring (F-024) [High]
  - score_portfolio_boost() using thesis_status/attention_state
  - Dependencies: IMPL-2

- [x] **IMPL-5**: Market Semantics Scoring (F-025) [Medium]
  - score_market_context() using TradingCalendar/NorthboundFlow/IndexConstituent
  - Dependencies: IMPL-2

## Phase 4: Ranking & Filtering

- [x] **IMPL-6**: Ranking & Filtering (F-026) [Medium]
  - rank_entries() with stable sort
  - filter_entries() with top-N, min_score, dedup
  - Dependencies: IMPL-1, IMPL-2

## Phase 5: Tests

- [x] **IMPL-7**: Watchlist Tests (F-028) [High]
  - Extend test_projection.py
  - Coverage >= 80%
  - Dependencies: IMPL-1, IMPL-2, IMPL-6

## Dependency Graph

```
IMPL-1 (Schema)
    ↓
IMPL-2 (Scoring Engine)
    ↓
    ├── IMPL-3 (Event Scoring)
    ├── IMPL-4 (Portfolio Scoring)
    └── IMPL-5 (Market Scoring)
    
IMPL-1, IMPL-2 → IMPL-6 (Ranking & Filtering)
    
IMPL-1, IMPL-2, IMPL-6 → IMPL-7 (Tests)
```

## Notes

- F-027 (personalization config) is deferred to iteration 2
- All features use hardcoded defaults in P1-2
- Scoring is deterministic: identical inputs → identical outputs
- Graceful degradation: missing data contributes 0.0 (except market: 0.5)
