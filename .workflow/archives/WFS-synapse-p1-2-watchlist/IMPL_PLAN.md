# Implementation Plan: P1-2 Daily Watchlist Generator

**Session**: WFS-synapse-p1-2-watchlist
**Created**: 2026-05-19T22:45:00+08:00
**Status**: Ready for Execution

## 1. Executive Summary

P1-2 Daily Watchlist Generator enhances the existing watchlist projection with signal scoring, event-driven filtering, portfolio-aware scoring, market semantics validation, ranking/filtering, and comprehensive tests. F-027 (personalization config) is deferred to iteration 2.

**Key Metrics**:
- Features: 7 (F-021 to F-026, F-028; F-027 deferred)
- Estimated Complexity: Medium-High
- Execution Model: Phased (sequential with parallel opportunities)
- Critical Path: F-021 → F-022 → F-026 → F-028

## 2. Scope

### In Scope

| Feature | Name | Priority | Description |
|---------|------|----------|-------------|
| F-021 | watchlist-schema-extension | High | WatchlistEntry schema 新增 priority_score 和 reason 字段 |
| F-022 | signal-scoring-engine | High | 基于 Signal、Event、Position 等多维度数据计算优先级分数 |
| F-023 | event-driven-filtering | High | 基于 Event lifecycle decay model 的时间衰减评分机制 |
| F-024 | portfolio-aware-scoring | High | 基于 Position thesis_status 和 attention_state 的持仓感知机制 |
| F-025 | market-semantics-validation | Medium | 集成 P1-1 Market Semantics（TradingCalendar、NorthboundFlow、IndexConstituent） |
| F-026 | ranking-and-filtering | Medium | 基于 priority_score 的排序和过滤机制 |
| F-028 | watchlist-tests | High | 扩展 test_projection.py，添加 scoring/ranking/filtering 测试 |

### Out of Scope

- F-027: personalization-config (deferred to iteration 2)
- Real-time push notifications
- Web/mobile UI
- ML-based recommendations
- Multi-market support (A-share only)
- Historical backtesting
- Custom scoring formulas

## 3. Architecture Overview

### Current State

```
synapse/core/projection/watchlist_generator.py (191 lines)
├── generate_daily() - basic merge of events+signals+positions
├── save_watchlist() - YAML serialization
├── _build_event_entries() - event-based entries
├── _build_signal_entries() - signal-based entries
└── _build_portfolio_entries() - portfolio-based entries
```

### Target State

```
synapse/core/projection/watchlist_generator.py (enhanced)
├── generate_daily() - 4-dimension scoring pipeline
├── save_watchlist() - YAML serialization (unchanged)
├── _build_event_entries() - event-based entries (unchanged)
├── _build_signal_entries() - signal-based entries (unchanged)
├── _build_portfolio_entries() - portfolio-based entries (unchanged)
├── _score_entries() - NEW: 4-dimension scoring pipeline
├── _rank_entries() - NEW: sort by priority_score
├── _filter_entries() - NEW: top-N, min_score, dedup
└── _validate_market_context() - NEW: trading day check

synapse/core/projection/scoring/ (NEW directory)
├── __init__.py
├── engine.py - ScoringEngine with pipeline architecture
├── signal_scorer.py - score_signal_contribution()
├── event_scorer.py - score_event_decay()
├── portfolio_scorer.py - score_portfolio_boost()
├── market_scorer.py - score_market_context()
├── aggregator.py - aggregate_scores() weighted sum
└── types.py - ScoredEntry, ScoringResult, ScoringContext
```

### Design Decisions (Resolved)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Scoring dimensions | 4 (signal, event, portfolio, market) | F-025 market semantics produces scoring signals |
| Default weights | signal=0.35, event=0.30, portfolio=0.20, market=0.15 | Signal captures real-time triggers; market is supplementary |
| Weight validation | Auto-normalize with warning | Product-manager non-crash requirement |
| F-027 scope | Deferred to iteration 2 | Default weights need 30-day user validation |
| YAML structure | Flat structure | Consistent with existing load_config() pattern |
| Invalid config | Warning + fallback to defaults | Satisfies non-crash requirement |

## 4. Implementation Strategy

### Execution Model: Phased

```
Phase 1: Schema Extension (F-021)
    ↓
Phase 2: Scoring Engine Core (F-022)
    ↓
Phase 3: Scoring Components (F-023, F-024, F-025) [PARALLEL]
    ↓
Phase 4: Ranking & Filtering (F-026)
    ↓
Phase 5: Tests (F-028)
```

### Phase Details

#### Phase 1: Schema Extension (F-021)
- **Task**: IMPL-1
- **Dependencies**: None (foundation)
- **Estimated Effort**: Low
- **Key Changes**:
  - Add `priority_score: float = 0.0` to WatchlistEntry
  - Add `reason: str = ""` to WatchlistEntry
  - Add `__post_init__` validation for priority_score range [0.0, 1.0]
  - Update `to_dict()` to include new fields
  - Update `from_dict()` with Lazy Upcast defaults
  - Add round-trip tests

