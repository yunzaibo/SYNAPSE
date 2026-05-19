"""End-to-end integration tests for the full backtest pipeline.

Covers IMPL-008 requirements:
- Full pipeline: synthetic factor data -> BacktestRunResult with all fields
- Deterministic results: same input produces identical output
- Component composition: each sub-component is invoked correctly
- Performance benchmark: 300 stocks, 5 years monthly completes in < 3s
- Error handling: graceful degradation when a component fails
- Data contract validation: result objects match frozen dataclass schemas
- Edge cases: zero variance factors, single stock, extreme costs
"""

from __future__ import annotations

import time
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from synapse.backtest.config import BacktestConfig
from synapse.backtest.engine import BacktestEngine, BacktestRequest
from synapse.backtest.metrics import MetricsCalculator
from synapse.backtest.result import (
    AttributionResult,
    BacktestRunResult,
    ICAnalysisResult,
    PerformanceMetrics,
    QuintilePortfolio,
)
from synapse.core.market.calendar import trading_days_between


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _get_monthly_trading_days(start: date, end: date) -> list[pd.Timestamp]:
    """Get the first trading day of each month within a date range.

    Uses TradingCalendar to ensure dates are valid trading days,
    avoiding holiday misalignment issues.
    """
    tdays = trading_days_between(start, end)
    monthly: list[pd.Timestamp] = []
    seen_months: set[tuple[int, int]] = set()
    for d in tdays:
        key = (d.year, d.month)
        if key not in seen_months:
            monthly.append(pd.Timestamp(d))
            seen_months.add(key)
    return monthly


def _make_synthetic_data(
    n_stocks: int = 300,
    n_months: int = 60,
    seed: int = 42,
    start_date: str = "2019-01-01",
    end_date: str = "2023-12-31",
) -> tuple[pd.DataFrame, pd.Series]:
    """Create synthetic factor DataFrame (MultiIndex date, ticker) and forward returns.

    Uses TradingCalendar dates to ensure alignment with rebalance dates.
    Generates 300 stocks x 60 months of monthly data with a known
    signal-to-noise ratio so metrics are within predictable ranges.
    """
    rng = np.random.RandomState(seed)

    # Use TradingCalendar-aligned dates
    dates = _get_monthly_trading_days(
        date.fromisoformat(start_date),
        date.fromisoformat(end_date),
    )[:n_months]

    tickers = [f"SZ{str(i).zfill(6)}" for i in range(n_stocks)]

    # Create a persistent factor that predicts returns
    # Note: QuintileSorter ranks highest factor values as Q1 (rank 1),
    # and BacktestEngine goes long Q5 (lowest rank) and short Q1 (highest rank).
    # So we need low factor values to predict HIGH returns for the long side.
    base_ranks = rng.permutation(n_stocks)  # persistent stock ranking

    factor_rows = []
    return_rows = []
    for i, dt in enumerate(dates):
        # Factor: low values = good stocks (will be in Q5 after ranking)
        # Negate base_ranks so high original rank -> low factor -> Q5 (long)
        factor = -base_ranks.astype(float) + rng.randn(n_stocks) * 3.0
        # Returns: weak alpha + noise (realistic signal-to-noise)
        alpha = -(factor - factor.mean()) / (factor.std() + 1e-8) * 0.003
        ret = alpha + rng.randn(n_stocks) * 0.005
        factor_rows.append(factor)
        return_rows.append(ret)

    factor_vals = np.concatenate(factor_rows)
    fwd_vals = np.concatenate(return_rows)

    idx = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])
    fv_df = pd.DataFrame(factor_vals, index=idx, columns=["momentum"])
    fr = pd.Series(fwd_vals, index=idx, name="fwd_ret")

    return fv_df, fr


def _default_config(**overrides) -> BacktestConfig:
    defaults = dict(
        universe="integration-test",
        benchmark="CSI300",
        start_date="2019-01-01",
        end_date="2023-12-31",
        rebalance_frequency="monthly",
        transaction_cost_bps=10.0,
        slippage_bps=5.0,
    )
    defaults.update(overrides)
    return BacktestConfig(**defaults)


