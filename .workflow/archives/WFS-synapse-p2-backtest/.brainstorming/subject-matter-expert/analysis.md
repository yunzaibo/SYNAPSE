# P2 Long-Short Quintile Backtest Engine -- Subject Matter Expert Analysis

**Metadata**: 2026-05-19T23:45:00+08:00, subject-matter-expert, quantitative-backtest

---

## 1. Methodology -- Quintile Portfolio Sorting

### 1.1 Equal-Weight Quintile Sorting

The quintile sorting algorithm divides the cross-sectional stock universe into 5 equal groups ranked by a single factor value. This is the standard academic methodology (Fama-French, Barra) for evaluating factor predictive power.

**Algorithm (per rebalancing date t)**:

```
1. Collect factor values f(i, t) for all eligible stocks i in universe U_t
2. Remove stocks with NaN factor values or missing forward returns
3. Rank remaining stocks by f(i, t) in ascending order
4. Assign quintile labels: Q1 (bottom 20%) ... Q5 (top 20%)
5. Within each quintile, assign equal weights: w(i) = 1 / |Q_k|
```

**Equal-weight rationale**: Within each quintile, every stock receives weight `1/N_k` where `N_k` is the number of stocks in quintile k. This avoids introducing secondary factor biases (e.g., market-cap weighting would混入 size factor exposure). Equal-weight is the canonical approach in academic factor research.

**Edge cases**:
- When `|U_t|` is not divisible by 5, the middle quintile (Q3) absorbs the remainder. For example, 101 stocks yields quintiles of size [20, 20, 21, 20, 20].
- Stocks with identical factor values at quintile boundaries are assigned to the lower quintile (conservative approach).

### 1.2 Long-Short Spread Construction

The long-short (L/S) portfolio is constructed as:

```
R_LS(t) = R_Q5(t) - R_Q1(t)
```

Where:
- `R_Q5(t)` = return of the top quintile (long leg) at period t
- `R_Q1(t)` = return of the bottom quintile (short leg) at period t

**Interpretation**: A positive L/S spread indicates the factor has monotonic predictive power -- high factor values predict high returns. The L/S spread isolates the factor's alpha from market beta.

**Cumulative return**:

```
CUM_LS(T) = Product_{t=1}^{T} (1 + R_LS(t)) - 1
```

### 1.3 Rebalancing Protocol

The system supports three rebalancing frequencies, all anchored to the `TradingCalendar` from P1:

| Frequency | Rebalance Dates | Typical Use Case |
|-----------|----------------|------------------|
| Daily | Every trading day | High-frequency factors, microstructure |
| Weekly | Every Friday (or last trading day of week) | Momentum, reversal factors |
| Monthly | Last trading day of month (default) | Value, quality, fundamental factors |

**Rebalancing procedure**:

```
1. Identify rebalance dates from TradingCalendar
2. On each rebalance date t:
   a. Compute factor values f(i, t) using FactorEngine (with PIT validation)
   b. Sort and assign quintiles
   c. Compute portfolio weights
   d. Calculate turnover: TO(t) = sum(|w_new(i) - w_old(i)|) / 2
   e. Record portfolio composition
3. Between rebalance dates, portfolios are held static (buy-and-hold)
```

**Critical**: Factor values at rebalance date t must use data available at t (point-in-time). The `FactorEngine._filter_point_in_time()` with `publication_lag` ensures no look-ahead bias. For fundamental factors (EP, BP, SP), a `publication_lag=1` means only data published at least 1 day before t is used.

### 1.4 Transaction Cost Model

Per guidance specification, a simplified fixed-bps cost model:

```
Cost(t) = TO(t) * |trade_value| * cost_bps / 10000
```

Where `cost_bps` defaults to 15 basis points (typical A-share round-trip: ~8-12 bps brokerage + ~10 bps impact for mid-cap). This is deliberately simplified -- full market impact modeling is out of scope.

---

## 2. Metrics -- Performance Metrics Definitions and Formulas

