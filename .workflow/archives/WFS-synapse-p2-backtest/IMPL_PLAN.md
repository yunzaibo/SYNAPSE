# Implementation Plan: P2 Long-Short Quintile Backtest Engine

**Session**: WFS-synapse-p2-backtest
**Date**: 2026-05-19
**Complexity**: Medium (8 tasks, 8 features)
**Estimated Time**: 3-5 days
**Execution**: Phased (agent-based)

---

## Overview

Build a long-short quintile backtest engine for A-share factor research, integrating with P6 FactorEngine and P1 Market Semantics. The engine provides 5-quintile portfolio sorting, 8 core performance metrics, factor IC analysis, return attribution, and Parquet-based result persistence.

**Architecture**: Three-layer event-driven architecture (Data -> Signal -> Execution -> Orchestration) with dependency injection for testability and composability.

**Key Design Decisions**:
- Frozen dataclasses (`frozen=True, slots=True`) for all result objects (consistency with P1)
- DataFrame MultiIndex `(date, ticker)` as data contract between P6 FactorEngine and P2
- Parquet for durable storage, in-memory DataFrames for intermediate calculations
- Dependency injection in BacktestEngine for unit testing and component swapping

---

## Task Details

### IMPL-001: Quintile Portfolio Sorter and Data Models

**Dependencies**: None (foundation task)
**Files**:
- `synapse/backtest/result.py` (create) - 5 frozen dataclasses
- `synapse/backtest/quintile.py` (create) - QuintileSorter class
- `tests/unit/test_quintile_sorter.py` (create) - 8+ test cases

**Deliverables**:
- 5 frozen dataclasses: QuintilePortfolio, PerformanceMetrics (14 fields), ICAnalysisResult, AttributionResult, BacktestResult
- QuintileSorter with `sort()` and `sort_timeseries()` methods
- Edge case handling: all NaN, <5 stocks, ties

**Acceptance Criteria**:
- 5 frozen dataclasses with `frozen=True, slots=True`
- Quintile weights sum to 1.0 within each group
- Deterministic sorting with `method='first'`

---

### IMPL-002: Performance Metrics Calculator

**Dependencies**: IMPL-001
**Files**:
- `synapse/backtest/metrics.py` (modify) - Add MetricsCalculator class
- `tests/unit/test_metrics_calculator.py` (create) - 10+ test cases

**Deliverables**:
- MetricsCalculator with stateful single-pass computation
- 8 core metrics: annual_return, volatility, sharpe, max_drawdown, turnover, win_rate, excess_return, information_ratio
- Extended metrics: calmar, profit_loss_ratio, cumulative_return, annual_turnover
- Backward compatibility: existing `compute_metrics()` preserved

**Acceptance Criteria**:
- All 8 metrics computed in single pass
- Zero volatility handled (Sharpe = 0.0)
- Legacy `compute_metrics()` still works

---

### IMPL-003: Factor IC Analysis

**Dependencies**: IMPL-001
**Files**:
- `synapse/backtest/ic_analyzer.py` (create) - ICAnalyzer class
- `tests/unit/test_ic_analyzer.py` (create) - 6+ test cases

**Deliverables**:
- ICAnalyzer with cross-sectional RankIC computation
- Rolling IC with configurable window (default 20)
- ICIR = mean(IC) / std(IC)
- IC positive ratio

**Acceptance Criteria**:
- RankIC matches scipy.stats.spearmanr
- Rolling window parameter controls output length
- Frozen ICAnalysisResult returned

---

### IMPL-004: Long-Short Spread Calculation

**Dependencies**: IMPL-001
**Files**:
- `synapse/backtest/spread.py` (create) - LongShortSpread class
- `tests/unit/test_long_short_spread.py` (create) - 6+ test cases

**Deliverables**:
- LongShortSpread with spread returns (Q5 - Q1)
- Cumulative spread calculation
- Optional benchmark comparison (CSI 300)
- Annualized metrics

**Acceptance Criteria**:
- Spread = Q5 - Q1 verified
- Cumulative spread = product(1+spread) - 1
- Missing benchmark handled gracefully

---

### IMPL-005: Return Attribution Engine

**Dependencies**: IMPL-001
**Files**:
- `synapse/backtest/attribution.py` (create) - AttributionEngine class
- `tests/unit/test_attribution_engine.py` (create) - 6+ test cases

**Deliverables**:
- AttributionEngine with Barra-style OLS decomposition
- Factor + residual = total return
- R-squared for model fit
- Multi-factor ready (P2: single factor)

