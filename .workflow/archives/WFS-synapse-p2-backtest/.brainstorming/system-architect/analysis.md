# P2 Long-Short Quintile Backtest Engine -- System Architect Analysis

**Metadata**: 2026-05-19, system-architect, quantitative-backtest, [architecture, interfaces, data-flow, integration, error-handling, configuration, performance]

## 1. Architecture

### 1.1 Layered Architecture Overview

The P2 backtest engine adopts a **three-layer event-driven architecture** aligned with the guidance specification (D-003). The layers are strictly separated by responsibility, enabling independent testing and flexible composition.

```
+-------------------------------------------------------------------+
|                       Orchestration Layer                          |
|            BacktestEngine (orchestrates full pipeline)             |
+-------------------------------------------------------------------+
         |                    |                    |
         v                    v                    v
+------------------+  +------------------+  +------------------+
|   Signal Layer   |  | Execution Layer  |  | Analytics Layer  |
|                  |  |                  |  |                  |
| - QuintileSorter |  | - PortfolioSim   |  | - MetricsCalc    |
| - ICAnalyzer     |  | - TradeExecutor  |  | - ICAnalyzer     |
| - Attribution    |  | - CostModel      |  | - AttributionEng |
+------------------+  +------------------+  +------------------+
         |                    |                    |
         v                    v                    v
+-------------------------------------------------------------------+
|                        Data Layer                                  |
|  FactorEngine (P6) | DataSource | TradingCalendar (P1)           |
|  ExRightAdjustment (P1) | Parquet Storage                        |
+-------------------------------------------------------------------+
```

**Layer Responsibilities**:

- **Data Layer**: Raw data access, factor computation, calendar operations, price adjustment. Delegates to P6 FactorEngine and P1 Market Semantics.
- **Signal Layer**: Factor-to-signal conversion (quintile sorting), IC/RankIC analysis, return attribution decomposition.
- **Execution Layer**: Portfolio simulation (equal-weight allocation, rebalancing), transaction cost modeling, trade tracking.
- **Orchestration Layer**: Coordinates the full pipeline from factor values to final results. Single entry point.

### 1.2 Event-Driven Justification

The existing `BacktestEngine` already follows an implicit event model: each rebalance period is a "tick" that triggers sorting, allocation, and cost deduction. P2 formalizes this with explicit data objects flowing between components, rather than a pub/sub bus. The rationale:

1. **Testability**: Each component accepts data objects and returns results -- no shared mutable state.
2. **Composability**: Components can be swapped (e.g., different cost models, different sorting methods).
3. **Alignment with P6**: FactorEngine already uses PartialResult for error containment; the same pattern extends naturally.

### 1.3 Module Structure

```
synapse/backtest/
    __init__.py          # Public API exports
    config.py            # BacktestConfig (extend existing)
    engine.py            # BacktestEngine (refactor existing)
    metrics.py           # MetricsCalculator (extend existing)
    quintile.py          # NEW: QuintileSorter
    ic_analyzer.py       # NEW: ICAnalyzer
    attribution.py       # NEW: AttributionEngine
    cost_model.py        # NEW: CostModel (transaction cost abstraction)
    result.py            # NEW: BacktestResult, QuintilePortfolio, PerformanceMetrics (frozen dataclasses)
    persistence.py       # NEW: Parquet storage for results
```

## 2. Core Interfaces

### 2.1 BacktestEngine (refactored from existing)

The existing `BacktestEngine.run_backtest()` takes raw `pd.Series` and `BacktestConfig`. P2 refactors this into a richer interface that separates concerns.

```python
@dataclass(frozen=True)
class BacktestRequest:
    """Immutable request to run a backtest."""
    factor_values: pd.DataFrame          # MultiIndex (date, ticker), columns = factor_ids
    forward_returns: pd.Series           # MultiIndex (date, ticker)
    config: BacktestConfig
    benchmark_returns: Optional[pd.Series] = None  # Optional CSI 300 benchmark

class BacktestEngine:
    """Orchestrates the full backtest pipeline.

    Dependencies (injected):
        sorter: QuintileSorter -- factor-to-portfolio mapping
        metrics_calc: MetricsCalculator -- return-to-metrics computation
        ic_analyzer: ICAnalyzer -- factor IC analysis
        attribution: AttributionEngine -- return attribution
    """

    def __init__(
        self,
        sorter: QuintileSorter,
        metrics_calc: MetricsCalculator,
        ic_analyzer: ICAnalyzer,
        attribution: AttributionEngine,
    ) -> None: ...

    def run(self, request: BacktestRequest) -> BacktestResult:
        """Execute full pipeline: sort -> simulate -> measure -> attribute."""
        ...
```