The 8 core metrics are computed in a single pass through the return series (specification requirement: stateful MetricsCalculator).

### 2.1 Annualized Return (R_annual)

```
R_annual = (Product_{t=1}^{T} (1 + R(t)))^{252/T} - 1
```

Where 252 is the standard number of trading days per year. For monthly rebalancing: `R_annual = (1 + R_total)^{12/N_months} - 1`.

**Implementation note**: Use geometric compounding, not arithmetic mean. Arithmetic mean overstates returns for volatile strategies.

### 2.2 Sharpe Ratio (SR)

```
SR = (R_p - R_f) / sigma_p * sqrt(252)
```

Where:
- `R_p` = mean daily portfolio return
- `R_f` = risk-free rate (use SHIBOR overnight rate or constant 2% for simplicity)
- `sigma_p` = std dev of daily portfolio returns
- `sqrt(252)` = annualization factor

**A-share adaptation**: For L/S portfolios, the benchmark excess return is already market-neutral, so `R_f` is often set to 0. The Sharpe then measures pure risk-adjusted alpha.

**Thresholds** (industry norms):
- SR > 2.0: Excellent factor
- SR 1.0-2.0: Good factor
- SR 0.5-1.0: Marginal factor
- SR < 0.5: Poor factor

### 2.3 Maximum Drawdown (MDD)

```
MDD = max_{t in [0,T]} (max_{s in [0,t]} V(s) - V(t)) / max_{s in [0,t]} V(s)
```

Where `V(t)` is the cumulative portfolio value at time t. MDD is reported as a positive number (e.g., 0.15 = 15% drawdown).

**Drawdown duration**: Also track the number of trading days from peak to recovery (drawdown duration). This is important for assessing capital efficiency.

### 2.4 Win Rate (WR)

```
WR = count(R(t) > 0) / T
```

The proportion of periods with positive returns. For daily frequency, expect ~50-55% for a moderate factor; for monthly frequency, expect higher (55-65%) as monthly returns are less noisy.

### 2.5 Profit/Loss Ratio (PLR)

```
PLR = mean(R(t) | R(t) > 0) / |mean(R(t) | R(t) < 0)|
```

The average winning return divided by the absolute average losing return. PLR > 1.0 means winners are larger than losers.

**Kelly-optimal interpretation**: The optimal fraction of capital to allocate is:

```
f* = WR - (1 - WR) / PLR
```

If f* < 0, the strategy has negative expected value.

### 2.6 Calmar Ratio (CR)

```
CR = R_annual / MDD
```

The annualized return divided by maximum drawdown. Calmar is preferred over Sharpe for tail-risk assessment because it directly penalizes deep drawdowns.

**Thresholds**:
- CR > 3.0: Excellent
- CR 1.5-3.0: Good
- CR 0.5-1.5: Marginal
- CR < 0.5: Poor

### 2.7 Information Ratio (IR)

```
IR = (R_p - R_b) / sigma(R_p - R_b) * sqrt(252)
```

Where `R_b` is the benchmark return (default: CSI 300) and `sigma(R_p - R_b)` is the tracking error. IR measures active return per unit of active risk.

**Note**: For L/S portfolios, IR is conceptually similar to Sharpe (since the L/S spread is already benchmark-neutral), but IR uses the benchmark excess return as the reference, which matters when comparing against a specific benchmark like CSI 300.

### 2.8 Turnover Rate (TR)

```
TR = (1/T) * sum_{t=1}^{T} TO(t)
```

Where `TO(t) = sum(|w_new(i) - w_old(i)|) / 2` at each rebalance date. This is the two-way turnover (buys + sells).

**A-share specific**: High turnover (>50% monthly) is problematic due to stamp tax (0.05% sell-side), brokerage fees, and market impact. Factors with high IC but high turnover may underperform after costs.

### 2.9 MetricsCalculator Implementation Pattern