**Acceptance Criteria**:
- Factor contribution + residual = total return (within tolerance)
- R-squared computed correctly
- Frozen AttributionResult returned

---

### IMPL-006: Backtest Engine Core (Orchestration)

**Dependencies**: IMPL-001, IMPL-002, IMPL-003, IMPL-004, IMPL-005
**Files**:
- `synapse/backtest/engine.py` (modify) - Refactor with DI
- `synapse/backtest/config.py` (modify) - Extend BacktestConfig
- `synapse/backtest/__init__.py` (modify) - Export new components
- `tests/unit/test_backtest_engine.py` (modify) - Extend tests

**Deliverables**:
- BacktestRequest frozen dataclass
- Refactored BacktestEngine with DI constructor
- CostModel extraction
- Full pipeline: sort -> simulate -> metrics -> IC -> attribution
- Legacy `run_backtest()` preserved as wrapper

**Acceptance Criteria**:
- DI components injected correctly
- Full pipeline produces frozen BacktestResult
- Legacy interface backward compatible
- TradingCalendar integration for rebalance dates

---

### IMPL-007: Backtest Result Persistence

**Dependencies**: IMPL-001, IMPL-002
**Files**:
- `synapse/backtest/persistence.py` (create) - Parquet read/write
- `tests/unit/test_persistence.py` (create) - 6+ test cases

**Deliverables**:
- `save_result()` - BacktestResult to Parquet
- `load_result()` - Parquet to BacktestResult with lazy upcast
- `query_results()` - Filter by date range and factor name
- Schema versioning in Parquet metadata

**Acceptance Criteria**:
- Save/load roundtrip preserves all fields
- Schema version in Parquet metadata
- Query API filters correctly

---

### IMPL-008: End-to-End Integration Tests

**Dependencies**: IMPL-006, IMPL-007
**Files**:
- `tests/integration/test_backtest_pipeline.py` (create) - 5+ tests
- `tests/integration/test_p6_integration.py` (create) - 4+ tests
- `tests/integration/test_p1_calendar_integration.py` (create) - 3+ tests

**Deliverables**:
- Full pipeline tests with synthetic data
- P6 FactorEngine data contract validation
- P1 TradingCalendar integration validation
- Performance benchmarks
- Code coverage >=90%

**Acceptance Criteria**:
- All integration tests pass
- P6 data contract validated
- P1 calendar integration validated
- Code coverage >=90%

---

## File Layout

```
synapse/backtest/
  __init__.py          # exports all public API
  config.py            # BacktestConfig (extended)
  engine.py            # BacktestEngine (refactored with DI)
  metrics.py           # MetricsCalculator (extended)
  quintile.py          # NEW: QuintileSorter
  ic_analyzer.py       # NEW: ICAnalyzer
  attribution.py       # NEW: AttributionEngine
  spread.py            # NEW: LongShortSpread
  persistence.py       # NEW: Parquet storage
  result.py            # NEW: All frozen dataclasses

tests/
  unit/
    test_quintile_sorter.py      # NEW
    test_metrics_calculator.py   # NEW
    test_ic_analyzer.py          # NEW
    test_long_short_spread.py    # NEW
    test_attribution_engine.py   # NEW
    test_backtest_engine.py      # Extended
    test_persistence.py          # NEW
  integration/
    test_backtest_pipeline.py    # NEW
    test_p6_integration.py       # NEW
    test_p1_calendar_integration.py  # NEW
```

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| pd.qcut edge cases | Non-deterministic quintiles | Use rank-based approach with method='first' |
| Zero volatility in Sharpe | Division by zero | Guard with std > 1e-10 check |
| OLS numerical instability | Wrong attribution | Use np.linalg.lstsq with rcond |
| Schema evolution breaks old files | Data loss | Lazy upcast with default values |
| Large dataset performance | Slow UX | Vectorized operations, optional parallelism |

---

## Validation Checklist

- [ ] All 8 task JSONs follow unified flat schema
- [ ] Every task has `cli_execution.id` and computed `cli_execution.strategy`
- [ ] All requirements contain explicit counts or enumerated lists
- [ ] All acceptance criteria are measurable with verification commands
- [ ] Task count within limits (<=8)
- [ ] No circular dependencies in `depends_on` chains
- [ ] `plan.json` aggregates all task IDs and shared context
- [ ] `IMPL_PLAN.md` follows template structure
- [ ] `TODO_LIST.md` links correctly to task JSONs
- [ ] Artifact references match actual brainstorming artifact paths