**Design Decision**: Dependency injection over hardcoded composition. This allows:
- Unit testing with mock components
- Swapping sorting strategies (quintile vs. tercile vs. custom)
- Optional IC analysis or attribution (can be None/skipped)

### 2.2 QuintileSorter (NEW)

```python
@dataclass(frozen=True)
class QuintilePortfolio:
    """Immutable portfolio assignment for a single rebalance date."""
    rebalance_date: date
    long_tickers: tuple[str, ...]         # Top quintile (Q5)
    short_tickers: tuple[str, ...]        # Bottom quintile (Q1)
    quintile_labels: dict[str, int]       # ticker -> quintile (1-5)
    weights: dict[str, float]             # ticker -> weight (equal within quintile)

class QuintileSorter:
    """Sort stocks into quintiles by factor value.

    Configuration:
        n_quintiles: int = 5
        weight_method: str = "equal"  # only "equal" supported in P2
    """

    def sort(
        self,
        factor_values: pd.Series,     # MultiIndex (date, ticker)
        target_date: date,
        n_quintiles: int = 5,
    ) -> QuintilePortfolio:
        """Assign stocks to quintiles for a single date."""
        ...

    def sort_timeseries(
        self,
        factor_values: pd.DataFrame,  # MultiIndex (date, ticker)
        rebalance_dates: list[date],
    ) -> dict[date, QuintilePortfolio]:
        """Assign stocks to quintiles across multiple rebalance dates."""
        ...
```

**Key Behavior**: Equal-weight quintile sorting (20% per group), consistent with guidance specification D-005. The `QuintilePortfolio` is frozen/immutable after creation.

### 2.3 MetricsCalculator (extended from existing)

The existing `compute_metrics()` function is stateless and takes numpy arrays. P2 wraps this in a stateful calculator that accumulates statistics during iteration, per guidance specification D-002.

```python
@dataclass(frozen=True)
class PerformanceMetrics:
    """Immutable snapshot of all 8 core metrics + derived metrics."""
    # Core 8
    annual_return: float
    volatility: float
    sharpe: float
    max_drawdown: float
    turnover: float
    win_rate: float
    excess_return: float
    information_ratio: float
    # Derived (P2 additions)
    calmar: float                        # annual_return / abs(max_drawdown)
    profit_loss_ratio: float             # avg_profit / avg_loss
    cumulative_return: float
    annual_turnover: float

class MetricsCalculator:
    """Stateful calculator that computes all metrics in a single pass.

    Configuration:
        risk_free_rate: float = 0.0
        annualization_factor: int = 252
        benchmark: Optional[pd.Series] = None
    """

    def __init__(
        self,
        risk_free_rate: float = 0.0,
        annualization_factor: int = 252,
        benchmark: Optional[pd.Series] = None,
    ) -> None: ...

    def compute(
        self,
        portfolio_returns: np.ndarray,
    ) -> PerformanceMetrics:
        """Compute all metrics from a return series."""
        ...

    # Backward-compatible static method
    @staticmethod
    def compute_legacy(
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray,
        risk_free_rate: float = 0.0,
    ) -> BacktestMetrics:
        """Legacy interface wrapping existing compute_metrics."""
        ...
```

**Backward Compatibility**: The existing `BacktestMetrics` dataclass and `compute_metrics()` function are preserved as `compute_legacy()` for existing test compatibility.

### 2.4 ICAnalyzer (NEW)