```python
@dataclass(frozen=True)
class PerformanceMetrics:
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_loss_ratio: float
    calmar_ratio: float
    information_ratio: float
    turnover_rate: float
```

The calculator should accumulate state during iteration:

```
init:  cum_return = 1.0, peak = 1.0, wins = 0, losses = 0, ...
for each R(t):
    cum_return *= (1 + R(t))
    peak = max(peak, cum_return)
    dd = (peak - cum_return) / peak  --> track max
    if R(t) > 0: wins += 1; win_sum += R(t)
    if R(t) < 0: losses += 1; loss_sum += R(t)
    running_sum += R(t); running_sq += R(t)^2
finalize: compute all 8 metrics from accumulated state
```

This single-pass design avoids redundant iteration over the return series.

---

## 3. IC Analysis -- Factor IC Methodology

### 3.1 Pearson IC vs Spearman RankIC

The existing `audit.py` already provides both. For the backtest engine, **RankIC (Spearman) is preferred** because:

1. Factor values and returns are typically non-normally distributed
2. RankIC is robust to outliers (common in A-shares due to limit-up/limit-down)
3. RankIC measures monotonic relationship, not linear -- more appropriate for factor evaluation

**Pearson IC** (`compute_ic`): `corr(f_i, r_i)` across all stocks i at time t. Measures linear correlation.

**Spearman RankIC** (`compute_rank_ic`): `corr(rank(f_i), rank(r_i))` across all stocks i at time t. Measures rank correlation.

### 3.2 Rolling IC Computation

The existing `compute_rolling_ic` uses a rolling window (default 60 days in `audit.py`, configurable to 20 days per guidance spec). The computation:

```
For each date t >= window:
    IC(t) = corr(factor_values[t-window+1:t], forward_returns[t-window+1:t])
```

**For cross-sectional IC** (the standard in factor research):

```
For each date t:
    IC(t) = RankIC({f(i,t)}_{i in U_t}, {r(i,t+1)}_{i in U_t})
```

This computes the cross-sectional rank correlation between factor values and 1-day forward returns across all stocks at a single point in time. The rolling IC then tracks how this cross-sectional IC evolves over time.

**Implementation bridge**: The existing `compute_rolling_ic` computes time-series IC (single stock, multiple periods). For cross-sectional IC (multiple stocks, single period), the backtest engine needs a separate function:

```python
def compute_cross_sectional_ic(
    factor_panel: pd.DataFrame,  # MultiIndex (date, ticker)
    return_panel: pd.DataFrame,  # MultiIndex (date, ticker)
) -> pd.Series:
    """Compute cross-sectional RankIC for each date."""
    dates = factor_panel.index.get_level_values(0).unique()
    ics = {}
    for dt in dates:
        fv = factor_panel.loc[dt].dropna()
        fr = return_panel.loc[dt].dropna()
        common = fv.index.intersection(fr.index)
        if len(common) < 10:  # minimum stock count
            continue
        ics[dt] = spearmanr(fv.loc[common], fr.loc[common])[0]
    return pd.Series(ics, name="cross_sectional_ic")
```

### 3.3 ICIR (IC Information Ratio)

```
ICIR = mean(IC_t) / std(IC_t)
```

The existing `compute_icir` in `audit.py` already implements this. ICIR measures the stability of the factor's predictive power over time.

**Factor rating thresholds** (from `rate_factor`):

| Rating | |ICIR| Threshold | Interpretation |
|--------|----------------|----------------|
| A | >= 0.5 | Highly stable, strong predictive power |
| B | >= 0.3 | Moderately stable |
| C | >= 0.1 | Weak stability |
| D | < 0.1 | Unstable, unreliable factor |

**Critical insight**: A factor can have high mean IC but low ICIR if the IC is volatile. ICIR is the primary metric for factor selection in multi-factor models.

### 3.4 IC Decay Analysis

The existing `decay.py` provides `compute_ic_decay` and `compute_decay_half_life`. This is essential for determining optimal holding periods:

