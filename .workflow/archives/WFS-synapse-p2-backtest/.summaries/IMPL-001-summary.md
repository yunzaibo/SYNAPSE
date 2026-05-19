# Task: IMPL-001 Quintile Portfolio Sorter and Data Models

## Implementation Summary

### Files Created
- `synapse/backtest/result.py`: 5 frozen dataclasses (QuintilePortfolio, PerformanceMetrics, ICAnalysisResult, AttributionResult, BacktestRunResult)
- `synapse/backtest/quintile.py`: QuintileSorter class with sort() and sort_timeseries() methods
- `tests/unit/test_quintile_sorter.py`: 25 unit tests covering normal sorting, edge cases, immutability, serialization

### Files Modified
- `synapse/backtest/__init__.py`: Added exports for QuintileSorter and all 5 frozen dataclasses

### Content Added

#### Frozen Dataclasses (`synapse/backtest/result.py`)

- **QuintilePortfolio** (`result.py:22`): Immutable quintile assignment record. Fields: date, quintiles (dict[int, tuple[str, ...]]), weights (dict[int, dict[str, float]]), factor_name, universe_size, valid_count. Includes to_dict()/from_dict().
- **PerformanceMetrics** (`result.py:71`): 14-field performance record with defaults. Fields: annual_return, volatility, sharpe, max_drawdown, turnover, win_rate, excess_return, information_ratio, calmar, profit_loss_ratio, long_short_spread, max_drawdown_duration, skewness, kurtosis.
- **ICAnalysisResult** (`result.py:107`): Factor IC analysis. Fields: factor_id, ic_series, rank_ic_series, ic_mean, ic_std, icir, rank_ic_mean, rank_ic_std, rank_icir, rolling_ic, ic_positive_ratio.
- **AttributionResult** (`result.py:164`): Factor return attribution. Fields: factor_returns (dict[int, float]), residual_returns, total_factor_return, residual_return, r_squared.
- **BacktestRunResult** (`result.py:202`): Top-level container aggregating all sub-models. Fields: id, schema_version, config, run_timestamp, start_date, end_date, factor_id, quintile_portfolios, quintile_returns, long_short_returns, benchmark_returns, performance, ic_analysis, attribution, status, error.

#### QuintileSorter (`synapse/backtest/quintile.py`)

- **QuintileSorter.sort()** (`quintile.py:24`): Single-date sorting. Args: factor_values (pd.Series with MultiIndex date/ticker), target_date, n_quintiles=5, factor_name. Uses pd.qcut() with rank(method='first') for deterministic assignment. Returns QuintilePortfolio or None if insufficient data.
- **QuintileSorter.sort_timeseries()** (`quintile.py:85`): Multi-date sorting. Args: factor_values (pd.Series or single-column pd.DataFrame), rebalance_dates, n_quintiles=5, factor_name. Returns dict[date, QuintilePortfolio].

### Outputs for Dependent Tasks

#### Available Components
```python
from synapse.backtest.result import (
    QuintilePortfolio,
    PerformanceMetrics,
    ICAnalysisResult,
    AttributionResult,
    BacktestRunResult,
)
from synapse.backtest.quintile import QuintileSorter
```

#### Integration Points
- **QuintileSorter.sort()**: Takes FactorEngine output (pd.Series with MultiIndex date/ticker) and returns QuintilePortfolio for each rebalancing date.
- **QuintileSorter.sort_timeseries()**: Batch sorting for multiple dates, suitable for monthly rebalancing loops.
- **BacktestRunResult**: Top-level container for IMPL-006 (BacktestEngine Core) to aggregate all sub-results.
- **PerformanceMetrics**: Used by IMPL-002 (MetricsCalculator) for standardized metric output.
- **ICAnalysisResult**: Used by IMPL-003 (ICAnalyzer) for IC time series and statistics.
- **AttributionResult**: Used by IMPL-005 (AttributionEngine) for factor return decomposition.

### Test Coverage
- 25 tests in `tests/unit/test_quintile_sorter.py` -- all passing
- 14 existing backtest tests -- no regressions
- Test classes: TestQuintileSorterSort (10), TestQuintileSorterTimeseries (4), TestFrozenDataclasses (5), TestSerialization (6)

### Convergence Criteria Met
- 5 frozen dataclasses with frozen=True and slots=True (verified: 5 decorators + 1 docstring mention)
- QuintileSorter produces 5 equal-weight groups (verified: test_normal_5_quintile_sorting)
- Edge cases handled (all NaN, <5 stocks, single stock, exactly 5 stocks)
- Quintile weights sum to 1.0 within each group (verified: test_equal_weight_sum_to_one)

## Status: Complete
