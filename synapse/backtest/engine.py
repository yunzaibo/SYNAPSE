from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from synapse.backtest.config import BacktestConfig
from synapse.backtest.metrics import compute_metrics, BacktestMetrics


@dataclass
class BacktestResult:
    config: BacktestConfig
    metrics: BacktestMetrics
    portfolio_returns: list = field(default_factory=list)
    trades: list = field(default_factory=list)
    status: str = "running"  # running | succeeded | failed


class BacktestEngine:
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