- **Fast decay** (< 5 days): Intraday/overnight factors, not suitable for daily backtest
- **Medium decay** (5-20 days): Suitable for weekly rebalancing
- **Slow decay** (20-60 days): Suitable for monthly rebalancing
- **Very slow decay** (60+ days): Fundamental factors, quarterly rebalancing

The backtest engine should auto-suggest rebalancing frequency based on IC decay half-life.

---

## 4. Attribution -- Return Attribution Model

### 4.1 Barra-Style Factor Model

The return attribution decomposes portfolio returns into systematic factor components and idiosyncratic residual:

```
R(i, t) = alpha(i) + sum_{k=1}^{K} beta(i, k) * F(k, t) + epsilon(i, t)
```

Where:
- `R(i, t)` = excess return of stock i at time t
- `alpha(i)` = stock-specific alpha (intercept)
- `beta(i, k)` = exposure of stock i to factor k
- `F(k, t)` = return of factor k at time t
- `epsilon(i, t)` = residual (idiosyncratic) return

### 4.2 Factor Exposure Computation

For a portfolio P, the factor exposure is:

```
beta(P, k) = sum_{i in P} w(i) * beta(i, k)
```

Where `beta(i, k)` is estimated via cross-sectional regression:

```
R(i, t) = sum_{k} beta(i, k) * F(k, t) + epsilon(i, t)
```

**Simplified approach for P2**: Since we are evaluating single-factor quintile portfolios, the exposure to the sorting factor is approximately 1.0 for Q5 and -1.0 for Q1 (by construction). The attribution focuses on:

1. **Factor return component**: `F(factor, t) = R_Q5(t) - R_Q1(t)` (the L/S spread)
2. **Residual component**: Stock-specific returns within each quintile

### 4.3 Attribution Decomposition for L/S Portfolio

```
R_LS(t) = Factor_Return(t) + Residual(t)

Factor_Return(t) = beta_LS * F(t)    # systematic component
Residual(t) = R_LS(t) - Factor_Return(t)  # idiosyncratic component
```

**For quintile portfolios**:
- Factor return = quintile spread return (by construction)
- Residual = within-quintile dispersion (diversification benefit)

**Attribution report structure**:

```python
@dataclass(frozen=True)
class AttributionResult:
    factor_name: str
    factor_return_contribution: float  # % of total return from factor
    residual_contribution: float       # % of total return from residual
    factor_exposure: float             # portfolio beta to factor
    r_squared: float                   # how much variance the factor explains
    turnover_impact: float             # return lost to transaction costs
```

### 4.4 Multi-Factor Extension (Future)

While P2 focuses on single-factor evaluation, the attribution model should be designed for easy extension to multi-factor:

```
R_LS(t) = sum_{k} w_k * F_k(t) + Residual(t)
```

Where `w_k` is the portfolio's exposure to factor k, and `F_k(t)` is the return of factor k. This follows the Barra risk model structure.

---

## 5. Benchmark -- Benchmark Comparison Methodology

### 5.1 Benchmark Selection

**Default benchmark**: CSI 300 (沪深300) -- the most liquid A-share broad market index.

**Rationale**: CSI 300 represents the large-cap segment, is actively traded (ETF, futures), and is the de facto benchmark for A-share institutional investors.

**Alternative benchmarks** (configurable):

| Benchmark | Code | Use Case |
|-----------|------|----------|
| CSI 300 | 000300.SH | Default, large-cap |
| CSI 500 | 000905.SH | Mid-cap factors |
| CSI 800 | 000906.SH | Full market |
| CSI All Share | 000985.CSI | Broadest coverage |

### 5.2 Excess Return Calculation

```
R_excess(t) = R_portfolio(t) - R_benchmark(t)
```

For L/S portfolios, the benchmark excess return is particularly meaningful because:
- The L/S spread is already market-neutral
- Excess return measures whether the factor adds value beyond what the benchmark provides
- However, for a pure L/S strategy, the benchmark comparison is less relevant (the strategy is self-benchmarking)

