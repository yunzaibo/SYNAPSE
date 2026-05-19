from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

import numpy as np
import pandas as pd

from synapse.backtest.config import BacktestConfig
from synapse.backtest.metrics import MetricsCalculator, compute_metrics, BacktestMetrics
from synapse.core.market.calendar import trading_days_between


# ---------------------------------------------------------------------------
# CostModel — transaction cost + slippage
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CostModel:
    """Immutable transaction cost model.

    Computes turnover-based costs as:
        turnover = len(new_positions - old_positions) / total_stocks
        cost = turnover * (transaction_cost_bps + slippage_bps) / 10000
    """

    transaction_cost_bps: float
    slippage_bps: float

    def compute_cost(
        self,
        old_positions: set,
        new_positions: set,
        total_stocks: int,
    ) -> float:
        """Compute transaction cost for a position change.

        Args:
            old_positions: Set of ticker symbols in previous portfolio.
            new_positions: Set of ticker symbols in current portfolio.
            total_stocks: Total number of stocks in the universe.

        Returns:
            Cost as a decimal (e.g., 0.0001 = 1 bps).
        """
        turnover = len(new_positions - old_positions) / max(total_stocks, 1)
        return turnover * (self.transaction_cost_bps + self.slippage_bps) / 10000


# ---------------------------------------------------------------------------
# BacktestRequest — immutable request container
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BacktestRequest:
    """Immutable container for a backtest request.

    Bundles factor data, returns, configuration, and optional metadata
    into a single frozen dataclass for the engine's ``run()`` method.
    """

    factor_values: pd.DataFrame  # MultiIndex (date, ticker)
    forward_returns: pd.Series   # MultiIndex (date, ticker)
    config: BacktestConfig
    benchmark_returns: Optional[pd.Series] = None
    factor_id: str = ""


# ---------------------------------------------------------------------------
# BacktestResult — legacy mutable result
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    config: BacktestConfig
    metrics: BacktestMetrics
    portfolio_returns: list = field(default_factory=list)
    trades: list = field(default_factory=list)
    status: str = "running"  # running | succeeded | failed


# ---------------------------------------------------------------------------
# BacktestEngine — DI-driven orchestrator
# ---------------------------------------------------------------------------