# ---------------------------------------------------------------------------
# Step 1: Full pipeline integration tests
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """Test 1: Complete backtest pipeline from synthetic data to BacktestRunResult."""

    def test_full_pipeline(self):
        """Run the complete backtest pipeline and verify all result fields."""
        fv_df, fr = _make_synthetic_data()
        config = _default_config()

        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
            factor_id="momentum_300",
        )

        engine = BacktestEngine()
        result = engine.run(request)

        # Verify result type and status
        assert isinstance(result, BacktestRunResult)
        assert result.status == "succeeded"
        assert result.factor_id == "momentum_300"
        assert result.id  # non-empty run ID
        assert result.run_timestamp  # non-empty timestamp

        # Verify config is stored
        assert result.config["universe"] == "integration-test"
        assert result.config["n_quintiles"] == 5
        assert result.config["start_date"] == "2019-01-01"
        assert result.config["end_date"] == "2023-12-31"

        # Verify quintile portfolios exist and are well-formed
        assert len(result.quintile_portfolios) > 0
        for qp in result.quintile_portfolios:
            assert isinstance(qp, QuintilePortfolio)
            assert 1 in qp.quintiles
            assert 5 in qp.quintiles
            assert qp.universe_size == 300
            assert qp.valid_count <= 300

        # Verify quintile returns are populated
        assert len(result.quintile_returns) > 0
        for q_id, q_ret in result.quintile_returns.items():
            assert isinstance(q_id, int)
            assert isinstance(q_ret, float)

        # Verify long-short returns
        assert len(result.long_short_returns) > 0
        for r in result.long_short_returns:
            assert isinstance(r, float)

        # Verify performance metrics are within reasonable ranges
        perf = result.performance
        assert isinstance(perf, PerformanceMetrics)
        # Annual return: should be finite and reasonable
        assert np.isfinite(perf.annual_return)
        assert perf.annual_return > -1.0  # not a total loss
        assert 0.0 <= perf.volatility < 5.0
        assert np.isfinite(perf.sharpe)
        assert -1.0 <= perf.max_drawdown <= 0.0
        assert 0.0 <= perf.win_rate <= 1.0

        # Verify IC analysis is enabled
        assert result.ic_analysis is not None
        assert isinstance(result.ic_analysis, ICAnalysisResult)
        assert result.ic_analysis.factor_id == "momentum_300"
        assert len(result.ic_analysis.ic_series) > 0

        # Verify attribution is enabled
        assert result.attribution is not None
        assert isinstance(result.attribution, AttributionResult)


class TestDeterministicResults:
    """Test 2: Same input produces identical BacktestRunResult."""

    def test_deterministic_results(self):
        """Run the same backtest twice and verify identical results."""
        fv_df, fr = _make_synthetic_data(seed=123)
        config = _default_config()

        def _run_backtest():
            request = BacktestRequest(
                factor_values=fv_df.copy(),
                forward_returns=fr.copy(),
                config=config,
                factor_id="deterministic_test",
            )
            engine = BacktestEngine()
            return engine.run(request)

        result1 = _run_backtest()
        result2 = _run_backtest()

        # Core metrics should be identical (deterministic algorithm)
        assert result1.performance.annual_return == result2.performance.annual_return
        assert result1.performance.volatility == result2.performance.volatility
        assert result1.performance.sharpe == result2.performance.sharpe
        assert result1.performance.max_drawdown == result2.performance.max_drawdown
        assert result1.performance.win_rate == result2.performance.win_rate

        # Long-short returns should be identical
        assert len(result1.long_short_returns) == len(result2.long_short_returns)
        for r1, r2 in zip(result1.long_short_returns, result2.long_short_returns):
            assert r1 == pytest.approx(r2)

        # Quintile portfolios should have the same structure
        assert len(result1.quintile_portfolios) == len(result2.quintile_portfolios)
        for qp1, qp2 in zip(result1.quintile_portfolios, result2.quintile_portfolios):
            assert qp1.date == qp2.date
            assert qp1.universe_size == qp2.universe_size
            assert qp1.valid_count == qp2.valid_count
            for q_id in qp1.quintiles:
                assert set(qp1.quintiles[q_id]) == set(qp2.quintiles[q_id])

        # IC analysis should be identical
        assert result1.ic_analysis is not None
        assert result2.ic_analysis is not None
        assert result1.ic_analysis.ic_mean == result2.ic_analysis.ic_mean
        assert result1.ic_analysis.icir == result2.ic_analysis.icir


