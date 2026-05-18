import numpy as np

from synapse.backtest.metrics import compute_metrics, BacktestMetrics


def test_compute_metrics_known_data():
    # Positive constant returns -> positive Sharpe, positive annual return
    returns = np.full(252, 0.0005)
    metrics = compute_metrics(returns, np.zeros(252))

    assert isinstance(metrics, BacktestMetrics)
    assert metrics.annual_return > 0
    assert metrics.volatility == 0.0  # constant returns have zero volatility
    assert metrics.sharpe == 0.0  # zero std -> defined as 0 by our impl
    assert metrics.max_drawdown == 0.0
    assert metrics.win_rate == 1.0


def test_compute_metrics_negative_returns():
    returns = np.full(252, -0.001)
    metrics = compute_metrics(returns, np.zeros(252))

    assert metrics.annual_return < 0
    assert metrics.win_rate == 0.0
    assert metrics.max_drawdown < 0


def test_compute_metrics_mixed_returns():
    rng = np.random.RandomState(123)
    returns = rng.randn(252) * 0.01
    benchmark = rng.randn(252) * 0.005
    metrics = compute_metrics(returns, benchmark)

    # Sharpe should be a finite number
    assert np.isfinite(metrics.sharpe)
    assert np.isfinite(metrics.information_ratio)

    # Win rate between 0 and 1
    assert 0.0 <= metrics.win_rate <= 1.0

    # Max drawdown should be <= 0
    assert metrics.max_drawdown <= 0.0

    # Volatility should be >= 0
    assert metrics.volatility >= 0.0


def test_compute_metrics_empty_array():
    metrics = compute_metrics(np.array([]), np.array([]))

    assert metrics.annual_return == 0
    assert metrics.volatility == 0
    assert metrics.sharpe == 0
    assert metrics.max_drawdown == 0
    assert metrics.turnover == 0
    assert metrics.win_rate == 0
    assert metrics.excess_return == 0
    assert metrics.information_ratio == 0


def test_compute_metrics_with_risk_free_rate():
    returns = np.full(252, 0.001)
    benchmark = np.zeros(252)

    metrics_with_rf = compute_metrics(returns, benchmark, risk_free_rate=0.02)
    metrics_no_rf = compute_metrics(returns, benchmark, risk_free_rate=0.0)

    # With positive risk-free rate, Sharpe should be lower (excess return is smaller)
    assert metrics_with_rf.sharpe <= metrics_no_rf.sharpe


def test_sharpe_and_drawdown_ranges():
    """Verify metrics are within expected physical ranges."""
    rng = np.random.RandomState(42)
    returns = rng.randn(504) * 0.015  # ~2 years of daily returns
    benchmark = rng.randn(504) * 0.01
    metrics = compute_metrics(returns, benchmark)

    # Sharpe typically between -5 and 5 for normal data
    assert -10 < metrics.sharpe < 10

    # Max drawdown between -1 and 0
    assert -1.0 <= metrics.max_drawdown <= 0.0

    # Win rate between 0 and 1
    assert 0.0 <= metrics.win_rate <= 1.0
