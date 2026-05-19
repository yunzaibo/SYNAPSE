# Quality Review: SYNAPSE P2 Long-Short Quintile Backtest Engine

**Session**: WFS-synapse-p2-backtest
**Date**: 2026-05-19
**Reviewer**: Quality Review Agent
**Score**: 8.0 / 10

## Executive Summary

The `synapse/backtest/` module is a well-structured, thoroughly tested quantitative backtest engine. It achieves **223 passing tests** (148 unit + 75 integration) with a strong test-to-code ratio (approximately 4.3:1 by line count). The code demonstrates solid engineering: frozen dataclasses for immutability, DI-driven architecture, comprehensive edge case handling, and Parquet-based persistence with schema versioning.

---

## Quality Score Breakdown

| Dimension | Score | Notes |
|-----------|-------|-------|
| Test Coverage | 9/10 | Excellent breadth, every API method tested |
| Code Correctness | 8/10 | Algorithms sound, one shared-state mutation issue |
| Error Handling | 8/10 | Graceful degradation, some areas need more logging |
| Performance | 7/10 | Benchmark passes, some optimization opportunities |
| Best Practices | 8/10 | PEP 8, type annotations, frozen dataclasses |

---

## Test Coverage Analysis

| Module | Source LOC | Test LOC | Unit Tests | Coverage |
|--------|-----------|----------|------------|----------|
| engine.py | 593 | 551 + 638 | 23 | 96% |
| config.py | 32 | 59 + 545 | 3 | 100% |
| quintile.py | 141 | 326 | 10 | 98% |
| metrics.py | 279 | 393 + 86 | 17 | 98% |
| ic_analyzer.py | 148 | 262 | 10 | 96% |
| attribution.py | 101 | 224 | 8 | 100% |
| spread.py | 135 | 158 | 7 | 100% |
| persistence.py | 425 | 451 | 16 | 96% |
| result.py | 275 | Part of quintile tests | 10 | 100% |

**Total**: 223 tests, 98% coverage

---

## Issues Found

### High (2)

#### H1. Shared mutable state in MetricsCalculator (engine.py:292-294)
Engine directly mutates `self.metrics_calc._benchmark_returns` on every `run()` call.
**Fix**: Pass `benchmark_returns` as parameter to `compute()`.

#### H2. Attribution reconstruction discards valid zero-valued attributions (persistence.py:336-339)
When `total_factor_return=0.0` but `factor_returns` is non-empty, data is silently lost.
**Fix**: Use presence-based check instead of zero-value check.

### Medium (5)

#### M1. Attribution receives misaligned data (engine.py:383-393)
Uses portfolio return as both dependent and independent variable (degenerate OLS).
**Fix**: Compute real per-quintile factor returns or remove for P2.

#### M2. Legacy cost model differs from new API (engine.py:567)
Different turnover calculation produces different cost values.
**Fix**: Align cost models or document difference.

#### M3. BacktestConfig is mutable (config.py)
Plain `@dataclass` while result dataclasses are frozen.
**Fix**: Make `BacktestConfig` frozen.

#### M4. Hardcoded Q5/Q1 column names (spread.py:100-101)
Will raise `KeyError` if column names differ.
**Fix**: Parameterize top/bottom quintile selection.

#### M5. No logging in engine
Zero `logger.debug/info/warning` calls.
**Fix**: Add debug-level logging for diagnostics.

### Low (6)

- L1: Excessive deferred imports in engine.py
- L2: `_config_to_dict` duplicates logic
- L3: `compute_metrics` and `MetricsCalculator` overlap
- L4: Unused `import` in spread.py
- L5: Broad exception handling in `query_results`
- L6: Legacy `BacktestResult` not frozen

---

## Code Smells

1. **God method**: `_run_pipeline` (212 lines)
2. **Feature envy**: Engine reaches into `metrics_calc._benchmark_returns`
3. **Magic numbers**: `252` appears without named constant
4. **Inconsistent date handling**: Dual normalization paths

---

## Recommendations

### Immediate (Before Merge)
1. Fix H1: Refactor `MetricsCalculator.compute()` to accept `benchmark_returns`
2. Fix H2: Use presence-based check in attribution reconstruction
3. Fix M4: Parameterize quintile selection in spread

### Short-Term (Next Sprint)
4. Refactor `_run_pipeline` into smaller methods
5. Make `BacktestConfig` frozen
6. Align cost models between legacy and new API
7. Add engine-level logging

### Medium-Term
8. Property-based testing with Hypothesis
9. Pre-group forward returns for performance
10. Deprecate `compute_metrics()` / `BacktestMetrics`
