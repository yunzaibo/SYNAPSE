# P2 Long-Short Quintile Backtest Engine -- Data Architect Analysis

**Role**: Data Architect
**Date**: 2026-05-19
**Status**: Draft
**References**: guidance-specification.md, synapse/core/schemas/, synapse/factor/, synapse/backtest/, synapse/data/, synapse/core/temporal.py

---

## 1. Data Models

### 1.1 Existing State (P1/P6)

The codebase already provides these data structures that P2 must integrate with:

| Module | Class | Pattern | Key Fields |
|--------|-------|---------|------------|
| `core/schemas/base.py` | `BaseSchema` | dataclass | id, schema_version, status, created_at, updated_at, source_type, created_by, market_context |
| `core/schemas/base.py` | `MarketContext` | dataclass | research_date, market_date, trading_session |
| `core/temporal.py` | `TemporalContext` | dataclass | event_time, market_date, event_timezone, market_session, available_at, as_of_date |
| `factor/engine.py` | `FactorEngine` | class | compute_factor -> Series, compute_batch -> DataFrame, compute_all -> DataFrame |
| `factor/audit.py` | `FactorAuditReport` | dataclass | ic_mean, ic_std, icir, rank_ic_mean, turnover, decay_half_life, coverage, rating |
| `factor/portfolio.py` | `FactorPortfolio` | dataclass | name, weights, method, expected_ic, expected_risk, rebalance_freq |
| `backtest/engine.py` | `BacktestResult` | dataclass | config, metrics, portfolio_returns, trades, status |
| `backtest/metrics.py` | `BacktestMetrics` | dataclass | annual_return, volatility, sharpe, max_drawdown, turnover, win_rate, excess_return, information_ratio |

**Critical observation**: The existing `BacktestResult` does NOT inherit `BaseSchema`, is NOT frozen, and lacks temporal/schema-version support. This is the primary gap P2 must address.

### 1.2 Proposed New Models

#### 1.2.1 QuintilePortfolio

Represents a single quintile group's portfolio at a point in time.

```python
@dataclass(frozen=True, slots=True)
class QuintilePortfolio:
    """One of the 5 equal-weight portfolios from quintile sorting."""

    quintile_id: int          # 1 (bottom) through 5 (top)
    tickers: tuple[str, ...]  # stocks in this quintile, sorted by weight
    weights: dict[str, float] # ticker -> weight (equal-weight: 1/len(tickers))
    factor_id: str            # which factor was used for sorting
    sort_date: date           # the date when sorting was performed
    total_value: float = 1.0  # notional portfolio value (normalized)

    def __post_init__(self) -> None:
        if not 1 <= self.quintile_id <= 5:
            raise ValueError(f"quintile_id must be 1-5, got {self.quintile_id}")
        if not self.tickers:
            raise ValueError("tickers must not be empty")

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> QuintilePortfolio: ...
```

**Design rationale**: Frozen dataclass matches P1 `AdjustmentEvent` / `AdjustmentFactors` pattern. The `tuple[str, ...]` for tickers ensures immutability. The `to_dict()` / `from_dict()` pattern follows all existing schema serialization conventions.

**Gap vs existing code**: The current `BacktestEngine` uses `set` for long/short stocks and computes returns inline. P2 replaces this with structured `QuintilePortfolio` objects that capture the full 5-quintile decomposition, not just top/bottom.

#### 1.2.2 BacktestResult (enhanced)

The existing `BacktestResult` is a plain mutable dataclass. P2 must upgrade it to follow BaseSchema patterns while preserving backward compatibility.

```python
@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Immutable result of a complete backtest run."""

    # --- Identity ---
    id: str
    schema_version: str = "2.0"

    # --- Configuration ---
    config: BacktestConfig = field(default_factory=BacktestConfig)

    # --- Temporal ---
    run_timestamp: datetime = field(default_factory=lambda: datetime.now(CST))
    start_date: date = field(default_factory=date.today)
    end_date: date = field(default_factory=date.today)

    # --- Factor provenance ---
    factor_id: str = ""
    factor_source: str = ""         # e.g. "FactorEngine:momentum_6m_1m"

    # --- Portfolio snapshots ---
    quintile_portfolios: tuple[QuintilePortfolio, ...] = ()

    # --- Return series ---
    quintile_returns: dict[int, tuple[float, ...]] = field(default_factory=dict)
    long_short_returns: tuple[float, ...] = ()
    benchmark_returns: tuple[float, ...] = ()

    # --- Metrics ---
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    ic_analysis: ICAnalysisResult | None = None
    attribution: AttributionResult | None = None

    # --- Status ---
    status: str = "running"  # running | succeeded | failed
    error: str | None = None

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> BacktestResult: ...
```

