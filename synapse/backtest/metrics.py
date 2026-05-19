from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from synapse.backtest.result import PerformanceMetrics


@dataclass
class BacktestMetrics:
    annual_return: float
    volatility: float
    sharpe: float
    max_drawdown: float
    turnover: float
    win_rate: float
    excess_return: float
    information_ratio: float


def compute_metrics(
    portfolio_returns: np.ndarray,
    benchmark_returns: np.ndarray,
    risk_free_rate: float = 0.0,
) -> BacktestMetrics:
    """Compute all 8 backtest metrics."""
    n = len(portfolio_returns)
    if n == 0:
        return BacktestMetrics(0, 0, 0, 0, 0, 0, 0, 0)

    # Annual return (assume 252 trading days)
    total_return = np.prod(1 + portfolio_returns) - 1
    annual_return = (1 + total_return) ** (252 / n) - 1

    # Volatility (annualized)
    volatility = np.std(portfolio_returns) * np.sqrt(252)

    # Sharpe ratio (use > 1e-10 to handle floating-point near-zero std)
    excess = portfolio_returns - risk_free_rate / 252
    std_excess = float(np.std(excess))
    sharpe = (np.mean(excess) / std_excess * np.sqrt(252)) if std_excess > 1e-10 else 0.0

    # Max drawdown
    cumulative = np.cumprod(1 + portfolio_returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - running_max) / running_max
    max_drawdown = float(np.min(drawdowns))

    # Turnover (simplified: average absolute daily change)
    turnover = float(np.mean(np.abs(portfolio_returns)))

    # Win rate
    win_rate = float(np.mean(portfolio_returns > 0))

    # Excess return
    excess_return = float(np.mean(portfolio_returns - benchmark_returns)) * 252

    # Information ratio (use > 1e-10 to handle floating-point near-zero std)
    active_returns = portfolio_returns - benchmark_returns
    tracking_error = float(np.std(active_returns) * np.sqrt(252))
    information_ratio = (excess_return / tracking_error) if tracking_error > 1e-10 else 0.0

    return BacktestMetrics(
        annual_return=round(annual_return, 6),
        volatility=round(volatility, 6),
        sharpe=round(sharpe, 4),
        max_drawdown=round(max_drawdown, 6),
        turnover=round(turnover, 6),
        win_rate=round(win_rate, 4),
        excess_return=round(excess_return, 6),
        information_ratio=round(information_ratio, 4),
    )


# ---------------------------------------------------------------------------
# MetricsCalculator — single-pass performance metrics
# ---------------------------------------------------------------------------