class BacktestEngine:
    """Event-driven backtest engine with dependency injection.

    Orchestrates the full pipeline:
        quintile sorting -> portfolio simulation -> metrics -> IC analysis -> attribution

    Components are injected via constructor; defaults are used when not provided.
    The ``run()`` method accepts a ``BacktestRequest`` and returns a frozen
    ``BacktestRunResult``.  The legacy ``run_backtest()`` method is preserved
    for backward compatibility.
    """

    def __init__(
        self,
        sorter=None,
        metrics_calc=None,
        ic_analyzer=None,
        attribution=None,
        spread=None,
    ):
        from synapse.backtest.quintile import QuintileSorter
        from synapse.backtest.ic_analyzer import ICAnalyzer
        from synapse.backtest.attribution import AttributionEngine
        from synapse.backtest.spread import LongShortSpread

        self.sorter = sorter or QuintileSorter()
        self.metrics_calc = metrics_calc or MetricsCalculator()
        self.ic_analyzer = ic_analyzer or ICAnalyzer()
        self.attribution = attribution or AttributionEngine()
        self.spread = spread or LongShortSpread()

    # ------------------------------------------------------------------
    # New event-driven API
    # ------------------------------------------------------------------

    def run(self, request: BacktestRequest):
        """Execute a full backtest pipeline.

        Args:
            request: Frozen BacktestRequest with factor data, returns, and config.

        Returns:
            BacktestRunResult with all computed outputs.
        """
        from synapse.backtest.result import (
            BacktestRunResult,
            QuintilePortfolio,
            PerformanceMetrics,
        )

        config = request.config
        run_id = uuid.uuid4().hex[:12]
        run_ts = datetime.now().isoformat()

        try:
            return self._run_pipeline(request, run_id, run_ts)
        except Exception as exc:
            return BacktestRunResult(
                id=run_id,
                run_timestamp=run_ts,
                start_date=config.start_date,
                end_date=config.end_date,
                factor_id=request.factor_id,
                status="failed",
                error=str(exc),
            )

    def _run_pipeline(
        self,
        request: BacktestRequest,
        run_id: str,
        run_ts: str,
    ):
        from synapse.backtest.result import (
            BacktestRunResult,
            QuintilePortfolio,
            PerformanceMetrics,
        )

        config = request.config
        fv = request.factor_values
        fr = request.forward_returns

        # --- empty-data guard ---
        if fv.empty or fr.empty:
            return BacktestRunResult(
                id=run_id,
                run_timestamp=run_ts,
                config=config.to_dict() if hasattr(config, "to_dict") else {},
                start_date=config.start_date,
                end_date=config.end_date,
                factor_id=request.factor_id,
                status="failed",
                error="Empty factor_values or forward_returns",
            )

        # --- Generate rebalance dates via TradingCalendar ---
        start_dt = date.fromisoformat(config.start_date)
        end_dt = date.fromisoformat(config.end_date)
        all_trading_days = trading_days_between(start_dt, end_dt)
        rebalance_dates = self._select_rebalance_dates(
            all_trading_days, config.rebalance_frequency
        )

        if not rebalance_dates:
            return BacktestRunResult(
                id=run_id,
                run_timestamp=run_ts,
                config=self._config_to_dict(config),
                start_date=config.start_date,
                end_date=config.end_date,
                factor_id=request.factor_id,
                status="failed",
                error="No rebalance dates found in the given range",
            )

        # --- Normalize rebalance dates to match factor data index ---
        factor_series = self._df_to_series(fv)
        rebalance_dates = self._normalize_dates(rebalance_dates, factor_series)

        # --- Quintile sorting for all rebalance dates ---
        quintile_portfolios = self.sorter.sort_timeseries(
            factor_series,
            rebalance_dates,
            n_quintiles=config.n_quintiles,
            factor_name=request.factor_id,
        )

        # --- Simulate portfolio returns per rebalance period ---
        long_short_returns: list[float] = []
        quintile_period_returns: dict[int, list[float]] = {
            q: [] for q in range(1, config.n_quintiles + 1)
        }
        portfolio_returns_list: list[float] = []
        cost_model = CostModel(
            transaction_cost_bps=config.transaction_cost_bps,
            slippage_bps=config.slippage_bps,
        )
        prev_long: set = set()
        prev_short: set = set()

        for i, reb_date in enumerate(rebalance_dates):
            # Determine the holding period: from reb_date to the next rebalance date
            if i + 1 < len(rebalance_dates):
                next_reb = rebalance_dates[i + 1]
            else:
                next_reb = end_dt

            # Extract forward returns for this period
            try:
                period_fr = fr.xs(reb_date, level="date")
            except KeyError:
                continue

            if period_fr.empty:
                continue

            portfolio = quintile_portfolios.get(reb_date)
            if portfolio is None:
                continue

            # Compute per-quintile returns
            period_q_returns: dict[int, float] = {}
            for q_id, tickers in portfolio.quintiles.items():
                ticker_list = [t for t in tickers if t in period_fr.index]
                if ticker_list:
                    q_ret = float(period_fr.loc[ticker_list].mean())
                else:
                    q_ret = 0.0
                period_q_returns[q_id] = q_ret
                quintile_period_returns[q_id].append(q_ret)

            # Long-short: top quintile long, bottom quintile short
            top_q = config.n_quintiles  # e.g., 5
            bottom_q = 1
            long_ret = period_q_returns.get(top_q, 0.0)
            short_ret = period_q_returns.get(bottom_q, 0.0)

            # Transaction cost
            all_tickers: set = set()
            for tickers in portfolio.quintiles.values():
                all_tickers.update(tickers)
            long_tickers = set(portfolio.quintiles.get(top_q, ()))
            short_tickers = set(portfolio.quintiles.get(bottom_q, ()))
            new_long = long_tickers - prev_long
            new_short = short_tickers - prev_short
            cost = cost_model.compute_cost(
                prev_long | prev_short,
                long_tickers | short_tickers,
                len(all_tickers),
            )

            period_return = long_ret - short_ret - cost
            long_short_returns.append(period_return)
            portfolio_returns_list.append(period_return)
            prev_long = long_tickers
            prev_short = short_tickers

        # --- Performance metrics ---
        ret_array = (
            np.array(portfolio_returns_list)
            if portfolio_returns_list
            else np.array([0.0])
        )
        bench_array = (
            request.benchmark_returns.values
            if request.benchmark_returns is not None
            else None
        )
        performance = self.metrics_calc.compute(ret_array, benchmark_returns=bench_array)

        # --- IC analysis (optional) ---
        ic_result = None
        if config.enable_ic_analysis:
            ic_result = self.ic_analyzer.compute_ic(
                fv, fr, factor_id=request.factor_id
            )

        # --- Attribution (optional) ---
        attr_result = None
        if config.enable_attribution and portfolio_returns_list:
            attr_result = self._run_attribution(
                portfolio_returns_list, rebalance_dates, fv, fr
            )

        # --- Long-short spread ---
        spread_result = None
        if portfolio_returns_list and quintile_period_returns.get(1):
            q_df = pd.DataFrame(quintile_period_returns)
            # Rename columns to Q1..QN
            q_df.columns = [f"Q{c}" for c in q_df.columns]
            spread_result = self.spread.compute(q_df)

        # --- Assemble result ---
        benchmark_tuple = (
            tuple(request.benchmark_returns.tolist())
            if request.benchmark_returns is not None
            else ()
        )

        # Convert portfolio dates back to date objects for serialization
        # (they may have been converted to pd.Timestamp by _normalize_dates)
        normalized_portfolios = []
        for qp in tuple(quintile_portfolios.values()):
            if hasattr(qp.date, "date") and callable(qp.date.date):
                # pd.Timestamp -> date
                from synapse.backtest.result import QuintilePortfolio
                normalized_portfolios.append(
                    QuintilePortfolio(
                        date=qp.date.date(),
                        quintiles=qp.quintiles,
                        weights=qp.weights,
                        factor_name=qp.factor_name,
                        universe_size=qp.universe_size,
                        valid_count=qp.valid_count,
                    )
                )
            else:
                normalized_portfolios.append(qp)

        return BacktestRunResult(
            id=run_id,
            schema_version="1.0",
            config=self._config_to_dict(config),
            run_timestamp=run_ts,
            start_date=config.start_date,
            end_date=config.end_date,
            factor_id=request.factor_id,
            quintile_portfolios=tuple(normalized_portfolios),
            quintile_returns={
                q: float(np.mean(rets)) if rets else 0.0
                for q, rets in quintile_period_returns.items()
            },
            long_short_returns=tuple(long_short_returns),
            benchmark_returns=benchmark_tuple,
            performance=performance,
            ic_analysis=ic_result,
            attribution=attr_result,
            status="succeeded" if long_short_returns else "failed",
        )

    def _run_attribution(
        self,
        portfolio_returns_list: list[float],
        rebalance_dates: list[date],
        fv: pd.DataFrame,
        fr: pd.Series,
    ):
        """Run attribution on long-short returns vs quintile factor returns."""
        from synapse.backtest.result import AttributionResult

        if len(portfolio_returns_list) < 3:
            return AttributionResult()

        # Build factor returns from the long-short portfolio returns
        ps_ret = pd.Series(
            portfolio_returns_list[:len(rebalance_dates)],
            index=rebalance_dates[:len(portfolio_returns_list)],
        )
        # Create a dummy factor return (the long-short return itself as the factor)
        factor_ret_df = pd.DataFrame(
            {1: portfolio_returns_list[:len(rebalance_dates)]},
            index=rebalance_dates[:len(portfolio_returns_list)],
        )

        return self.attribution.compute(ps_ret, factor_ret_df)

    @staticmethod
    def _normalize_dates(
        rebalance_dates: list[date], factor_series: pd.Series
    ) -> list:
        """Convert rebalance date objects to match the factor data index type.

        The factor data index may use pd.Timestamp or date objects.
        This method ensures the rebalance dates are compatible with the
        index for .xs() lookups.
        """
        if not rebalance_dates:
            return rebalance_dates

        # Detect the date type used in the factor series index
        idx = factor_series.index
        if hasattr(idx, "get_level_values"):
            first_level = idx.get_level_values(0)
            if len(first_level) > 0:
                sample = first_level[0]
            else:
                sample = None
        else:
            sample = idx[0] if len(idx) > 0 else None

        if sample is None:
            return rebalance_dates

        # If index uses pd.Timestamp, convert date objects to Timestamps
        if isinstance(sample, pd.Timestamp):
            return [pd.Timestamp(d) for d in rebalance_dates]
        # If index uses date objects, keep as-is
        return rebalance_dates

    @staticmethod
    def _select_rebalance_dates(
        trading_days: list[date], frequency: str
    ) -> list[date]:
        """Select rebalance dates from trading days based on frequency.

        Args:
            trading_days: All trading days in the range.
            frequency: 'daily', 'weekly', or 'monthly'.

        Returns:
            List of rebalance dates.
        """
        if not trading_days:
            return []
        if frequency == "daily":
            return list(trading_days)
        elif frequency == "weekly":
            # Rebalance on the first trading day of each week (ISO week)
            result: list[date] = []
            current_week: Optional[int] = None
            for d in trading_days:
                iso_week = d.isocalendar()[1]
                if iso_week != current_week:
                    result.append(d)
                    current_week = iso_week
            return result
        else:  # monthly
            result = []
            current_month: Optional[tuple[int, int]] = None
            for d in trading_days:
                key = (d.year, d.month)
                if key != current_month:
                    result.append(d)
                    current_month = key
            return result

    @staticmethod
    def _df_to_series(df: pd.DataFrame) -> pd.Series:
        """Convert a single-column DataFrame to a Series, keeping MultiIndex."""
        if isinstance(df, pd.Series):
            return df
        if df.shape[1] == 1:
            return df.iloc[:, 0]
        raise ValueError(
            f"factor_values DataFrame must have exactly one column, got {df.shape[1]}"
        )

    @staticmethod
    def _config_to_dict(config: BacktestConfig) -> dict:
        """Convert BacktestConfig to a plain dict for storage."""
        return {
            "universe": config.universe,
            "benchmark": config.benchmark,
            "start_date": config.start_date,
            "end_date": config.end_date,
            "rebalance_frequency": config.rebalance_frequency,
            "transaction_cost_bps": config.transaction_cost_bps,
            "slippage_bps": config.slippage_bps,
            "position_limit": config.position_limit,
            "n_quintiles": config.n_quintiles,
            "ic_window": config.ic_window,
            "ic_min_periods": config.ic_min_periods,
            "enable_attribution": config.enable_attribution,
            "enable_ic_analysis": config.enable_ic_analysis,
            "output_dir": config.output_dir,
        }

    # ------------------------------------------------------------------
    # Legacy API — preserved for backward compatibility
    # ------------------------------------------------------------------

    def run_backtest(
        self,
        factor_values: pd.Series,
        forward_returns: pd.Series,
        config: BacktestConfig,
    ) -> BacktestResult:
        """Simple long-short backtest: top quintile long, bottom quintile short.

        1. Rank stocks by factor value each period
        2. Go long top 20%, short bottom 20%
        3. Equal weight within quintiles
        4. Apply transaction costs on rebalance
        5. Monthly rebalance

        This is the legacy API.  New code should use ``run(BacktestRequest)``.
        """
        # Align data
        aligned = pd.concat([factor_values, forward_returns], axis=1).dropna()
        if len(aligned) < 2:
            return BacktestResult(
                config=config,
                metrics=compute_metrics(np.array([]), np.array([])),
                status="failed",
            )

        factor_col = aligned.columns[0]
        returns_col = aligned.columns[1]

        # Get dates for monthly rebalance
        if hasattr(aligned.index, "date"):
            dates = pd.Series(aligned.index).dt.to_period("M")
        else:
            dates = pd.Series(range(len(aligned))) // 21  # approximate monthly

        # Convert to numpy array to avoid pandas MultiIndex alignment issues
        dates_arr = dates.values

        portfolio_returns = []
        trades = []
        prev_long: set = set()
        prev_short: set = set()

        for period in dates.unique():
            mask = dates_arr == period
            period_data = aligned.iloc[mask]
            if len(period_data) < 5:
                continue

            fv = period_data[factor_col]
            fr = period_data[returns_col]

            # Rank and select quintiles
            n = len(fv)
            q20 = max(1, n // 5)
            ranked = fv.rank(ascending=False)

            long_stocks = set(ranked[ranked <= q20].index)
            short_stocks = set(ranked[ranked > n - q20].index)

            # Calculate returns
            long_ret = fr.loc[list(long_stocks)].mean() if long_stocks else 0
            short_ret = fr.loc[list(short_stocks)].mean() if short_stocks else 0

            # Transaction costs (only on rebalance)
            new_long = long_stocks - prev_long
            new_short = short_stocks - prev_short
            cost_bps = config.transaction_cost_bps + config.slippage_bps
            turnover_cost = (len(new_long) + len(new_short)) / max(n, 1) * cost_bps / 10000

            period_return = long_ret - short_ret - turnover_cost
            portfolio_returns.append(period_return)

            trades.append({
                "period": str(period),
                "long": list(long_stocks),
                "short": list(short_stocks),
                "return": period_return,
            })

            prev_long = long_stocks
            prev_short = short_stocks

        ret_array = np.array(portfolio_returns) if portfolio_returns else np.array([0.0])
        bench_array = np.zeros_like(ret_array)

        metrics = compute_metrics(ret_array, bench_array)

        return BacktestResult(
            config=config,
            metrics=metrics,
            portfolio_returns=portfolio_returns,
            trades=trades,
            status="succeeded" if portfolio_returns else "failed",
        )