**Design rationale**:
- Frozen + slots: thread-safe, memory-efficient, consistent with P1 AdjustmentEvent
- `schema_version = "2.0"`: signals this is the P2 evolution; enables Weak Schema + Lazy Upcast
- `factor_source`: traceability back to which FactorEngine factor_id produced this result
- `quintile_returns` keyed by quintile_id (1-5): enables per-quintile analysis
- `ic_analysis` and `attribution` are optional: allows partial results if those sub-analyses fail

#### 1.2.3 PerformanceMetrics (expanded)

The existing `BacktestMetrics` has 8 fields. P2 extends it with additional metrics required by the guidance specification.

```python
@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    """Comprehensive performance metrics computed in a single pass."""

    # --- Core 8 (from existing BacktestMetrics) ---
    annual_return: float = 0.0
    volatility: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    turnover: float = 0.0
    win_rate: float = 0.0
    excess_return: float = 0.0
    information_ratio: float = 0.0

    # --- Extended metrics (P2) ---
    calmar: float = 0.0              # annual_return / |max_drawdown|
    profit_loss_ratio: float = 0.0   # avg profit / avg loss
    long_short_spread: float = 0.0   # cumulative L/S return
    max_drawdown_duration: int = 0   # trading days from peak to recovery
    skewness: float = 0.0            # return distribution skew
    kurtosis: float = 0.0            # return distribution kurtosis

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> PerformanceMetrics: ...
```

**Design rationale**: The guidance spec mandates 8 core metrics plus additional diagnostics. `calmar` and `profit_loss_ratio` are explicitly called out. `skewness`/`kurtosis` and `max_drawdown_duration` are standard in factor research but currently missing. All fields have defaults for backward compatibility with existing `compute_metrics()`.

#### 1.2.4 ICAnalysisResult

New model to capture factor IC analysis integrated from P6's `factor.audit` module.

```python
@dataclass(frozen=True, slots=True)
class ICAnalysisResult:
    """IC/RankIC analysis results for the backtest period."""

    factor_id: str
    ic_series: tuple[float, ...]          # daily IC values
    rank_ic_series: tuple[float, ...]     # daily RankIC values
    ic_mean: float = 0.0
    ic_std: float = 0.0
    icir: float = 0.0
    rank_ic_mean: float = 0.0
    rank_ic_std: float = 0.0
    rank_icir: float = 0.0
    rolling_ic: tuple[float, ...] = ()    # rolling-window IC (configurable window)
    ic_positive_ratio: float = 0.0        # % of periods with positive IC

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> ICAnalysisResult: ...
```

**Gap vs existing code**: P6's `FactorAuditReport` is a snapshot (ic_mean, ic_std, icir). P2's `ICAnalysisResult` stores the full IC time series, enabling downstream analysis like IC regime detection and rolling IC visualization.

#### 1.2.5 AttributionResult

New model for Barra-style return attribution (F-033).

```python
@dataclass(frozen=True, slots=True)
class AttributionResult:
    """Decomposition of portfolio returns into factor and residual components."""

    factor_returns: dict[str, float]    # factor_id -> contribution
    residual_returns: tuple[float, ...] # idiosyncratic residual per period
    total_factor_return: float = 0.0    # sum of factor contributions
    residual_return: float = 0.0        # total residual
    r_squared: float = 0.0             # goodness of fit

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> AttributionResult: ...
```

**Design rationale**: Barra-style decomposition separates systematic (factor) from idiosyncratic (residual) returns. `factor_returns` is a dict to support multi-factor attribution. `r_squared` indicates how well the factor model explains return variance.

### 1.3 Model Hierarchy

```
BacktestResult (frozen, schema_version="2.0")
  |-- config: BacktestConfig (existing, mutable OK)
  |-- performance: PerformanceMetrics (frozen)
  |-- quintile_portfolios: tuple[QuintilePortfolio, ...] (frozen)
  |-- ic_analysis: ICAnalysisResult | None (frozen)
  |-- attribution: AttributionResult | None (frozen)
```