class MetricsCalculator:
    """Compute 8 core performance metrics in a single pass through the return series.

    Core metrics: annual_return, volatility, sharpe, max_drawdown,
    win_rate, profit_loss_ratio, calmar, information_ratio.

    Additional fields (turnover, long_short_spread, skewness, kurtosis,
    max_drawdown_duration) are populated where trivially available; others
    default to 0.0.
    """

    def __init__(
        self,
        risk_free_rate: float = 0.0,
        annualization_factor: int = 252,
    ) -> None:
        self._risk_free_rate = risk_free_rate
        self._annualization_factor = annualization_factor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute(
        self,
        returns: np.ndarray,
        benchmark_returns: Optional[np.ndarray] = None,
    ) -> PerformanceMetrics:
        """Compute all metrics in a single pass through *returns*.

        Parameters
        ----------
        returns : np.ndarray
            1-D array of periodic (daily) returns.
        benchmark_returns : np.ndarray, optional
            Benchmark return series for excess return / IR calculation.
            Passed per-call to avoid shared mutable state.

        Returns
        -------
        PerformanceMetrics
            Frozen dataclass with all 14 metric fields populated.
        """
        n = len(returns)
        if n == 0:
            return PerformanceMetrics()

        ann = self._annualization_factor
        rf_daily = self._risk_free_rate / ann
        has_bench = (
            benchmark_returns is not None
            and len(benchmark_returns) == n
        )

        # --- accumulation state ---
        cum_return = 1.0
        peak = 1.0
        max_dd_mag = 0.0  # positive magnitude

        wins = 0
        losses = 0
        win_sum = 0.0
        loss_sum = 0.0

        raw_sum = 0.0
        raw_sq = 0.0

        excess_sum = 0.0
        excess_sq = 0.0

        active_sum = 0.0
        active_sq = 0.0

        dd_duration = 0
        max_dd_duration = 0

        for i in range(n):
            r = float(returns[i])

            # cumulative return & drawdown
            cum_return *= 1.0 + r
            if cum_return > peak:
                peak = cum_return
                dd_duration = 0
            else:
                dd_mag = (peak - cum_return) / peak
                if dd_mag > max_dd_mag:
                    max_dd_mag = dd_mag
                dd_duration += 1
                if dd_duration > max_dd_duration:
                    max_dd_duration = dd_duration

            # win / loss
            if r > 0:
                wins += 1
                win_sum += r
            else:
                losses += 1
                loss_sum += r

            # raw accumulators (volatility)
            raw_sum += r
            raw_sq += r * r

            # excess accumulators (Sharpe)
            e = r - rf_daily
            excess_sum += e
            excess_sq += e * e

            # active accumulators (Information Ratio)
            if has_bench:
                a = r - float(benchmark_returns[i])
                active_sum += a
                active_sq += a * a

        # --- finalize metrics ---

        # Annual Return
        total_return = cum_return - 1.0
        annual_return = (1.0 + total_return) ** (ann / n) - 1.0

        # Volatility (population std, matches np.std default)
        raw_mean = raw_sum / n
        raw_var = raw_sq / n - raw_mean * raw_mean
        if raw_var < 0:
            raw_var = 0.0
        volatility = math.sqrt(raw_var) * math.sqrt(ann)

        # Sharpe
        excess_mean = excess_sum / n
        excess_var = excess_sq / n - excess_mean * excess_mean
        if excess_var < 0:
            excess_var = 0.0
        excess_std = math.sqrt(excess_var)
        if excess_std > 1e-10:
            sharpe = excess_mean / excess_std * math.sqrt(ann)
        else:
            sharpe = 0.0

        # Max Drawdown (negative, matching existing convention)
        max_drawdown = -max_dd_mag

        # Win Rate
        win_rate = wins / n

        # Profit / Loss Ratio
        if losses > 0 and loss_sum != 0 and wins > 0:
            profit_loss_ratio = (win_sum / wins) / (-loss_sum / losses)
        else:
            profit_loss_ratio = 0.0

        # Calmar
        if max_dd_mag > 1e-10:
            calmar = annual_return / max_dd_mag
        else:
            calmar = 0.0

        # Excess Return & Information Ratio
        if has_bench:
            excess_return = active_sum / n * ann
            active_mean = active_sum / n
            active_var = active_sq / n - active_mean * active_mean
            if active_var < 0:
                active_var = 0.0
            tracking_error = math.sqrt(active_var) * math.sqrt(ann)
            if tracking_error > 1e-10:
                information_ratio = excess_return / tracking_error
            else:
                information_ratio = 0.0
        else:
            excess_return = 0.0
            information_ratio = 0.0

        return PerformanceMetrics(
            annual_return=round(annual_return, 6),
            volatility=round(volatility, 6),
            sharpe=round(sharpe, 4),
            max_drawdown=round(max_drawdown, 6),
            turnover=0.0,
            win_rate=round(win_rate, 4),
            excess_return=round(excess_return, 6),
            information_ratio=round(information_ratio, 4),
            calmar=round(calmar, 4),
            profit_loss_ratio=round(profit_loss_ratio, 4),
            long_short_spread=0.0,
            max_drawdown_duration=max_dd_duration,
            skewness=0.0,
            kurtosis=0.0,
        )

    # ------------------------------------------------------------------
    # Legacy wrapper
    # ------------------------------------------------------------------

    @staticmethod
    def compute_legacy(
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray,
        risk_free_rate: float = 0.0,
    ) -> BacktestMetrics:
        """Backward-compatible wrapper around the original compute_metrics()."""
        return compute_metrics(portfolio_returns, benchmark_returns, risk_free_rate)
