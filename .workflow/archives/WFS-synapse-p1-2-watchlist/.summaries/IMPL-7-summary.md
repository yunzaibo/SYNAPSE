# Task: IMPL-7 Watchlist Tests

## Implementation Summary

### Files Modified
- `tests/unit/test_projection.py`: Added 79 new comprehensive tests across 13 new test classes

### Test Coverage Results

| Module | Before | After | Change |
|--------|--------|-------|--------|
| scoring/aggregator.py | 92% | 100% | +8% |
| scoring/engine.py | 100% | 100% | -- |
| scoring/event_scorer.py | 98% | 100% | +2% |
| scoring/market_scorer.py | 100% | 100% | -- |
| scoring/portfolio_scorer.py | 100% | 100% | -- |
| scoring/types.py | 96% | 100% | +4% |
| projection/timeline.py | 98% | 100% | +2% |
| watchlist_generator.py | 82% | 99% | +17% |
| **TOTAL** | **93%** | **97%** | **+4%** |

### New Test Classes Added

- **TestBuildReason**: 4 tests for `build_reason()` format, missing dims, neutral market, ordering
- **TestScoringResultRoundtrip**: 5 tests for `ScoringResult`, `MarketData`, `ScoringContext` serialization
- **TestWatchlistEntrySerialization**: 5 tests for full roundtrip with signals, triggers, linked IDs
- **TestRankingEdgeCases**: 4 tests for same scores, determinism, mixed sorting
- **TestFilteringEdgeCases**: 9 tests for boundary thresholds, dedup, multiple triggers, large lists
- **TestSignalScoring**: 5 tests for weak/medium/strong, count bonus, multi-ticker
- **TestPortfolioScoringEdgeCases**: 5 tests for all combinations, fading, unknown, duplicates
- **TestEventScoringEdgeCases**: 5 tests for naive datetime, zero impact, ancient events, multi-type
- **TestPositionRebuilderExtended**: 7 tests for update-existing, review outcomes, sell-orphan, multi-ticker
- **TestTimelineExtended**: 4 tests for empty statement, revision entry, mixed artifacts, entry dict
- **TestMarketScoringExtended**: 4 tests for clamped outflow, bearish/bullish, unavailable
- **TestGenerateDailyExtended**: 5 tests for determinism, dedup, portfolio ranking, min_score, max_entries
- **TestScoringEngineExtended**: 5 tests for batch, empty, config hash, all-zero
- **TestSaveWatchlist**: 5 tests for file creation, empty, subdir, naming conventions
- **TestAggregatorExtended**: 6 tests for clamped range, single dim, zero total, all dims

### Key Coverage Gaps Fixed
- `build_reason()` in aggregator.py: now fully tested
- `ScoringResult.from_dict()` in types.py: now fully tested
- `save_watchlist()` in watchlist_generator.py: now tested with tmp_path
- `_score_signal()` count bonus logic: now tested for all strength levels
- Position rebuilder update-existing branch: now tested
- Event scorer naive datetime branch: now tested

## Outputs for Dependent Tasks

### Test Patterns Established
- Use `_make_wl_entry()` helper for quick scored WatchlistEntry creation
- Use `tmp_path` pytest fixture for file I/O tests (save_watchlist)
- Signal scoring includes count_bonus: `min(len(relevant) * 0.1, 0.3)`
- filter_entries dedup keeps first occurrence (assumed highest in ranked input)

## Status: Complete