All new models use `frozen=True, slots=True` to match the P1 convention established by `AdjustmentEvent` and `AdjustmentFactors`. The `to_dict()` / `from_dict()` pattern is universal across all 9 existing schema objects and must be preserved.

---

## 2. Storage Strategy

### 2.1 Storage Layer Architecture

```
┌─────────────────────────────────────────────────┐
│                   BacktestResult                  │
│  (frozen dataclass, in-memory)                   │
└──────────────┬──────────────────┬────────────────┘
               │                  │
    ┌──────────▼──────────┐  ┌───▼────────────────┐
    │  Parquet (durable)   │  │  DataFrame (temp)  │
    │  results/            │  │  intermediate       │
    │  {factor}_{date}.pq  │  │  calculations       │
    └─────────────────────┘  └────────────────────┘
```

### 2.2 Parquet Storage (Durable Results)

Following the P1 pattern from `adjustment.py` where `{symbol}.parquet` is the canonical storage format.

**Directory structure**:
```
data/backtest/
  results/
    {factor_id}/
      {run_id}.parquet          # BacktestResult metrics summary
  quintile_returns/
    {factor_id}/
      {run_id}.parquet          # Per-quintile daily returns
  ic_analysis/
    {factor_id}/
      {run_id}.parquet          # IC/RankIC time series
  attribution/
    {factor_id}/
      {run_id}.parquet          # Factor attribution decompositions
```

**Parquet schema for results summary** (`{run_id}.parquet`):

| Column | Parquet Type | Description |
|--------|-------------|-------------|
| run_id | string | Unique backtest run identifier |
| factor_id | string | Factor used for sorting |
| start_date | date | Backtest start |
| end_date | date | Backtest end |
| rebalance_freq | string | daily / weekly / monthly |
| transaction_cost_bps | float | Cost parameter |
| slippage_bps | float | Slippage parameter |
| annual_return | float | Annualized return |
| volatility | float | Annualized volatility |
| sharpe | float | Sharpe ratio |
| max_drawdown | float | Max drawdown |
| turnover | float | Average turnover |
| win_rate | float | Win rate |
| excess_return | float | Excess return over benchmark |
| information_ratio | float | Information ratio |
| calmar | float | Calmar ratio |
| profit_loss_ratio | float | Profit/loss ratio |
| run_timestamp | timestamp | When the run was executed |

**Parquet schema for quintile returns** (`{run_id}.parquet` in quintile_returns/):

| Column | Parquet Type | Description |
|--------|-------------|-------------|
| date | date | Trading date |
| quintile_id | int32 | 1-5 |
| return | float64 | Quintile portfolio return |
| cumulative_return | float64 | Cumulative return since start |
| long_short_spread | float64 | Q5 - Q1 spread |

**Parquet schema for IC analysis** (`{run_id}.parquet` in ic_analysis/):

| Column | Parquet Type | Description |
|--------|-------------|-------------|
| date | date | Trading date |
| factor_id | string | Factor identifier |
| ic | float64 | Pearson IC |
| rank_ic | float64 | Spearman RankIC |
| rolling_ic | float64 | Rolling-window IC |
| forward_return | float64 | Forward return used for IC |

### 2.3 DataFrame Storage (Intermediate Calculations)

Intermediate data lives in-memory as DataFrames during computation. This follows the P6 FactorEngine pattern where `compute_batch()` returns a DataFrame.

**Key intermediate DataFrames**:

| Name | Index | Columns | Created By |
|------|-------|---------|------------|
| factor_matrix | MultiIndex(date, ticker) | factor_id | FactorEngine.compute_batch() |
| return_matrix | MultiIndex(date, ticker) | "return" | Price data + forward returns |
| quintile_assignments | MultiIndex(date, ticker) | "quintile_id" | Quintile sorter |
| portfolio_returns | date index | quintile_1..quintile_5, L/S spread | Portfolio return calculator |

**Lifecycle**: Intermediate DataFrames are created at the start of `BacktestEngine.run()`, transformed through the pipeline, and consumed by metric/attribution computation. They are NOT persisted -- only the final `BacktestResult` (via Parquet) and `ICAnalysisResult` are durable.

### 2.4 Serialization Compatibility

The existing `adjustment.py` establishes two serialization patterns:

1. **Parquet for bulk data**: `pd.read_parquet()` / `df.to_parquet()` -- used for adjustment factors, OHLCV prices
2. **YAML for metadata**: `DatasetMetadata.to_yaml()` / `from_yaml()` -- used for dataset provenance

P2 extends this:
- **Parquet** for return series, IC series, metrics (columnar, queryable)
- **JSON** for `BacktestResult.to_dict()` (human-readable, YAML-compatible) -- follows BaseSchema pattern
- **No YAML for results**: Backtest results are analytical data, not configuration metadata

---

## 3. Data Flow

### 3.1 End-to-End Pipeline

```
FactorEngine                    BacktestEngine                    Storage
============                    =============                     =======

[compute_batch]                 [run]
    |                               |
    v                               v
factor_matrix               quintile_sorter
DataFrame(date,ticker)       -> DataFrame(date,ticker)
columns=factor_ids           column=quintile_id
    |                               |
    v                               v
FactorSpec.publication_lag   portfolio_builder
    |                          -> dict[int, QuintilePortfolio]
    v                               |
PIT filter (as_of_date)      return_calculator
    |                          -> dict[int, tuple[float,...]]
    v                               |
factor_values                metric_calculator
pd.Series(ticker)            -> PerformanceMetrics
    |                          ic_analyzer
    v                          -> ICAnalysisResult
Forward returns                attribution_engine
pd.Series(ticker)            -> AttributionResult
                                 |
                                 v
                          BacktestResult (frozen)
                                 |
                                 v
                          Parquet persistence
```

### 3.2 Detailed Step-by-Step Flow

**Step 1: Factor Value Input**

FactorEngine produces a DataFrame with MultiIndex (date, ticker) and factor_id columns. This is the output of `FactorEngine.compute_batch()` or `compute_all()`.

```
Input: pd.DataFrame
  Index: MultiIndex(date=Timestamp, ticker=str)
  Columns: [factor_id_1, factor_id_2, ...]
```

The backtest engine accepts a single factor_id's column from this DataFrame, or a combined factor score. This matches the guidance spec requirement: "accept factor values as DataFrame with MultiIndex (date, ticker)".

**Step 2: Forward Return Computation**

For each (date, ticker) pair, compute the forward return:

```python
# For monthly rebalance: 1-month forward return
# For weekly: 1-week forward return
# For daily: next-day return
forward_returns = prices.groupby('ticker')['adj_close'].pct_change(lookahead)
```

Forward returns must be aligned with the factor_matrix on the same MultiIndex. Returns on non-trading days are excluded using `TradingCalendar.trading_days_between()`.

**Step 3: Quintile Sorting**

On each rebalance date:
1. Extract factor values for all tickers at that date
2. Rank tickers by factor value (ascending)
3. Split into 5 equal groups (20% each)
4. Assign quintile_id 1 (bottom) to 5 (top)
5. For ties: use average rank, distribute to lower quintile first

```python
# Pseudocode for quintile assignment
ranks = factor_values.rank(method='average')
quintile_id = pd.qcut(ranks, q=5, labels=[1, 2, 3, 4, 5])
```

**Step 4: Portfolio Construction**

For each quintile:
1. Build `QuintilePortfolio` with equal weights (1/num_tickers)
2. Apply position_limit from BacktestConfig
3. Filter out tickers with insufficient data (< lookback_days of history)

Long-short spread = Quintile 5 return - Quintile 1 return.

**Step 5: Return Computation**

For each period between rebalance dates:
1. Compute period return for each quintile (equal-weight average)
2. Apply transaction costs only on rebalance dates
3. Compute L/S spread = Q5 return - Q1 return

Cost model (simplified, per guidance spec):
```python
turnover_cost = (new_positions / total_positions) * (transaction_cost_bps + slippage_bps) / 10000
```

**Step 6: Metrics Computation**

Single-pass computation through the return series (guidance spec MUST):
1. Annualized return: `(1 + total_return)^(252/n) - 1`
2. Volatility: `std(returns) * sqrt(252)`
3. Sharpe: `mean(excess) / std(excess) * sqrt(252)`
4. Max drawdown: peak-to-trough of cumulative returns
5. Win rate: `count(returns > 0) / total`
6. Profit/loss ratio: `mean(returns[returns > 0]) / |mean(returns[returns < 0])|`
7. Calmar: `annual_return / |max_drawdown|`
8. Information ratio: `excess_return / tracking_error`

