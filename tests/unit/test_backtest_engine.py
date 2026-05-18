import numpy as np
import pandas as pd

from synapse.backtest.config import BacktestConfig
from synapse.backtest.engine import BacktestEngine, BacktestResult


def _make_sample_data(n_stocks: int = 20, n_days: int = 60):
    """Generate sample factor_values and forward_returns for testing."""
    rng = np.random.RandomState(42)
    dates = pd.bdate_range("2023-01-01", periods=n_days)
    tickers = [f"STK{i:02d}" for i in range(n_stocks)]

    # Build a multi-index DataFrame
    idx = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])
    factor_values = pd.Series(rng.randn(len(idx)), index=idx, name="factor")
    forward_returns = pd.Series(rng.randn(len(idx)) * 0.01, index=idx, name="fwd_ret")
    return factor_values, forward_returns


def test_run_backtest_succeeds():
    factor_values, forward_returns = _make_sample_data()
    config = BacktestConfig(
        universe="sample-equity",
        benchmark="benchmark",
        start_date="2023-01-01",
        end_date="2023-03-31",
        rebalance_frequency="monthly",
        transaction_cost_bps=5.0,
        slippage_bps=2.0,
    )
    engine = BacktestEngine()
    result = engine.run_backtest(factor_values, forward_returns, config)

    assert isinstance(result, BacktestResult)
    assert result.status == "succeeded"
    assert result.config == config


def test_run_backtest_metrics_are_numeric():
    factor_values, forward_returns = _make_sample_data()
    config = BacktestConfig(
        universe="sample",
        benchmark="bench",
        start_date="2023-01-01",
        end_date="2023-03-31",
        rebalance_frequency="monthly",
        transaction_cost_bps=10.0,
        slippage_bps=5.0,
    )
    engine = BacktestEngine()
    result = engine.run_backtest(factor_values, forward_returns, config)

    m = result.metrics
    for field_name in ("annual_return", "volatility", "sharpe", "max_drawdown",
                       "turnover", "win_rate", "excess_return", "information_ratio"):
        val = getattr(m, field_name)
        assert isinstance(val, (int, float)), f"{field_name} is not numeric: {type(val)}"


def test_run_backtest_produces_trades():
    factor_values, forward_returns = _make_sample_data()
    config = BacktestConfig(
        universe="sample",
        benchmark="bench",
        start_date="2023-01-01",
        end_date="2023-03-31",
        rebalance_frequency="monthly",
        transaction_cost_bps=5.0,
        slippage_bps=2.0,
    )
    engine = BacktestEngine()
    result = engine.run_backtest(factor_values, forward_returns, config)

    assert len(result.trades) > 0
    for trade in result.trades:
        assert "period" in trade
        assert "long" in trade
        assert "short" in trade
        assert "return" in trade


def test_run_backtest_with_minimal_data_returns_failed():
    # Less than 2 aligned rows -> should fail
    factor_values = pd.Series([1.0], index=pd.MultiIndex.from_tuples(
        [(pd.Timestamp("2023-01-01"), "A")], names=["date", "ticker"]
    ))
    forward_returns = pd.Series([0.01], index=pd.MultiIndex.from_tuples(
        [(pd.Timestamp("2023-01-01"), "A")], names=["date", "ticker"]
    ))
    config = BacktestConfig(
        universe="sample",
        benchmark="bench",
        start_date="2023-01-01",
        end_date="2023-01-01",
        rebalance_frequency="monthly",
        transaction_cost_bps=5.0,
        slippage_bps=2.0,
    )
    engine = BacktestEngine()
    result = engine.run_backtest(factor_values, forward_returns, config)
    assert result.status == "failed"