```python
@dataclass(frozen=True)
class ICResult:
    """Immutable IC analysis results."""
    ic_series: pd.Series                # Daily RankIC values
    ic_mean: float
    ic_std: float
    icir: float                         # IC mean / IC std
    ic_positive_ratio: float            # % of days with IC > 0
    rolling_ic: Optional[pd.Series] = None  # Rolling IC with configurable window
    ic_decay: Optional[pd.Series] = None    # IC decay at various lags

class ICAnalyzer:
    """Compute Information Coefficient between factor values and forward returns.

    Configuration:
        window: int = 20                 # Rolling IC window (trading days)
        min_periods: int = 10            # Minimum periods for rolling computation
    """

    def __init__(
        self,
        window: int = 20,
        min_periods: int = 10,
    ) -> None: ...

    def compute_ic(
        self,
        factor_values: pd.DataFrame,    # MultiIndex (date, ticker)
        forward_returns: pd.Series,     # MultiIndex (date, ticker)
    ) -> ICResult:
        """Compute RankIC, rolling IC, ICIR, and IC decay."""
        ...

    def compute_ic_by_quintile(
        self,
        factor_values: pd.DataFrame,
        forward_returns: pd.Series,
        quintile_labels: dict[date, dict[str, int]],
    ) -> pd.DataFrame:
        """Compute IC within each quintile group for validation."""
        ...
```

### 2.5 AttributionEngine (NEW)

```python
@dataclass(frozen=True)
class AttributionResult:
    """Immutable return attribution decomposition."""
    factor_exposure_return: pd.Series   # Return from factor exposure
    residual_return: pd.Series          # Unexplained return
    r_squared: float                    # Model fit quality
    factor_loadings: dict[str, float]   # Factor loading per factor_id
    period_attribution: list[dict]      # Per-period breakdown

class AttributionEngine:
    """Barra-style factor model return attribution.

    Decomposes portfolio returns into:
    - Factor exposure return (from factor betas * factor returns)
    - Residual return (unexplained alpha)
    """

    def __init__(self) -> None: ...

    def compute(
        self,
        portfolio_returns: pd.Series,
        factor_returns: pd.DataFrame,   # Factor return time series
        factor_exposures: pd.DataFrame,  # Portfolio factor loadings
    ) -> AttributionResult:
        """Decompose returns using factor model."""
        ...
```

### 2.6 CostModel (NEW, extracted)

```python
class CostModel:
    """Transaction cost calculation with configurable components.

    Current P2 implementation: fixed bps model.
    Extensible for future market impact models.
    """

    def __init__(
        self,
        transaction_cost_bps: float,
        slippage_bps: float,
    ) -> None: ...

    def compute_cost(
        self,
        old_positions: set[str],
        new_positions: set[str],
        total_stocks: int,
    ) -> float:
        """Compute transaction cost as a fraction of portfolio value.

        Cost = (turnover_ratio) * (transaction_cost_bps + slippage_bps) / 10000
        """
        ...
```

**Extraction Rationale**: The existing cost calculation is embedded in `BacktestEngine.run_backtest()`. Extracting it into a dedicated class enables:
- Unit testing cost logic independently
- Future extension to market impact models
- Configuration-driven cost parameters

## 3. Data Flow

### 3.1 End-to-End Pipeline

```
P6 FactorEngine                         P1 Market Semantics
    |                                        |
    | compute_batch()                        | TradingCalendar
    | -> pd.DataFrame                        | -> rebalance_dates
    |    (MultiIndex: date, ticker)          |
    |    (columns: factor_ids)               | ExRightAdjustment
    |                                        | -> adjusted prices
    v                                        v
+-------------------------------------------------------------------+
|                    BacktestEngine.run(request)                     |
+-------------------------------------------------------------------+
    |                                                               |
    | Step 1: Generate rebalance dates                              |
    |   rebalance_dates = TradingCalendar.trading_days_between()    |
    |   filtered by config.rebalance_frequency                     |
    |                                                               |
    | Step 2: For each rebalance date:                              |
    |   QuintileSorter.sort(factor_values, date)                   |
    |   -> QuintilePortfolio (frozen)                               |
    |                                                               |
    | Step 3: Simulate portfolio returns                            |
    |   Equal-weight long Q5, short Q1                              |
    |   CostModel.compute_cost(prev, new, n)                       |
    |   period_return = long_ret - short_ret - cost                |
    |                                                               |
    | Step 4: Compute metrics                                       |
    |   MetricsCalculator.compute(return_series)                    |
    |   -> PerformanceMetrics (frozen)                              |
    |                                                               |
    | Step 5: IC analysis (optional)                                |
    |   ICAnalyzer.compute_ic(factor_values, forward_returns)       |
    |   -> ICResult (frozen)                                        |
    |                                                               |
    | Step 6: Attribution (optional)                                |
    |   AttributionEngine.compute(portfolio_ret, factor_ret, ...)   |
    |   -> AttributionResult (frozen)                               |
    |                                                               |
    v                                                               v
+-------------------------------------------------------------------+
|                      BacktestResult (frozen)                       |
|  config, metrics, ic_result, attribution, trades, quintile_history |
+-------------------------------------------------------------------+
    |
    v
+-------------------------------------------------------------------+
|                 Persistence (Parquet)                              |
|  save_result(result, path) -> {factor}_{date}.parquet            |
+-------------------------------------------------------------------+
```