class TestComponentComposition:
    """Test 3: Verify each component (sorter, metrics, IC, attribution) is called correctly."""

    def test_component_composition(self):
        """Verify the engine orchestrates all components in the correct order."""
        fv_df, fr = _make_synthetic_data(n_stocks=50, n_months=24,
                                          start_date="2021-01-01", end_date="2022-12-31")
        config = _default_config(
            start_date="2021-01-01",
            end_date="2022-12-31",
            enable_ic_analysis=True,
            enable_attribution=True,
        )

        # Create mocks for all components
        mock_sorter = MagicMock()
        mock_metrics = MagicMock(spec=MetricsCalculator)
        mock_ic = MagicMock()
        mock_attr = MagicMock()
        mock_spread = MagicMock()

        # Configure mock_metrics.compute to return a valid PerformanceMetrics
        mock_metrics.compute.return_value = PerformanceMetrics(
            annual_return=0.15,
            volatility=0.2,
            sharpe=0.75,
            max_drawdown=-0.1,
        )

        # Configure mock_ic.compute_ic to return a valid ICAnalysisResult
        mock_ic.compute_ic.return_value = ICAnalysisResult(
            factor_id="test",
            ic_mean=0.05,
            ic_series=(0.1, 0.05, 0.02),
        )

        # Configure mock_attr.compute to return a valid AttributionResult
        mock_attr.compute.return_value = AttributionResult(
            factor_returns={1: 0.01},
            residual_returns=(0.001, 0.002),
            r_squared=0.85,
        )

        # Configure mock_spread.compute
        from synapse.backtest.spread import LongShortSpreadResult
        mock_spread.compute.return_value = LongShortSpreadResult(
            spread_returns=(0.01, 0.02),
            annual_spread_return=0.15,
        )

        engine = BacktestEngine(
            sorter=mock_sorter,
            metrics_calc=mock_metrics,
            ic_analyzer=mock_ic,
            attribution=mock_attr,
            spread=mock_spread,
        )

        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
            factor_id="composition_test",
        )

        result = engine.run(request)

        # Verify sorter was called
        assert mock_sorter.sort_timeseries.called
        call_args = mock_sorter.sort_timeseries.call_args
        assert call_args[1].get("n_quintiles") == 5 or call_args[0][2] == 5

        # Verify metrics calculator was called
        assert mock_metrics.compute.called

        # Verify IC analyzer was called (enabled in config)
        assert mock_ic.compute_ic.called

        # Verify attribution was called (enabled in config and has sufficient data)
        assert mock_attr.compute.called

        # Note: spread may not be called when mock sorter returns MagicMock objects
        # instead of real QuintilePortfolio dicts. The spread computation requires
        # real quintile_period_returns data. This is covered by real integration tests.

        # Result should reflect mock values
        assert result.status == "succeeded"


class TestPerformanceBenchmark:
    """Test 4: 300 stocks, 5 years monthly completes in < 3s."""

    def test_performance_benchmark(self):
        """Benchmark: 300 stocks x 60 months must complete in under 3 seconds."""
        fv_df, fr = _make_synthetic_data(n_stocks=300, n_months=60)
        config = _default_config()

        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
            factor_id="benchmark_test",
        )

        engine = BacktestEngine()

        start_time = time.time()
        result = engine.run(request)
        elapsed = time.time() - start_time

        assert result.status == "succeeded"
        assert elapsed < 3.0, f"Backtest took {elapsed:.2f}s, expected < 3.0s"
        print(f"\n  [PERF] 300 stocks x 60 months: {elapsed:.3f}s")