**Step 7: IC Analysis**

Reuses P6's `compute_ic()`, `compute_rank_ic()`, `compute_rolling_ic()` from `factor.audit`:
1. For each (date, ticker): compute Pearson IC and RankIC
2. Compute rolling IC with configurable window (default: 20 days per guidance spec)
3. Aggregate: IC mean, IC std, ICIR, RankIC mean/std/ICIR
4. IC positive ratio: % of periods where IC > 0

**Step 8: Attribution Analysis**

Barra-style decomposition:
1. Regress portfolio returns on factor returns
2. Factor return contribution = beta * factor_return
3. Residual = portfolio_return - factor_contribution
4. R-squared = variance(factor_contribution) / variance(total_return)

**Step 9: Result Assembly**

Assemble frozen `BacktestResult` with all components, then persist to Parquet.

### 3.3 Data Type Contracts

| Interface | Input Type | Output Type | Source Module |
|-----------|-----------|-------------|---------------|
| FactorEngine.compute_batch | list[str], list[str], date | DataFrame(MultiIndex, factor_cols) | factor/engine.py |
| BacktestEngine.run | DataFrame, BacktestConfig | BacktestResult | backtest/engine.py |
| compute_metrics | ndarray, ndarray | PerformanceMetrics | backtest/metrics.py (enhanced) |
| compute_rolling_ic | DataFrame(factor, forward_return), int | Series | factor/audit.py |
| TradingCalendar | date, date | list[date] | core/market/calendar.py |

---

## 4. Schema Compatibility with P1/P6

### 4.1 Direct Integration Points

**P6 FactorEngine -> P2 BacktestEngine**:

The `FactorEngine.compute_batch()` returns a DataFrame with MultiIndex (date, ticker) and factor_id columns. P2 consumes this directly:

```python
# P6 produces:
factor_matrix = factor_engine.compute_batch(
    factor_ids=["momentum_6m_1m"],
    tickers=["000001.SZ", "600000.SH", ...],
    target_date=date(2024, 12, 31)
)
# Result: DataFrame with index=(date, ticker), columns=["momentum_6m_1m"]

# P2 consumes:
backtest_engine.run(
    factor_matrix=factor_matrix,
    factor_id="momentum_6m_1m",
    config=BacktestConfig(...)
)
```

No transformation needed -- the DataFrame format is directly consumable.

**P1 TradingCalendar -> P2 Rebalancing**:

P2 uses `TradingCalendar.trading_days_between(start, end)` to determine rebalance dates:

```python
from synapse.core.market.calendar import TradingCalendar

calendar = TradingCalendar()
all_trading_days = calendar.trading_days_between(config.start_date, config.end_date)

# Monthly rebalance: pick first trading day of each month
rebalance_dates = [d for d in all_trading_days if d.month != prev_month]
```

**P1 Adjustment -> P2 Price Data**:

P2 uses `adjust_prices()` from `core/market/adjustment.py` for forward-adjusted prices when computing returns:

```python
from synapse.core.market.adjustment import adjust_prices, AdjustmentType

adj_df = adjust_prices(raw_prices, factors, AdjustmentType.FORWARD)
# Returns DataFrame with adj_open, adj_high, adj_low, adj_close columns
```

**P1 TemporalContext -> P2 Result Provenance**:

P2 attaches temporal context to results via the `run_timestamp` and `start_date`/`end_date` fields. The full `TemporalContext` is not embedded in `BacktestResult` (it's overkill for batch results), but `as_of_date` semantics are preserved through the PIT filtering in the data flow.

### 4.2 Schema Evolution Strategy

Following the Weak Schema + Lazy Upcast pattern (ADR-005, established in P1):

1. **Write**: Always write the latest schema version (`schema_version = "2.0"`)
2. **Read**: Accept schema_version 1.0 (existing BacktestMetrics) and 2.0 (new BacktestResult)
3. **No migration script**: Old results can be read; new results have additional fields with sensible defaults

Backward compatibility:
- Existing `BacktestMetrics` (8 fields) -> `PerformanceMetrics` (14 fields): old fields map 1:1, new fields default to 0.0
- Existing `BacktestResult` (4 fields) -> new `BacktestResult` (15+ fields): old fields map 1:1, new fields default to empty/None

### 4.3 Enum Compatibility

P2 reuses P1 enums where applicable:

| P1 Enum | P2 Usage | Module |
|---------|----------|--------|
| `ObjectStatus` | BacktestResult.status values (active/inactive/archived) | core/schemas/base.py |
| `MarketSession` | TradingCalendar integration | core/temporal.py |
| `AdjustmentType` | Price adjustment for return computation | core/market/adjustment.py |

P2 introduces new enums:

```python
class RebalanceFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class BacktestStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

class AttributionMethod(str, Enum):
    BARRA = "barra"
    SIMPLE = "simple"
```

---

## 5. Data Validation Rules

### 5.1 Input Validation

| Rule | Field | Constraint | Error |
|------|-------|-----------|-------|
| V-001 | factor_matrix | Non-empty DataFrame | "factor_matrix is empty" |
| V-002 | factor_matrix.index | Must be MultiIndex(date, ticker) | "factor_matrix must have MultiIndex(date, ticker)" |
| V-003 | factor_matrix[factor_id] | Column must exist | "factor_id '{fid}' not in factor_matrix columns" |
| V-004 | config.start_date | <= config.end_date | "start_date must be before end_date" |
| V-005 | config.transaction_cost_bps | >= 0 | "transaction_cost_bps must be non-negative" |
| V-006 | config.slippage_bps | >= 0 | "slippage_bps must be non-negative" |
| V-007 | config.rebalance_frequency | In {daily, weekly, monthly} | "invalid rebalance_frequency" |
| V-008 | tickers | >= 5 tickers for meaningful quintiles | "need at least 5 tickers for quintile sorting" |

### 5.2 Computation Validation

| Rule | Context | Constraint | Action |
|------|---------|-----------|--------|
| V-009 | Quintile sorting | Each quintile has >= 1 ticker | Skip period, log warning |
| V-010 | Quintile sorting | factor values all NaN | Skip period, log warning |
| V-011 | Return computation | Dividing by zero in weight normalization | Clamp to 1/n |
| V-012 | Sharpe ratio | std < 1e-10 | Return 0.0 (avoid division by zero) |
| V-013 | Max drawdown | cumulative == 0 | Return 0.0 |
| V-014 | IC computation | Aligned pairs < 2 | Return IC = 0.0 |
| V-015 | Attribution | R-squared < 0 | Clamp to 0.0 (model explains nothing) |

### 5.3 Output Validation

| Rule | Field | Constraint | Action |
|------|-------|-----------|--------|
| V-016 | PerformanceMetrics.annual_return | In [-1.0, inf) | Log warning if < -1.0 |
| V-017 | PerformanceMetrics.sharpe | In (-inf, inf) | Check for NaN, replace with 0.0 |
| V-018 | PerformanceMetrics.max_drawdown | In [-1.0, 0.0] | Clamp if out of range |
| V-019 | ICAnalysisResult.ic_mean | In [-1.0, 1.0] | Log warning if out of range |
| V-020 | BacktestResult.status | Must be succeeded or failed | Never "running" in persisted result |

### 5.4 Validation Pattern

Following the `data/validator.py` pattern (list of error strings):

```python
def validate_backtest_result(result: BacktestResult) -> list[str]:
    """Validate a backtest result. Returns empty list if valid."""
    errors = []

    if not result.id:
        errors.append("result id must not be empty")

    if result.start_date > result.end_date:
        errors.append("start_date must be before end_date")

    if not result.quintile_returns:
        errors.append("quintile_returns must not be empty")

    # ... additional checks
    return errors
```

---

## 6. Temporal Data Handling (PIT Support)

### 6.1 Point-in-Time Semantics

The guidance spec requires PIT validation to prevent look-ahead bias. This is already supported in P6 via `FactorEngine._filter_point_in_time()` with `publication_lag`. P2 extends this to the full backtest pipeline.

**Temporal dimensions** (following ADR-008):

| Dimension | Field | Purpose |
|-----------|-------|---------|
| Event time | factor computation date | When factor values were computed |
| Market effective time | trade execution date | When trades would have been executed |
| Data availability | available_at | When data became available (publication lag) |
| As-of cutoff | as_of_date | Maximum date for data inclusion |

### 6.2 PIT Enforcement in Backtest Pipeline

```
Rebalance date: 2024-01-31

FactorEngine._filter_point_in_time(df, target_date=2024-01-31, publication_lag=7)
  -> Cutoff: 2024-01-24
  -> Only data from <= 2024-01-24 is used for factor computation
  -> No future data leakage

Forward returns: computed from 2024-01-31 to 2024-02-28
  -> Returns use post-rebalance prices (correct)

Quintile sorting: based on factor values computed at 2024-01-31
  -> Uses only information available at or before 2024-01-24 (after lag)
  -> Correctly avoids look-ahead bias
```

### 6.3 Rebalancing Date Resolution

P2 uses `TradingCalendar` to resolve rebalance dates, ensuring no rebalance falls on a non-trading day:

```python
def resolve_rebalance_dates(
    start: date, end: date, freq: RebalanceFrequency, calendar: TradingCalendar
) -> list[date]:
    """Resolve logical rebalance dates to actual trading days."""
    trading_days = calendar.trading_days_between(start, end)

    if freq == RebalanceFrequency.DAILY:
        return trading_days
    elif freq == RebalanceFrequency.WEEKLY:
        # First trading day of each week
        return _first_of_week(trading_days)
    elif freq == RebalanceFrequency.MONTHLY:
        # First trading day of each month
        return _first_of_month(trading_days)
```

### 6.4 Handling Stale/Missing Data

Following P6's pattern where `PartialResult` captures computation failures:

| Scenario | Detection | Handling |
|----------|-----------|----------|
| Ticker missing from factor_matrix | ticker not in DataFrame.index | Exclude from quintile, log warning |
| Factor value is NaN | `pd.isna(factor_value)` | Exclude from quintile, log warning |
| Forward return is NaN | `pd.isna(forward_return)` | Exclude from return computation |
| All tickers in a quintile are NaN | Empty quintile after filtering | Skip period, mark as failed |
| Calendar has no trading days in range | Empty trading_days list | Return empty BacktestResult |

### 6.5 Temporal Context in Results

The `BacktestResult` captures temporal provenance:

```python
@dataclass(frozen=True)
class BacktestResult:
    # ...
    run_timestamp: datetime   # when the backtest was executed (processing time)
    start_date: date          # backtest period start (market effective time)
    end_date: date            # backtest period end (market effective time)
    # ...
```

This mirrors the three temporal dimensions from ADR-008:
- `run_timestamp` = processing time (when the system computed the result)
- `start_date` / `end_date` = market effective time (the period being analyzed)
- `as_of_date` (implicit in factor computation) = data availability time

---

## Appendix A: File Layout for P2 Implementation

```
synapse/backtest/
  __init__.py          # exports: BacktestEngine, BacktestResult, PerformanceMetrics, ...
  config.py            # existing, enhanced with validate
  engine.py            # existing, rewritten with quintile support
  metrics.py           # existing, enhanced with extended metrics
  quintile.py          # NEW: QuintilePortfolio, quintile sorter
  ic_analysis.py       # NEW: ICAnalysisResult, wraps P6 audit functions
  attribution.py       # NEW: AttributionResult, Barra decomposition
  persistence.py       # NEW: Parquet read/write for BacktestResult
  validation.py        # NEW: validate_backtest_result()

synapse/data/
  loader.py            # existing, no changes needed
  metadata.py          # existing, no changes needed
  validator.py         # existing, no changes needed
```

## Appendix B: Key Design Decisions Summary

| Decision | Choice | Rationale | Guided By |
|----------|--------|-----------|-----------|
| Dataclass type | frozen=True, slots=True | Thread safety, memory efficiency, consistency with P1 AdjustmentEvent | guidance-spec D-004 |
| Storage format | Parquet for results, DataFrame for intermediate | Columnar queries, consistent with P1 market data | guidance-spec D-004 |
| Factor input format | DataFrame MultiIndex(date, ticker) | Direct from FactorEngine.compute_batch(), no transformation | guidance-spec D-005 |
| IC integration | Wrap P6 compute_ic/rank_ic/rolling_ic | Code reuse, consistent IC computation across modules | guidance-spec cross-role |
| Schema versioning | "2.0" with Lazy Upcast | Backward compat with existing BacktestMetrics | ADR-005, P1 pattern |
| Validation pattern | list[str] error messages | Matches data/validator.py pattern | P1 data layer convention |
| Temporal handling | As_of_date + publication_lag | Follows FactorEngine._filter_point_in_time() | ADR-008, P6 PIT |