### 3.2 Data Format Specifications

**Factor Values Input** (from P6 FactorEngine):
```
DataFrame with MultiIndex: (date: datetime, ticker: str)
Columns: factor_id strings (e.g., "momentum_6m_1m", "pe_ratio")
```

This matches the existing FactorEngine.compute_batch() output format -- no transformation needed.

**Forward Returns Input**:
```
Series with MultiIndex: (date: datetime, ticker: str)
Values: float (next-period return as decimal, e.g., 0.02 for 2%)
```

**Rebalance Date Generation**:
```
TradingCalendar.trading_days_between(start, end)
  -> filtered by config.rebalance_frequency:
     "daily"   -> all trading days
     "weekly"  -> first trading day of each week
     "monthly" -> first trading day of each month
```

### 3.3 Quintile Sorting Flow (per rebalance date)

```
factor_values_on_date = factor_values.xs(target_date, level="date")
    |
    v
ranked = factor_values_on_date.rank(ascending=False)
    |
    v
n = len(ranked)
q_size = n // 5
    |
    +-- Q5 (top 20%): long_tickers
    +-- Q4: hold (no position)
    +-- Q3: hold (no position)
    +-- Q2: hold (no position)
    +-- Q1 (bottom 20%): short_tickers
    |
    v
weights = {ticker: 1/len(quintile) for ticker in quintile}
```

**Handling Edge Cases**:
- `n < 5`: Cannot form 5 quintiles; return empty portfolio (skip period)
- `n % 5 != 0`: Bottom quintile gets floor(n/5), top gets floor(n/5), middle groups get remainder
- Ties in ranking: Use `method="first"` for deterministic ordering
- Missing factor values for some tickers: Drop NaN rows before sorting

## 4. Integration Points

### 4.1 P6 FactorEngine Integration

```
BacktestEngine
    |
    | accepts: pd.DataFrame from FactorEngine.compute_batch()
    |          or FactorEngine.compute_all()
    |
    | no direct import of FactorEngine -- data format contract only
    | (decoupled by DataFrame as the interface boundary)
    |
    v
FactorEngine.compute_batch(factor_ids, tickers, target_date)
    -> pd.DataFrame (MultiIndex: date x ticker, columns: factor_ids)
```

**Integration Pattern**: **Data contract (DataFrame)**, not direct API coupling. This means:
- BacktestEngine never imports FactorEngine
- FactorEngine can be replaced with any source producing the same DataFrame format
- Testing uses synthetic DataFrames without needing FactorEngine

**P6 FactorSpec Fields Used by P2**:
- `spec.publication_lag`: Enforced during factor computation (P6 responsibility)
- `spec.category`: Used for factor grouping in attribution analysis
- `spec.inputs`: Not needed by P2 (P6 handles data requirements)

### 4.2 P1 Market Semantics Integration

```
BacktestEngine
    |
    | imports: TradingCalendar from synapse.core.market.calendar
    |          ExRightAdjustment from synapse.core.market.adjustment
    |
    v
TradingCalendar.trading_days_between(start, end)
    -> list[date]  # Used to generate rebalance dates

TradingCalendar.is_trading_day(date)
    -> bool  # Filter non-trading days from rebalance schedule

ExRightAdjustment.adjust_prices(df, factors)
    -> DataFrame  # Price-adjusted data for return calculation
```