#### Phase 2: Scoring Engine Core (F-022)
- **Task**: IMPL-2
- **Dependencies**: IMPL-1 (schema)
- **Estimated Effort**: High
- **Key Changes**:
  - Create `synapse/core/projection/scoring/` directory
  - Implement `ScoringEngine` with pipeline architecture
  - Implement `ScoredEntry`, `ScoringResult`, `ScoringContext` types
  - Implement `aggregate_scores()` with weighted sum
  - Implement `generate_daily()` with 4-dimension scoring
  - Add determinism tests

#### Phase 3: Scoring Components (F-023, F-024, F-025)
- **Tasks**: IMPL-3, IMPL-4, IMPL-5 (parallel)
- **Dependencies**: IMPL-2 (scoring engine)
- **Estimated Effort**: Medium each
- **Key Changes**:
  - F-023: `score_event_decay()` using `apply_category_decay()`
  - F-024: `score_portfolio_boost()` using thesis_status/attention_state
  - F-025: `score_market_context()` using TradingCalendar/NorthboundFlow/IndexConstituent
  - Each scorer returns `(score, reason)` tuple

#### Phase 4: Ranking & Filtering (F-026)
- **Task**: IMPL-6
- **Dependencies**: IMPL-1, IMPL-2
- **Estimated Effort**: Medium
- **Key Changes**:
  - Implement `rank_entries()` with stable sort
  - Implement `filter_entries()` with top-N, min_score, dedup
  - Implement `_validate_market_context()` for trading day check
  - Integration with `generate_daily()` pipeline

#### Phase 5: Tests (F-028)
- **Task**: IMPL-7
- **Dependencies**: IMPL-1, IMPL-2, IMPL-6
- **Estimated Effort**: High
- **Key Changes**:
  - Extend `tests/unit/test_projection.py`
  - Add scoring determinism tests
  - Add ranking/sorting tests
  - Add filtering tests
  - Add serialization round-trip tests
  - Achieve >80% coverage for scoring/ranking/filtering

## 5. Task Breakdown

| Task ID | Title | Feature | Phase | Dependencies | Estimated Effort |
|---------|-------|---------|-------|--------------|------------------|
| IMPL-1 | Schema Extension | F-021 | 1 | None | Low |
| IMPL-2 | Scoring Engine Core | F-022 | 2 | IMPL-1 | High |
| IMPL-3 | Event-Driven Scoring | F-023 | 3 | IMPL-2 | Medium |
| IMPL-4 | Portfolio-Aware Scoring | F-024 | 3 | IMPL-2 | Medium |
| IMPL-5 | Market Semantics Scoring | F-025 | 3 | IMPL-2 | Medium |
| IMPL-6 | Ranking & Filtering | F-026 | 4 | IMPL-1, IMPL-2 | Medium |
| IMPL-7 | Watchlist Tests | F-028 | 5 | IMPL-1, IMPL-2, IMPL-6 | High |

## 6. Critical Path

```
IMPL-1 (Schema) → IMPL-2 (Scoring Engine) → IMPL-6 (Ranking) → IMPL-7 (Tests)
```

**Critical Path Duration**: 4 phases
**Parallelization Opportunities**: Phase 3 (IMPL-3, IMPL-4, IMPL-5 can run in parallel)

## 7. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Schema breaking change | MEDIUM | Lazy Upcast with defaults; round-trip tests |
| Scoring non-determinism | HIGH | Golden file tests; deterministic data sources |
| Weight tuning complexity | MEDIUM | Fixed defaults in P1-2; F-027 (deferred) for customization |
| Test coverage gaps | MEDIUM | Enforce >80% coverage gate; extend existing patterns |
| Integration complexity | LOW | Phased approach; each phase independently testable |

## 8. Success Criteria

- [ ] All 7 features implemented and tested
- [ ] Test coverage > 80% for scoring, ranking, filtering
- [ ] All existing tests pass (no regressions)
- [ ] Scoring is deterministic (identical inputs → identical outputs)
- [ ] Graceful degradation on missing data
- [ ] Schema round-trip tests pass
- [ ] Code follows existing patterns (dataclass, YAML, snake_case)

## 9. Dependencies

### Internal Dependencies

- P1-1 Market Semantics (TradingCalendar, NorthboundFlow, IndexConstituent)
- P3 Event System (Event lifecycle, PropagationGraph, ImpactAnalyzer)
- P5 DataSource (EastMoney, Akshare adapters)
- Existing watchlist_generator.py (191 lines, basic implementation)

### External Dependencies

- pandas >= 2.0
- numpy >= 1.24
- pyyaml >= 6.0
- pytest >= 7.0

## 10. Next Steps

1. Execute IMPL-1: Schema Extension (F-021)
2. Execute IMPL-2: Scoring Engine Core (F-022)
3. Execute IMPL-3, IMPL-4, IMPL-5 in parallel (F-023, F-024, F-025)
4. Execute IMPL-6: Ranking & Filtering (F-026)
5. Execute IMPL-7: Watchlist Tests (F-028)
6. Run full test suite
7. Update documentation
