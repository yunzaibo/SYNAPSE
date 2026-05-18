from dataclasses import dataclass

import numpy as np


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