**Integration Pattern**: **Direct import** for calendar and adjustment utilities. These are stable P1 APIs with no known versioning concerns.

**TemporalContext Usage**: The `P1 TemporalContext` (ADR-008) is used to validate that:
- Factor computation dates are before backtest execution dates
- No look-ahead bias exists in the data pipeline

### 4.3 Report Generation Integration

```
BacktestResult (frozen dataclass)
    |
    | passed to: ReportGenerator (P1)
    |
    v
ReportGenerator.generate(result: BacktestResult)
    -> Markdown / HTML report with:
       - PerformanceMetrics table
       - ICResult charts
       - AttributionResult decomposition
       - Quintile return time series
```

**Integration Pattern**: **Result object** passed to report generator. Report generator reads `BacktestResult` fields and formats output.

### 4.4 Existing Code Compatibility

The existing `BacktestEngine`, `BacktestConfig`, `BacktestMetrics`, and `compute_metrics()` are preserved with backward-compatible wrappers:

```python
# Existing code continues to work:
engine = BacktestEngine()
result = engine.run_backtest(factor_values, forward_returns, config)
# result.metrics is BacktestMetrics (existing)

# New code uses richer interface:
engine = BacktestEngine(sorter, metrics_calc, ic_analyzer, attribution)
result = engine.run(BacktestRequest(...))
# result.metrics is PerformanceMetrics (new, with 12 fields)
```

## 5. Error Handling

### 5.1 Error Hierarchy

Extends existing `SynapseError` hierarchy from `synapse/core/errors.py`:

```python
class BACKTEST_INSUFFICIENT_DATA(SynapseError):
    code = "BACKTEST_INSUFFICIENT_DATA"
    default_message = "Not enough data points for backtest"

class BACKTEST_SORT_FAILED(SynapseError):
    code = "BACKTEST_SORT_FAILED"
    default_message = "Quintile sorting failed"

class BACKTEST_IC_COMPUTATION_FAILED(SynapseError):
    code = "BACKTEST_IC_COMPUTATION_FAILED"
    default_message = "IC computation failed"

class BACKTEST_ATTRIBUTION_FAILED(SynapseError):
    code = "BACKTEST_ATTRIBUTION_FAILED"
    default_message = "Return attribution failed"

class BACKTEST_PERSISTENCE_FAILED(SynapseError):
    code = "BACKTEST_PERSISTENCE_FAILED"
    default_message = "Failed to persist backtest results"
```

### 5.2 Error Containment Strategy

Following the existing `PartialResult` pattern from P6 FactorEngine:

```python
@dataclass(frozen=True)
class PartialBacktestResult:
    """Result that may contain partial failures."""
    factor_id: str
    success: bool
    metrics: Optional[PerformanceMetrics] = None
    ic_result: Optional[ICResult] = None
    attribution: Optional[AttributionResult] = None
    errors: list[str] = field(default_factory=list)
```

**Containment Rules**:
1. **Factor computation failure**: Skip that factor, continue with others. Log warning.
2. **IC computation failure**: Set `ic_result = None` in result, continue with metrics.
3. **Attribution failure**: Set `attribution = None` in result, continue with metrics + IC.
4. **Quintile sorting failure** (e.g., < 5 stocks): Skip that rebalance period, log warning.
5. **Persistence failure**: Raise `BACKTEST_PERSISTENCE_FAILED` (data loss is not acceptable).

### 5.3 Data Validation

```python
def validate_factor_data(factor_values: pd.DataFrame) -> list[str]:
    """Validate factor data before backtest. Returns list of issues."""
    issues = []
    if factor_values.empty:
        issues.append("Factor values DataFrame is empty")
    if not isinstance(factor_values.index, pd.MultiIndex):
        issues.append("Factor values must have MultiIndex (date, ticker)")
    elif factor_values.index.names != ["date", "ticker"]:
        issues.append(f"Expected index names ['date', 'ticker'], got {factor_values.index.names}")
    # Check for excessive NaN
    nan_ratio = factor_values.isna().sum().sum() / factor_values.size
    if nan_ratio > 0.5:
        issues.append(f"Factor values have {nan_ratio:.1%} NaN (threshold: 50%)")
    return issues
```

### 5.4 Look-Ahead Bias Prevention