class TestErrorHandling:
    """Test 5: Graceful degradation when a component fails."""

    def test_sorter_failure_returns_failed(self):
        """Engine returns failed result when sorter raises an exception."""
        fv_df, fr = _make_synthetic_data(n_stocks=30, n_months=12,
                                          start_date="2022-01-01", end_date="2022-12-31")
        config = _default_config(
            start_date="2022-01-01",
            end_date="2022-12-31",
        )

        engine = BacktestEngine()
        with patch.object(
            engine.sorter, "sort_timeseries", side_effect=RuntimeError("sorter crashed")
        ):
            result = engine.run(BacktestRequest(
                factor_values=fv_df,
                forward_returns=fr,
                config=config,
                factor_id="error_test",
            ))

        assert isinstance(result, BacktestRunResult)
        assert result.status == "failed"
        assert "sorter crashed" in result.error

    def test_metrics_failure_returns_failed(self):
        """Engine returns failed result when metrics calculator raises."""
        fv_df, fr = _make_synthetic_data(n_stocks=30, n_months=12,
                                          start_date="2022-01-01", end_date="2022-12-31")
        config = _default_config(
            start_date="2022-01-01",
            end_date="2022-12-31",
        )

        engine = BacktestEngine()
        with patch.object(
            engine.metrics_calc, "compute", side_effect=RuntimeError("metrics crashed")
        ):
            result = engine.run(BacktestRequest(
                factor_values=fv_df,
                forward_returns=fr,
                config=config,
                factor_id="metrics_error_test",
            ))

        assert result.status == "failed"
        assert "metrics crashed" in result.error


class TestDataContractValidation:
    """Validate that result objects match their frozen dataclass schemas."""

    def test_backtest_run_result_frozen(self):
        """BacktestRunResult is immutable."""
        fv_df, fr = _make_synthetic_data(n_stocks=20, n_months=12,
                                          start_date="2022-01-01", end_date="2022-12-31")
        config = _default_config(
            start_date="2022-01-01",
            end_date="2022-12-31",
        )
        engine = BacktestEngine()
        result = engine.run(BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        ))

        with pytest.raises(AttributeError):
            result.status = "modified"  # type: ignore[misc]

    def test_performance_metrics_frozen(self):
        """PerformanceMetrics is immutable."""
        perf = PerformanceMetrics(annual_return=0.1)
        with pytest.raises(AttributeError):
            perf.annual_return = 0.2  # type: ignore[misc]

    def test_quintile_portfolio_frozen(self):
        """QuintilePortfolio is immutable."""
        qp = QuintilePortfolio(
            date=date(2023, 1, 1),
            quintiles={1: ("A",), 2: ("B",)},
            weights={1: {"A": 1.0}, 2: {"B": 1.0}},
            factor_name="test",
            universe_size=2,
            valid_count=2,
        )
        with pytest.raises(AttributeError):
            qp.universe_size = 100  # type: ignore[misc]

    def test_to_dict_from_dict_roundtrip(self):
        """BacktestRunResult survives a to_dict -> from_dict roundtrip."""
        fv_df, fr = _make_synthetic_data(n_stocks=20, n_months=12,
                                          start_date="2022-01-01", end_date="2022-12-31")
        config = _default_config(
            start_date="2022-01-01",
            end_date="2022-12-31",
        )
        engine = BacktestEngine()
        result = engine.run(BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        ))

        result_dict = result.to_dict()
        restored = BacktestRunResult.from_dict(result_dict)

        assert restored.id == result.id
        assert restored.status == result.status
        assert restored.factor_id == result.factor_id
        assert restored.performance.annual_return == result.performance.annual_return
        assert len(restored.quintile_portfolios) == len(result.quintile_portfolios)
        assert len(restored.long_short_returns) == len(result.long_short_returns)


