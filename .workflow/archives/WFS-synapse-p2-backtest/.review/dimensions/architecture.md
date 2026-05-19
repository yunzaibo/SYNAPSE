# Architecture Review: SYNAPSE P2 Long-Short Quintile Backtest Engine

**Session**: WFS-synapse-p2-backtest
**Date**: 2026-05-19
**Reviewer**: Architecture Review Agent
**Score**: 7.0 / 10

## Executive Summary

The `synapse/backtest/` module implements a well-structured quintile-sorting long-short backtest engine with dependency injection, frozen result dataclasses, and Parquet persistence. The separation of concerns across 9 files is solid, and the immutable result models are a strength. However, the architecture suffers from a significant God Method in `engine.py`, inconsistent state management in `MetricsCalculator`, and a confusing dual-API surface where legacy and modern paths coexist without a clear migration path.

---

## Strengths

### 1. Frozen Data Models (result.py)
All result types use `@dataclass(frozen=True, slots=True)`, providing thread safety, immutability guarantees, and efficient memory usage.

### 2. Dependency Injection Pattern (engine.py:100-117)
The `BacktestEngine.__init__` accepts optional component instances with sensible defaults, enabling mock injection in tests.

### 3. Config Validation (config.py:21-32)
"no silent defaults" philosophy for cost parameters prevents accidental zero-cost backtests.

### 4. Comprehensive Edge Case Handling
Every component handles empty/insufficient data gracefully.

### 5. Schema Versioning in Persistence (persistence.py)
Parquet persistence embeds `schema_version` in file metadata with `_lazy_upcast` for backward compatibility.

### 6. Single-Pass MetricsCalculator (metrics.py:83-266)
All 14 metrics computed in a single O(n) pass.

---

## Issues

### Critical

#### C1. Mutable State Mutation of Injected Component (engine.py:292-296)
```python
self.metrics_calc._benchmark_returns = (
    request.benchmark_returns.values
    if request.benchmark_returns is not None
    else None
)
```
**Problem**: Engine directly mutates private attribute of injected `MetricsCalculator`. Breaks DI contract.
**Impact**: Concurrent runs corrupt state, component not reusable.
**Fix**: Pass `benchmark_returns` as parameter to `MetricsCalculator.compute()`.

### High

#### H1. God Method: `_run_pipeline` (engine.py:155-367)
~210 lines handling date normalization, sorting, simulation, metrics, IC, attribution, spread, and result assembly.
**Fix**: Extract `_simulate_returns` and `_assemble_result` sub-methods.

#### H2. Dual Metrics Implementation (metrics.py)
Two implementations: `compute_metrics()` (8 fields) and `MetricsCalculator` (14 fields).
**Fix**: Deprecate `compute_metrics()` with warning.

#### H3. Legacy `run_backtest` Duplicates Logic (engine.py:500-593)
Does not use DI components, so bug fixes don't propagate.
**Fix**: Delegate to DI components or mark deprecated.

### Medium

#### M1. No Interface Contracts for DI Components
No Protocol/ABC for component interfaces.
**Fix**: Define `SorterProtocol`, `MetricsProtocol`, etc.

#### M2. BacktestConfig Is Mutable (config.py:4)
Unlike frozen result dataclasses.
**Fix**: Make `BacktestConfig` frozen.

#### M3. Hardcoded Quintile Column Names (spread.py:100-101)
Assumes Q1-Q5 naming.
**Fix**: Parameterize quintile IDs.

#### M4. Engine Constructor Lacks Type Annotations (engine.py:100-106)
**Fix**: Add proper type hints.

#### M5. Date Type Normalization Fragility (engine.py:396-426)
Runtime type detection instead of boundary enforcement.
**Fix**: Normalize at `BacktestRequest` boundary.

### Low

#### L1. `_config_to_dict` Duplicates Config Fields
**Fix**: Use `dataclasses.asdict()`.

#### L2. `benchmark_returns` Length Mismatch Silently Ignored
**Fix**: Add warning when padding with zeros.

#### L3. `_lazy_upcast` Is No-Op Placeholder
**Fix**: Remove if not needed soon.

---

## Recommendations (Priority Order)

1. **Fix MetricsCalculator state mutation** (C1)
2. **Extract engine._run_pipeline sub-methods** (H1)
3. **Define Protocol interfaces** (M1)
4. **Deprecate legacy `run_backtest`** (H3)
5. **Make BacktestConfig frozen** (M2)
6. **Add type annotations to engine constructor** (M4)

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Concurrent runs corrupt MetricsCalculator state | High | Medium | Refactor compute() to accept benchmark as parameter |
| Legacy API diverges from modern pipeline | High | High | Deprecate or delegate to DI components |
| New Config fields silently dropped from persistence | Medium | Low | Replace `_config_to_dict` with `asdict()` |
| Spread computation breaks with non-5 quintiles | Medium | Low | Parameterize quintile IDs |
| Date type inconsistencies cause subtle bugs | Medium | Medium | Normalize at request boundary |