The backtest enforces point-in-time discipline:

1. Factor values must be computed with `publication_lag` (handled by P6 FactorEngine)
2. Forward returns use the next period's close price
3. TradingCalendar ensures rebalance dates are actual trading days
4. Validation test: For each rebalance date, verify factor data is available before or on that date

## 6. Configuration

### 6.1 BacktestConfig (extended)

```python
@dataclass
class BacktestConfig:
    """Backtest configuration. Extended from existing."""
    # Identity
    universe: str                       # e.g., "csi300", "csi500", "custom"
    benchmark: str                      # e.g., "csi300", "none"

    # Time range
    start_date: str                     # ISO format "YYYY-MM-DD"
    end_date: str

    # Portfolio construction
    rebalance_frequency: str            # "daily" | "weekly" | "monthly"
    n_quintiles: int = 5               # Number of quintile groups
    weight_method: str = "equal"        # "equal" only in P2

    # Transaction costs (REQUIRED -- no silent defaults)
    transaction_cost_bps: float
    slippage_bps: float

    # Risk management
    position_limit: float = 1.0         # Max weight per position (1.0 = no limit)

    # Analytics
    ic_window: int = 20                 # Rolling IC window (trading days)
    ic_min_periods: int = 10            # Min periods for rolling IC
    enable_attribution: bool = True     # Whether to run attribution analysis
    enable_ic_analysis: bool = True     # Whether to run IC analysis

    # Persistence
    output_dir: str = "backtests/"      # Directory for Parquet output

    def __post_init__(self) -> None:
        if self.transaction_cost_bps is None:
            raise ValueError("transaction_cost_bps must be explicitly set")
        if self.slippage_bps is None:
            raise ValueError("slippage_bps must be explicitly set")
        if self.n_quintiles < 2:
            raise ValueError("n_quintiles must be >= 2")
        if self.rebalance_frequency not in ("daily", "weekly", "monthly"):
            raise ValueError(f"Invalid rebalance_frequency: {self.rebalance_frequency}")
```

### 6.2 YAML Configuration Example

```yaml
# backtest_config.yaml
universe: csi300
benchmark: csi300
start_date: "2020-01-01"
end_date: "2025-12-31"
rebalance_frequency: monthly
n_quintiles: 5
weight_method: equal
transaction_cost_bps: 10.0
slippage_bps: 5.0
position_limit: 1.0
ic_window: 20
ic_min_periods: 10
enable_attribution: true
enable_ic_analysis: true
output_dir: "backtests/csi300_momentum/"
```

### 6.3 Configuration Validation

Configuration is validated at construction time via `__post_init__`. The `BACKTEST_CONFIG_INVALID` error class from `synapse/core/errors.py` is reused.

## 7. Performance Considerations

### 7.1 Vectorized Operations

The existing `BacktestEngine` uses a Python loop over rebalance periods. P2 optimizes this:

**Current (P1)**:
```python
for period in dates.unique():    # Python loop -- slow for large datasets
    period_data = aligned.iloc[mask]
    ...
```

**P2 Optimization**:
```python
# Pre-compute all rankings vectorized
ranked = factor_values.groupby(level="date").rank(ascending=False)

# Vectorized quintile assignment
quintile_labels = ranked.groupby(level="date").transform(
    lambda x: pd.qcut(x, q=n_quintiles, labels=range(1, n_quintiles + 1))
)

# Vectorized return computation per quintile
quintile_returns = forward_returns.groupby(level="date").apply(
    lambda g: g.groupby(quintile_labels.loc[g.index]).mean()
)
```

**Expected Speedup**: 5-10x for typical datasets (300 stocks, 5 years, monthly rebalance = ~60 periods).

### 7.2 Memory Efficiency

For large backtests (1000+ stocks, 10+ years):

1. **Chunked processing**: Process rebalance dates in chunks of 50, accumulating results
2. **Sparse storage**: Only store non-zero quintile labels
3. **Parquet columnar storage**: Results stored in Parquet for efficient column queries
4. **Float32 for factor values**: Factor values typically don't need float64 precision

### 7.3 Parallelization Strategy

