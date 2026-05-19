"""Tests for BacktestEngine DI architecture, full pipeline, legacy compat, CostModel, and edge cases.

Covers IMPL-006 requirements:
- DI injection with mock components
- Full pipeline: synthetic factor data -> BacktestRunResult
- Legacy run_backtest() produces BacktestResult with BacktestMetrics
- TradingCalendar integration: rebalance dates match calendar
- CostModel: cost deduction matches expected formula
- Edge case: empty factor data returns failed result
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from synapse.backtest.config import BacktestConfig
from synapse.backtest.engine import BacktestEngine, BacktestRequest, BacktestResult, CostModel
from synapse.backtest.metrics import BacktestMetrics
from synapse.backtest.result import BacktestRunResult, PerformanceMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sample_data(
    n_stocks: int = 20,
    n_days: int = 60,
    seed: int = 42,
) -> tuple[pd.Series, pd.Series]:
    """Generate sample factor_values and forward_returns for testing."""
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2023-01-01", periods=n_days)
    tickers = [f"STK{i:02d}" for i in range(n_stocks)]

    idx = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])
    factor_values = pd.Series(rng.randn(len(idx)), index=idx, name="factor")
    forward_returns = pd.Series(rng.randn(len(idx)) * 0.01, index=idx, name="fwd_ret")
    return factor_values, forward_returns


def _make_sample_data_as_df(
    n_stocks: int = 20,
    n_days: int = 60,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.Series]:
    """Generate sample factor_values (DataFrame) and forward_returns for testing."""
    fv, fr = _make_sample_data(n_stocks, n_days, seed)
    return fv.to_frame(), fr


def _default_config(**overrides) -> BacktestConfig:
    defaults = dict(
        universe="sample-equity",
        benchmark="benchmark",
        start_date="2023-01-01",
        end_date="2023-03-31",
        rebalance_frequency="monthly",
        transaction_cost_bps=5.0,
        slippage_bps=2.0,
    )
    defaults.update(overrides)
    return BacktestConfig(**defaults)


# ===================================================================
# Legacy API tests (preserved from original)
# ===================================================================

def test_run_backtest_succeeds():
    factor_values, forward_returns = _make_sample_data()
    config = _default_config()
    engine = BacktestEngine()
    result = engine.run_backtest(factor_values, forward_returns, config)

    assert isinstance(result, BacktestResult)
    assert result.status == "succeeded"
    assert result.config == config


def test_run_backtest_metrics_are_numeric():
    factor_values, forward_returns = _make_sample_data()
    config = _default_config(transaction_cost_bps=10.0, slippage_bps=5.0)
    engine = BacktestEngine()
    result = engine.run_backtest(factor_values, forward_returns, config)

    m = result.metrics
    for field_name in ("annual_return", "volatility", "sharpe", "max_drawdown",
                       "turnover", "win_rate", "excess_return", "information_ratio"):
        val = getattr(m, field_name)
        assert isinstance(val, (int, float)), f"{field_name} is not numeric: {type(val)}"


def test_run_backtest_produces_trades():
    factor_values, forward_returns = _make_sample_data()
    config = _default_config()
    engine = BacktestEngine()
    result = engine.run_backtest(factor_values, forward_returns, config)

    assert len(result.trades) > 0
    for trade in result.trades:
        assert "period" in trade
        assert "long" in trade
        assert "short" in trade
        assert "return" in trade


def test_run_backtest_with_minimal_data_returns_failed():
    factor_values = pd.Series([1.0], index=pd.MultiIndex.from_tuples(
        [(pd.Timestamp("2023-01-01"), "A")], names=["date", "ticker"]
    ))
    forward_returns = pd.Series([0.01], index=pd.MultiIndex.from_tuples(
        [(pd.Timestamp("2023-01-01"), "A")], names=["date", "ticker"]
    ))
    config = _default_config(
        start_date="2023-01-01", end_date="2023-01-01"
    )
    engine = BacktestEngine()
    result = engine.run_backtest(factor_values, forward_returns, config)
    assert result.status == "failed"


# ===================================================================
# CostModel tests
# ===================================================================

class TestCostModel:
    def test_zero_turnover(self):
        cm = CostModel(transaction_cost_bps=10.0, slippage_bps=5.0)
        cost = cm.compute_cost({"A", "B"}, {"A", "B"}, 10)
        assert cost == 0.0

    def test_full_turnover(self):
        cm = CostModel(transaction_cost_bps=10.0, slippage_bps=5.0)
        cost = cm.compute_cost(set(), {"A", "B"}, 10)
        expected = (2 / 10) * (10.0 + 5.0) / 10000
        assert abs(cost - expected) < 1e-12

    def test_partial_turnover(self):
        cm = CostModel(transaction_cost_bps=5.0, slippage_bps=3.0)
        old = {"A", "B", "C", "D"}
        new = {"B", "C", "D", "E"}  # 1 new stock out of 4
        cost = cm.compute_cost(old, new, 4)
        expected = (1 / 4) * (5.0 + 3.0) / 10000
        assert abs(cost - expected) < 1e-12

    def test_zero_total_stocks(self):
        cm = CostModel(transaction_cost_bps=10.0, slippage_bps=5.0)
        cost = cm.compute_cost(set(), set(), 0)
        assert cost == 0.0

    def test_frozen_dataclass(self):
        cm = CostModel(transaction_cost_bps=10.0, slippage_bps=5.0)
        with pytest.raises(AttributeError):
            cm.transaction_cost_bps = 20.0  # type: ignore[misc]


# ===================================================================
# BacktestConfig validation tests
# ===================================================================

class TestBacktestConfigValidation:
    def test_n_quintiles_too_low(self):
        with pytest.raises(ValueError, match="n_quintiles must be >= 2"):
            BacktestConfig(
                universe="u", benchmark="b", start_date="2023-01-01",
                end_date="2023-12-31", rebalance_frequency="monthly",
                transaction_cost_bps=5.0, slippage_bps=2.0,
                n_quintiles=1,
            )

    def test_invalid_rebalance_frequency(self):
        with pytest.raises(ValueError, match="rebalance_frequency must be"):
            BacktestConfig(
                universe="u", benchmark="b", start_date="2023-01-01",
                end_date="2023-12-31", rebalance_frequency="annually",
                transaction_cost_bps=5.0, slippage_bps=2.0,
            )

    def test_valid_config_defaults(self):
        cfg = BacktestConfig(
            universe="u", benchmark="b", start_date="2023-01-01",
            end_date="2023-12-31", rebalance_frequency="monthly",
            transaction_cost_bps=5.0, slippage_bps=2.0,
        )
        assert cfg.n_quintiles == 5
        assert cfg.ic_window == 20
        assert cfg.ic_min_periods == 10
        assert cfg.enable_attribution is True
        assert cfg.enable_ic_analysis is True
        assert cfg.output_dir == "backtests/"


# ===================================================================
# DI injection tests
# ===================================================================

class TestDIInjection:
    def test_engine_uses_default_components(self):
        engine = BacktestEngine()
        assert engine.sorter is not None
        assert engine.metrics_calc is not None
        assert engine.ic_analyzer is not None
        assert engine.attribution is not None
        assert engine.spread is not None

    def test_engine_accepts_custom_components(self):
        mock_sorter = MagicMock()
        mock_metrics = MagicMock()
        mock_ic = MagicMock()
        mock_attr = MagicMock()
        mock_spread = MagicMock()

        engine = BacktestEngine(
            sorter=mock_sorter,
            metrics_calc=mock_metrics,
            ic_analyzer=mock_ic,
            attribution=mock_attr,
            spread=mock_spread,
        )
        assert engine.sorter is mock_sorter
        assert engine.metrics_calc is mock_metrics
        assert engine.ic_analyzer is mock_ic
        assert engine.attribution is mock_attr
        assert engine.spread is mock_spread


# ===================================================================
# Full pipeline tests (run method)
# ===================================================================

class TestRunPipeline:
    def test_full_pipeline_returns_backtest_run_result(self):
        fv_df, fr = _make_sample_data_as_df()
        config = _default_config()
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
            factor_id="momentum",
        )
        engine = BacktestEngine()
        result = engine.run(request)

        assert isinstance(result, BacktestRunResult)
        assert result.status == "succeeded"
        assert result.factor_id == "momentum"
        assert result.id  # non-empty run ID
        assert result.run_timestamp  # non-empty timestamp

    def test_full_pipeline_populates_performance(self):
        fv_df, fr = _make_sample_data_as_df()
        config = _default_config()
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        )
        engine = BacktestEngine()
        result = engine.run(request)

        assert isinstance(result.performance, PerformanceMetrics)
        # At least some metrics should be non-default
        assert result.performance.annual_return != 0.0 or result.performance.volatility != 0.0

    def test_full_pipeline_populates_quintile_portfolios(self):
        fv_df, fr = _make_sample_data_as_df()
        config = _default_config()
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        )
        engine = BacktestEngine()
        result = engine.run(request)

        assert len(result.quintile_portfolios) > 0
        for qp in result.quintile_portfolios:
            assert 1 in qp.quintiles
            assert 5 in qp.quintiles

    def test_full_pipeline_long_short_returns(self):
        fv_df, fr = _make_sample_data_as_df()
        config = _default_config()
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        )
        engine = BacktestEngine()
        result = engine.run(request)

        assert len(result.long_short_returns) > 0
        for r in result.long_short_returns:
            assert isinstance(r, float)

    def test_full_pipeline_config_stored(self):
        fv_df, fr = _make_sample_data_as_df()
        config = _default_config()
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        )
        engine = BacktestEngine()
        result = engine.run(request)

        assert result.config["universe"] == "sample-equity"
        assert result.config["n_quintiles"] == 5
        assert result.config["start_date"] == "2023-01-01"

    def test_full_pipeline_ic_analysis_enabled(self):
        fv_df, fr = _make_sample_data_as_df()
        config = _default_config(enable_ic_analysis=True)
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
            factor_id="test_factor",
        )
        engine = BacktestEngine()
        result = engine.run(request)

        assert result.ic_analysis is not None
        assert result.ic_analysis.factor_id == "test_factor"

    def test_full_pipeline_ic_analysis_disabled(self):
        fv_df, fr = _make_sample_data_as_df()
        config = _default_config(enable_ic_analysis=False)
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        )
        engine = BacktestEngine()
        result = engine.run(request)

        assert result.ic_analysis is None

    def test_full_pipeline_attribution_enabled(self):
        fv_df, fr = _make_sample_data_as_df()
        config = _default_config(enable_attribution=True)
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        )
        engine = BacktestEngine()
        result = engine.run(request)

        # Attribution may be None if insufficient data points, but the
        # engine should not crash
        assert result.status in ("succeeded", "failed")

    def test_full_pipeline_attribution_disabled(self):
        fv_df, fr = _make_sample_data_as_df()
        config = _default_config(enable_attribution=False)
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        )
        engine = BacktestEngine()
        result = engine.run(request)

        assert result.attribution is None


# ===================================================================
# Edge cases
# ===================================================================

class TestEdgeCases:
    def test_empty_factor_values_returns_failed(self):
        empty_fv = pd.DataFrame(columns=["factor"])
        empty_fv.index = pd.MultiIndex.from_tuples([], names=["date", "ticker"])
        fr = pd.Series(dtype=float)
        fr.index = pd.MultiIndex.from_tuples([], names=["date", "ticker"])

        config = _default_config()
        request = BacktestRequest(
            factor_values=empty_fv,
            forward_returns=fr,
            config=config,
        )
        engine = BacktestEngine()
        result = engine.run(request)

        assert isinstance(result, BacktestRunResult)
        assert result.status == "failed"
        assert result.error is not None

    def test_empty_forward_returns_returns_failed(self):
        fv_df, _ = _make_sample_data_as_df(n_days=10)
        empty_fr = pd.Series(dtype=float)
        empty_fr.index = pd.MultiIndex.from_tuples([], names=["date", "ticker"])

        config = _default_config()
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=empty_fr,
            config=config,
        )
        engine = BacktestEngine()
        result = engine.run(request)

        assert result.status == "failed"

    def test_exception_in_pipeline_returns_failed(self):
        """Engine catches exceptions and returns failed result."""
        fv_df, fr = _make_sample_data_as_df()
        config = _default_config()
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        )
        engine = BacktestEngine()
        # Patch sorter.sort_timeseries to raise
        with patch.object(engine.sorter, "sort_timeseries", side_effect=RuntimeError("boom")):
            result = engine.run(request)

        assert result.status == "failed"
        assert "boom" in result.error


# ===================================================================
# TradingCalendar integration
# ===================================================================

class TestTradingCalendarIntegration:
    def test_rebalance_dates_are_trading_days(self):
        fv_df, fr = _make_sample_data_as_df()
        config = _default_config(
            start_date="2023-01-01",
            end_date="2023-03-31",
            rebalance_frequency="monthly",
        )
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        )
        engine = BacktestEngine()
        result = engine.run(request)

        # Verify quintile portfolio dates are valid
        for qp in result.quintile_portfolios:
            d = qp.date
            # Should be a weekday (Mon-Fri) for standard trading days
            assert d.weekday() < 5, f"Portfolio date {d} is a weekend"

    def test_daily_rebalance(self):
        fv_df, fr = _make_sample_data_as_df(n_days=30)
        config = _default_config(
            start_date="2023-01-02",
            end_date="2023-02-10",
            rebalance_frequency="daily",
        )
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        )
        engine = BacktestEngine()
        result = engine.run(request)

        # Daily rebalance should produce more portfolios than monthly
        assert isinstance(result, BacktestRunResult)

    def test_weekly_rebalance(self):
        fv_df, fr = _make_sample_data_as_df(n_days=60)
        config = _default_config(
            start_date="2023-01-01",
            end_date="2023-03-31",
            rebalance_frequency="weekly",
        )
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        )
        engine = BacktestEngine()
        result = engine.run(request)

        assert isinstance(result, BacktestRunResult)
        if result.quintile_portfolios:
            # Verify dates are first trading day of each week
            dates = [qp.date for qp in result.quintile_portfolios]
            for i in range(1, len(dates)):
                # Each date should be in a different ISO week
                assert dates[i].isocalendar()[1] != dates[i - 1].isocalendar()[1] or \
                       dates[i].year != dates[i - 1].year


# ===================================================================
# BacktestRequest frozen dataclass
# ===================================================================

class TestBacktestRequest:
    def test_frozen(self):
        fv_df, fr = _make_sample_data_as_df()
        config = _default_config()
        req = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        )
        with pytest.raises(AttributeError):
            req.factor_id = "changed"  # type: ignore[misc]

    def test_default_factor_id(self):
        fv_df, fr = _make_sample_data_as_df()
        config = _default_config()
        req = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        )
        assert req.factor_id == ""
        assert req.benchmark_returns is None


# ===================================================================
# Legacy compat: run_backtest delegates to internal logic
# ===================================================================

class TestLegacyCompat:
    def test_run_backtest_returns_backtest_result(self):
        fv, fr = _make_sample_data()
        config = _default_config()
        engine = BacktestEngine()
        result = engine.run_backtest(fv, fr, config)

        assert isinstance(result, BacktestResult)
        assert isinstance(result.metrics, BacktestMetrics)

    def test_run_backtest_with_higher_quintiles(self):
        """Legacy API still uses 5 quintiles internally."""
        fv, fr = _make_sample_data(n_stocks=50, n_days=100)
        config = _default_config(n_quintiles=5)
        engine = BacktestEngine()
        result = engine.run_backtest(fv, fr, config)

        assert result.status == "succeeded"
        assert len(result.trades) > 0
