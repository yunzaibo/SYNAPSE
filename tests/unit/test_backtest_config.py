import pytest

from synapse.backtest.config import BacktestConfig


def test_create_config_with_explicit_costs():
    config = BacktestConfig(
        universe="sample-equity",
        benchmark="benchmark-sp500",
        start_date="2020-01-01",
        end_date="2023-12-31",
        rebalance_frequency="monthly",
        transaction_cost_bps=5.0,
        slippage_bps=2.0,
    )
    assert config.universe == "sample-equity"
    assert config.transaction_cost_bps == 5.0
    assert config.slippage_bps == 2.0
    assert config.position_limit == 1.0  # default


def test_create_config_with_position_limit():
    config = BacktestConfig(
        universe="us-equity",
        benchmark="sp500",
        start_date="2020-01-01",
        end_date="2023-12-31",
        rebalance_frequency="weekly",
        transaction_cost_bps=10.0,
        slippage_bps=3.0,
        position_limit=0.2,
    )
    assert config.position_limit == 0.2


def test_config_rejects_none_transaction_cost():
    with pytest.raises(ValueError, match="transaction_cost_bps must be explicitly set"):
        BacktestConfig(
            universe="sample",
            benchmark="bench",
            start_date="2020-01-01",
            end_date="2023-12-31",
            rebalance_frequency="monthly",
            transaction_cost_bps=None,
            slippage_bps=2.0,
        )


def test_config_rejects_none_slippage():
    with pytest.raises(ValueError, match="slippage_bps must be explicitly set"):
        BacktestConfig(
            universe="sample",
            benchmark="bench",
            start_date="2020-01-01",
            end_date="2023-12-31",
            rebalance_frequency="monthly",
            transaction_cost_bps=5.0,
            slippage_bps=None,
        )