```python
# Optional parallel processing for large universes
from concurrent.futures import ProcessPoolExecutor

def run_parallel(
    self,
    request: BacktestRequest,
    max_workers: int = 4,
) -> BacktestResult:
    """Parallel backtest by splitting rebalance dates."""
    # Split rebalance_dates into chunks
    # Process each chunk in separate process
    # Merge results
    ...
```

**When to use parallel**: > 500 stocks AND > 3 years of daily data. For typical CSI 300 backtests, vectorized single-process is sufficient.

### 7.4 Benchmark Performance Targets

| Dataset Size | Target Time | Memory |
|---|---|---|
| 300 stocks, 2 years, monthly | < 1s | < 100 MB |
| 300 stocks, 5 years, monthly | < 3s | < 200 MB |
| 1000 stocks, 5 years, daily | < 30s | < 1 GB |
| 3000 stocks, 10 years, daily | < 120s | < 4 GB |

### 7.5 Caching Strategy

```python
# Factor values can be cached across multiple backtests
class FactorValueCache:
    """Cache computed factor values to avoid redundant computation."""

    def __init__(self, cache_dir: str = "data/cache/") -> None: ...

    def get(self, factor_id: str, tickers: list[str], dates: list[date]) -> Optional[pd.DataFrame]: ...
    def put(self, factor_id: str, tickers: list[str], dates: list[date], values: pd.DataFrame) -> None: ...
    def invalidate(self, factor_id: str) -> None: ...
```

Cache is keyed by (factor_id, sorted_tickers_hash, date_range). Invalidation occurs when FactorSpec version bumps (`spec.next_version()`).

## 8. Testing Strategy

### 8.1 Unit Test Structure

```
tests/unit/
    test_backtest_engine.py      # Existing -- extend with new interface
    test_backtest_metrics.py     # Existing -- extend with PerformanceMetrics
    test_quintile_sorter.py      # NEW
    test_ic_analyzer.py          # NEW
    test_attribution_engine.py   # NEW
    test_cost_model.py           # NEW
    test_backtest_result.py      # NEW
    test_backtest_config.py      # Existing -- extend with new fields
```

### 8.2 Integration Test Structure

```
tests/integration/
    test_backtest_pipeline.py    # NEW: End-to-end with mock FactorEngine
    test_p6_integration.py       # NEW: Backtest + FactorEngine integration
    test_p1_calendar_integration.py  # NEW: Backtest + TradingCalendar
```

### 8.3 Key Test Scenarios

1. **Deterministic sorting**: Same input -> same quintile assignments
2. **Transaction cost accuracy**: Verify cost deduction matches expected formula
3. **IC computation correctness**: RankIC matches scipy.stats.spearmanr
4. **Metrics edge cases**: Empty returns, single period, all positive, all negative
5. **Attribution decomposition**: Factor return + residual = total return (within tolerance)
6. **PIT validation**: No look-ahead bias in factor values
7. **Large dataset performance**: 300 stocks, 5 years completes within target time

## 9. Risk Analysis

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Factor data missing for many tickers | Incomplete quintiles | High | Forward-fill with limit, skip tickers with insufficient data |
| Look-ahead bias in factor computation | Invalid results | Medium | PIT validation enforced by P6 FactorEngine |
| Slow performance on large datasets | Poor UX | Medium | Vectorized operations, optional parallelism |
| Quintile sorting ties | Non-deterministic results | Low | `method="first"` for deterministic ranking |
| Parquet storage version incompatibility | Data corruption | Low | Schema versioning in Parquet metadata |

## 10. Implementation Priority

Based on feature dependencies (guidance specification feature decomposition):

| Phase | Feature | Depends On | Effort |
|---|---|---|---|
| 1 | F-029: Quintile Portfolio Sorting | -- | Small |
| 2 | F-030: Backtest Engine Core | F-029 | Medium |
| 3 | F-035: Long-Short Spread | F-029, F-030 | Small |
| 4 | F-031: Performance Metrics | F-030 | Small |
| 5 | F-032: Factor IC Analysis | -- | Medium |
| 6 | F-033: Return Attribution | F-030 | Medium |
| 7 | F-034: Backtest Result Persistence | F-030, F-031 | Small |
| 8 | F-036: Integration Tests | All above | Medium |

**Total Estimated Effort**: ~15-20 implementation tasks across 8 features.