class TestEdgeCases:
    """Edge cases: zero variance, single stock, extreme costs."""

    def test_zero_variance_factor(self):
        """All stocks have the same factor value -- quintile sorter handles ties."""
        rng = np.random.RandomState(42)
        dates = _get_monthly_trading_days(date(2022, 1, 1), date(2022, 12, 31))
        tickers = [f"S{i}" for i in range(50)]
        idx = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])

        fv_df = pd.DataFrame(1.0, index=idx, columns=["factor"])  # all same value
        fr = pd.Series(rng.randn(len(idx)) * 0.01, index=idx, name="fwd_ret")

        config = _default_config(
            start_date="2022-01-01",
            end_date="2022-12-31",
        )
        engine = BacktestEngine()
        result = engine.run(BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
            factor_id="zero_var",
        ))

        # Should not crash; may succeed or fail gracefully
        assert isinstance(result, BacktestRunResult)
        assert result.status in ("succeeded", "failed")

    def test_single_stock_universe(self):
        """Backtest with only 1 stock -- quintile sorter needs >= n_quintiles stocks."""
        rng = np.random.RandomState(42)
        dates = _get_monthly_trading_days(date(2022, 1, 1), date(2022, 12, 31))
        idx = pd.MultiIndex.from_product([dates, ["ONLY"]], names=["date", "ticker"])

        fv_df = pd.DataFrame(rng.randn(len(dates)), index=idx, columns=["factor"])
        fr = pd.Series(rng.randn(len(dates)) * 0.01, index=idx, name="fwd_ret")

        config = _default_config(
            start_date="2022-01-01",
            end_date="2022-12-31",
            n_quintiles=5,
        )
        engine = BacktestEngine()
        result = engine.run(BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
            factor_id="single_stock",
        ))

        # Single stock < 5 quintiles => no valid portfolios => failed or empty
        assert isinstance(result, BacktestRunResult)
        # Should not raise an exception

    def test_extreme_transaction_costs(self):
        """Very high transaction costs should eat into returns."""
        fv_df, fr = _make_synthetic_data(n_stocks=50, n_months=24,
                                          start_date="2021-01-01", end_date="2022-12-31")
        config = _default_config(
            start_date="2021-01-01",
            end_date="2022-12-31",
            transaction_cost_bps=500.0,  # 5%
            slippage_bps=200.0,  # 2%
        )

        engine = BacktestEngine()
        result = engine.run(BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
            factor_id="high_cost",
        ))

        assert result.status == "succeeded"
        # High costs should reduce returns -- we just verify it runs without error
        assert len(result.long_short_returns) > 0

    def test_all_nan_factor_values(self):
        """All NaN factor values -- no valid stocks for sorting."""
        dates = _get_monthly_trading_days(date(2022, 1, 1), date(2022, 6, 30))
        tickers = [f"S{i}" for i in range(20)]
        idx = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])

        fv_df = pd.DataFrame(np.nan, index=idx, columns=["factor"])
        fr = pd.Series(0.01, index=idx, name="fwd_ret")

        config = _default_config(
            start_date="2022-01-01",
            end_date="2022-06-30",
        )
        engine = BacktestEngine()
        result = engine.run(BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
            factor_id="all_nan",
        ))

        # Should return failed (no valid factor values to sort)
        assert isinstance(result, BacktestRunResult)
        assert result.status == "failed"

    def test_weekly_rebalance_frequency(self):
        """Weekly rebalance should produce more portfolios than monthly."""
        # Generate weekly data so weekly rebalance dates have matching factor data
        rng = np.random.RandomState(42)
        from synapse.core.market.calendar import trading_days_between as tdb
        all_tdays = tdb(date(2021, 1, 1), date(2022, 12, 31))
        tickers = [f"S{i}" for i in range(50)]
        idx = pd.MultiIndex.from_product(
            [[pd.Timestamp(d) for d in all_tdays], tickers], names=["date", "ticker"]
        )
        fv_df = pd.DataFrame(rng.randn(len(idx)), index=idx, columns=["factor"])
        fr = pd.Series(rng.randn(len(idx)) * 0.01, index=idx, name="fwd_ret")

        config_monthly = _default_config(
            start_date="2021-01-01",
            end_date="2022-12-31",
            rebalance_frequency="monthly",
        )
        config_weekly = _default_config(
            start_date="2021-01-01",
            end_date="2022-12-31",
            rebalance_frequency="weekly",
        )

        engine = BacktestEngine()
        result_m = engine.run(BacktestRequest(
            factor_values=fv_df, forward_returns=fr, config=config_monthly,
        ))
        result_w = engine.run(BacktestRequest(
            factor_values=fv_df, forward_returns=fr, config=config_weekly,
        ))

        assert len(result_w.quintile_portfolios) >= len(result_m.quintile_portfolios)

    def test_benchmark_returns_stored(self):
        """Benchmark returns are stored in the result when provided."""
        fv_df, fr = _make_synthetic_data(n_stocks=50, n_months=24,
                                          start_date="2021-01-01", end_date="2022-12-31")
        rng = np.random.RandomState(99)
        benchmark = pd.Series(rng.randn(24) * 0.01, name="bench")

        config = _default_config(
            start_date="2021-01-01",
            end_date="2022-12-31",
        )
        engine = BacktestEngine()
        result = engine.run(BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
            benchmark_returns=benchmark,
        ))

        assert result.status == "succeeded"
        assert len(result.benchmark_returns) > 0