### 5.3 Benchmark-Relative Metrics

These metrics are computed when a benchmark is provided:

1. **Excess annualized return**: `R_p_annual - R_b_annual`
2. **Tracking error**: `std(R_p - R_b) * sqrt(252)`
3. **Information ratio**: (see Section 2.7)
4. **Beta**: `cov(R_p, R_b) / var(R_b)`
5. **Alpha (Jensen's)**: `R_p - [R_f + beta * (R_b - R_f)]`

### 5.4 Benchmark Data Requirements

The benchmark index data must be:
- Adjusted for dividends and splits (total return index)
- Aligned with the trading calendar (same trading days)
- Available for the full backtest period

The `TradingCalendar` from P1 ensures date alignment. Benchmark data can be fetched via the same `DataSource` pattern used by `FactorEngine`.

---

## 6. Risk Controls -- Risk Controls and Validation

### 6.1 Look-Ahead Bias Prevention

**Primary control**: Point-in-time (PIT) data access enforced via `FactorEngine._filter_point_in_time()`.

```
cutoff_date = compute_date - publication_lag days
data = data[data.date <= cutoff_date]
```

**Validation test**: For each factor, verify that the factor value at date t uses only data available at or before t. This can be tested by:
1. Computing factor at date t with full data
2. Computing factor at date t with data truncated at t-1
3. Verifying they are identical (or within floating-point tolerance)

### 6.2 Survivorship Bias Prevention

**Control**: The stock universe at each rebalance date must include all stocks that were tradable at that time, not just currently listed stocks. This means:
- Use point-in-time stock listings (delisted stocks must be included up to their delisting date)
- Include stocks that were suspended (assign NaN factor values, exclude from sorting)
- Include newly listed stocks (IPO stocks enter the universe after a warmup period, typically 60 trading days for A-shares)

### 6.3 Data Quality Controls

| Check | Threshold | Action |
|-------|-----------|--------|
| Missing factor values | > 30% of universe | Skip rebalance date |
| Insufficient stock count | < 50 stocks after filtering | Skip rebalance date |
| Extreme factor values | > 5 std from mean | Winsorize at 1%/99% percentile |
| Zero-volume stocks | Volume = 0 | Exclude from universe |
| Price edge cases | Price < 1 CNY or > 10000 CNY | Flag for review |

### 6.4 Turnover Control

**High turnover warning**: If monthly turnover exceeds 80%, the factor may be overfitting to noise. The backtest engine should:
1. Report turnover metrics prominently
2. Flag factors where turnover-adjusted Sharpe degrades significantly vs. raw Sharpe
3. Suggest rebalancing frequency reduction if turnover is excessive

### 6.5 Statistical Significance

**IC t-test**: Under the null hypothesis that IC mean = 0:

```
t = IC_mean / (IC_std / sqrt(N))
```

Where N is the number of IC observations. A factor is statistically significant at 5% level if |t| > 1.96.

**Bootstrap confidence interval**: For robustness, compute the 95% confidence interval of IC mean via bootstrap resampling (1000 iterations recommended).

### 6.6 Out-of-Sample Validation

**Walk-forward test**: Split the backtest period into in-sample and out-of-sample segments:

```
|---- In-Sample (train) ----|---- Out-of-Sample (test) ----|
|        70%                 |          30%                  |
```

Report metrics for both periods. Significant degradation in out-of-sample performance indicates overfitting.

---

## 7. Market Specifics -- A-Share Market Considerations

### 7.1 Trading Calendar Integration

The `TradingCalendar` from P1 (`calendar.py`) is critical for the backtest engine. Key considerations:

- **Hardcoded holidays 2024-2026**: The calendar covers the current planning horizon. The `refresh_calendar()` stub indicates future API-based updates.
- **Compensation workdays**: Weekend trading days (e.g., Spring Festival makeup) are handled via `CHINA_TRADING_DAYS`. The backtest engine must use these for accurate date counting.
- **Binary search efficiency**: `TradingCalendar.trading_day_offset()` uses `bisect` for O(log n) lookups, critical for large-scale backtests with thousands of rebalancing dates.

### 7.2 A-Share Specific Factor Behaviors

**Momentum reversal**: The `Momentum1M` factor is implemented as `-((close / close.shift(20)) - 1)`, reflecting the well-documented short-term reversal effect in A-shares. Unlike US markets, A-share momentum tends to reverse in the short term (< 1 month) due to retail investor herding and limit-up/limit-down mechanics.

**Value factor caveats**: EP, BP, SP factors use TTM (trailing twelve months) financials. In A-shares, financial reporting has a significant lag:
- Annual reports: Published by April 30 (following year)
- Quarterly reports: Published within 1 month of quarter end
- The `publication_lag=1` in `FactorSpec` is a simplified approximation; a more accurate model would use different lags for different report types.

### 7.3 Limit-Up / Limit-Down (涨跌停)

A-share daily price limits:
- Main board: +/-10%
- ChiNext (创业板): +/-20% (since 2020 reform)
- STAR Market (科创板): +/-20%
- ST stocks: +/-5%

**Impact on backtest**:
- Stocks at limit-up cannot be bought (no sell liquidity)
- Stocks at limit-down cannot be sold (no buy liquidity)
- The backtest engine should model this: if a stock hits limit-up/down, exclude it from trading on that day or delay execution to the next day

**Simplified approach**: Flag limit-hit days but do not alter the equal-weight calculation (academic standard). Full limit-up/down modeling is complex and out of scope for P2.

### 7.4 Short Selling Constraints

A-share short selling is limited:
- Only available through securities lending (融资融券)
- Most stocks are not lendable
- Borrowing costs are high (typically 8-10% annualized)

**Backtest implication**: The L/S spread is a theoretical construct. In practice, the "short" leg is often approximated by:
1. Not actually shorting (long-only quintile minus benchmark)
2. Using index futures to hedge market exposure
3. Shorting via ETF (if available)

The backtest engine should clearly label the L/S spread as "theoretical" and note the practical constraints.

### 7.5 Market Microstructure Effects

**Settlement**: T+1 settlement (buy today, can sell tomorrow). This affects:
- Turnover calculation: Same-day round-trips are impossible
- The backtest engine should model T+1 by requiring a 1-day delay between buy and sell signals

**Stamp tax**: 0.05% on sell-side only (reduced from 0.1% in 2023). This asymmetry favors buy-and-hold strategies.

**Lot size**: 100-share lots (整手). Positions must be in multiples of 100 shares. For equal-weight portfolios with many stocks, this creates rounding effects. The backtest should use fractional shares for theoretical accuracy.

### 7.6 Sector and Industry Considerations

A-share sectors follow the CITIC (中信) or SW (申万) industry classification. The backtest engine should support:

1. **Industry-neutral sorting**: Sort within each industry, then combine quintiles. This isolates the factor effect from industry exposure.
2. **Industry concentration reporting**: Report the industry composition of each quintile to identify sector biases.

This is not a core P2 requirement but should be designed for easy extension.

### 7.7 Data Source Alignment

The existing factor implementations use `data_source="eastmoney"` (东方财富). The backtest engine must ensure:
- Price data and fundamental data come from the same source (avoid mismatched adjustments)
- Dividend/split adjustments are applied consistently (复权处理)
- The `ExRightAdjustment` from P1 should be used for adjusted prices

---

## 8. Integration Points with Existing Codebase

### 8.1 P6 FactorEngine Integration

The backtest engine consumes FactorEngine output directly:

```python
# FactorEngine.compute_batch returns DataFrame with (ticker x factor_id)
factor_values = factor_engine.compute_batch(
    factor_ids=["ep", "bp", "momentum_6m_1m"],
    tickers=universe,
    target_date=rebalance_date
)
```

The adapter pattern bridges the FactorEngine interface (per-date computation) with the backtest engine's need for panel data (date x ticker).

### 8.2 P1 TradingCalendar Integration

```python
from synapse.core.market.calendar import TradingCalendar, add_trading_days

# Get rebalance dates
rebalance_dates = trading_days_between(start_date, end_date)
if rebalance_freq == "monthly":
    rebalance_dates = [d for d in rebalance_dates if d == last_trading_day_of_month(d)]

# Forward returns: next trading day's return
for dt in rebalance_dates:
    next_dt = add_trading_days(dt, 1)
    forward_return = (price[next_dt] - price[dt]) / price[dt]
```

### 8.3 P6 Portfolio Optimizer Integration

The existing `FactorPortfolioOptimizer` provides equal-weight, IC-weighted, and risk-parity methods. For quintile sorting, the equal-weight method is the default, but the IC-weighted method could be used for combining multiple factors within a quintile.

### 8.4 Audit System Integration

The existing `audit.py` functions (`compute_ic`, `compute_rank_ic`, `compute_icir`, `rate_factor`) should be reused by the backtest engine's IC analysis module rather than reimplemented.

---

## 9. Implementation Recommendations

### 9.1 Data Flow Architecture

```
FactorEngine.compute_batch() --> factor_panel (date x ticker DataFrame)
                                       |
                                       v
                            QuintileSorter.sort() --> quintile_labels (Series)
                                       |
                                       v
                            PortfolioBuilder.build() --> quintile_returns (DataFrame: Q1..Q5 + L/S)
                                       |
                                       v
                            MetricsCalculator.compute() --> PerformanceMetrics (frozen dataclass)
                                       |
                                       v
                            ICAnalyzer.analyze() --> ICAnalysisResult (frozen dataclass)
                                       |
                                       v
                            AttributionEngine.decompose() --> AttributionResult (frozen dataclass)
                                       |
                                       v
                            BacktestResult (frozen dataclass, persisted to Parquet)
```

### 9.2 Frozen Dataclass Pattern

Following the data architect's decision, all result objects must be frozen dataclasses:

```python
@dataclass(frozen=True)
class BacktestResult:
    factor_name: str
    start_date: date
    end_date: date
    rebalance_freq: str
    quintile_returns: pd.DataFrame     # columns: Q1..Q5, L/S
    performance_metrics: PerformanceMetrics
    ic_analysis: ICAnalysisResult
    attribution: AttributionResult
    metadata: dict                     # benchmark, cost_bps, etc.
```

### 9.3 Test Strategy

Following the guidance specification's risk controls:

1. **Unit tests**: Each metric computation in isolation
2. **Integration tests**: Full backtest pipeline with synthetic data
3. **Regression tests**: Known factor behavior (e.g., value factor should have positive IC in A-shares historically)
4. **Edge case tests**: Empty universe, single-stock quintile, all-NaN factors
5. **PIT validation tests**: Verify no look-ahead bias in factor computation

---

## Appendix: Glossary

| Term | Definition |
|------|------------|
| Quintile | Portfolio divided into 5 equal groups sorted by factor value |
| Long-Short | Strategy going long top quintile and short bottom quintile |
| IC | Rank correlation between factor values and forward returns |
| ICIR | IC mean / IC standard deviation |
| Sharpe Ratio | Risk-adjusted return (excess return / volatility) |
| Max Drawdown | Maximum peak-to-trough decline |
| Turnover Rate | Proportion of portfolio positions changed each period |
| Factor Exposure | Portfolio's sensitivity to factor returns |
| Attribution Analysis | Decomposing returns into factor and residual components |
| PIT | Point-in-time -- data available at the moment of decision |
| CSI 300 | 沪深300 -- benchmark index of 300 large-cap A-shares |
| T+1 | Settlement rule: buy today, sell tomorrow |
| ST | Special Treatment -- stocks with financial distress, 5% price limit |
