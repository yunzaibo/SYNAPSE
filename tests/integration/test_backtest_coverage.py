"""Targeted tests to increase coverage for synapse/backtest module.

Covers uncovered paths:
- persistence.py: save_result, load_result, query_results, _lazy_upcast
- engine.py: legacy run_backtest, _select_rebalance_dates edge cases
- metrics.py: standalone compute_metrics, MetricsCalculator edge cases
- attribution.py: edge cases (empty input, insufficient data)
- spread.py: edge cases (empty input, benchmark alignment)
- config.py: validation error paths
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from synapse.backtest.config import BacktestConfig
from synapse.backtest.engine import BacktestEngine, BacktestRequest
from synapse.backtest.ic_analyzer import ICAnalyzer
from synapse.backtest.metrics import MetricsCalculator, BacktestMetrics, compute_metrics
from synapse.backtest.persistence import (
    save_result,
    load_result,
    query_results,
    _lazy_upcast,
    _reconstruct_attribution,
)
from synapse.backtest.result import (
    AttributionResult,
    BacktestRunResult,
    ICAnalysisResult,
    PerformanceMetrics,
    QuintilePortfolio,
)
from synapse.backtest.spread import LongShortSpread, LongShortSpreadResult
from synapse.core.market.calendar import trading_days_between


# ---------------------------------------------------------------------------
# Persistence tests
# ---------------------------------------------------------------------------


class TestPersistence:
    """Test save/load/query operations for BacktestRunResult."""

    def test_save_and_load_roundtrip(self, tmp_path):
        """Save a result and load it back, verify all fields match."""
        from datetime import date as date_type

        result = BacktestRunResult(
            id="test_run_001",
            schema_version="1.0",
            config={"universe": "test", "n_quintiles": 5},
            run_timestamp="2024-01-15T10:00:00",
            start_date="2023-01-01",
            end_date="2023-12-31",
            factor_id="momentum",
            quintile_portfolios=(
                QuintilePortfolio(
                    date=date_type(2023, 1, 2),
                    quintiles={1: ("A", "B"), 5: ("C", "D")},
                    weights={1: {"A": 0.5, "B": 0.5}, 5: {"C": 0.5, "D": 0.5}},
                    factor_name="momentum",
                    universe_size=4,
                    valid_count=4,
                ),
            ),
            quintile_returns={1: 0.01, 5: 0.03},
            long_short_returns=(0.02, 0.015, -0.005),
            benchmark_returns=(0.01, 0.008, 0.002),
            performance=PerformanceMetrics(
                annual_return=0.15,
                volatility=0.2,
                sharpe=0.75,
                max_drawdown=-0.1,
            ),
            ic_analysis=ICAnalysisResult(
                factor_id="momentum",
                ic_mean=0.05,
                ic_series=(0.1, 0.05, 0.02),
                rank_ic_mean=0.05,
            ),
            attribution=AttributionResult(
                factor_returns={1: 0.01},
                residual_returns=(0.001, 0.002),
                total_factor_return=0.01,
                residual_return=0.0015,
                r_squared=0.85,
            ),
            status="succeeded",
        )

        save_result(result, tmp_path)
        loaded = load_result(tmp_path, "momentum", "test_run_001")

        assert loaded.id == result.id
        assert loaded.status == result.status
        assert loaded.factor_id == result.factor_id
        assert loaded.performance.annual_return == result.performance.annual_return
        assert loaded.performance.sharpe == result.performance.sharpe
        assert loaded.ic_analysis is not None
        assert loaded.ic_analysis.ic_mean == result.ic_analysis.ic_mean
        assert loaded.attribution is not None
        assert loaded.attribution.r_squared == result.attribution.r_squared
        assert len(loaded.long_short_returns) == len(result.long_short_returns)
        assert len(loaded.quintile_portfolios) == len(result.quintile_portfolios)

    def test_save_result_creates_parquet_files(self, tmp_path):
        """Verify save_result creates the expected directory structure."""
        result = BacktestRunResult(
            id="run_002",
            factor_id="value",
            start_date="2023-01-01",
            end_date="2023-12-31",
            status="succeeded",
        )
        save_result(result, tmp_path)

        # Check directory structure
        assert (tmp_path / "results" / "value" / "run_002.parquet").exists()
        assert (tmp_path / "quintile_returns" / "value" / "run_002.parquet").exists()

    def test_save_result_with_default_factor_id(self, tmp_path):
        """When factor_id is empty, uses 'default' as subdirectory."""
        result = BacktestRunResult(
            id="run_003",
            factor_id="",
            status="succeeded",
        )
        save_result(result, tmp_path)
        assert (tmp_path / "results" / "default" / "run_003.parquet").exists()

    def test_load_result_file_not_found(self, tmp_path):
        """load_result raises FileNotFoundError for missing result."""
        with pytest.raises(FileNotFoundError, match="No backtest result found"):
            load_result(tmp_path, "nonexistent", "nonexistent_run")

    def test_query_results_empty_dir(self, tmp_path):
        """query_results returns empty list when directory has no results."""
        results = query_results(tmp_path)
        assert results == []

    def test_query_results_with_data(self, tmp_path):
        """query_results finds saved results."""
        r1 = BacktestRunResult(
            id="r1", factor_id="f1", start_date="2023-01-01", end_date="2023-06-30",
            status="succeeded",
        )
        r2 = BacktestRunResult(
            id="r2", factor_id="f2", start_date="2023-07-01", end_date="2023-12-31",
            status="succeeded",
        )
        save_result(r1, tmp_path)
        save_result(r2, tmp_path)

        # Query all
        all_results = query_results(tmp_path)
        assert len(all_results) == 2

        # Query by factor_name
        f1_results = query_results(tmp_path, factor_name="f1")
        assert len(f1_results) == 1
        assert f1_results[0].factor_id == "f1"

        # Query by date range
        date_results = query_results(tmp_path, start_date="2023-07-01")
        assert len(date_results) == 1

    def test_query_results_nonexistent_dir(self, tmp_path):
        """query_results handles nonexistent directory gracefully."""
        results = query_results(tmp_path / "nonexistent")
        assert results == []

    def test_lazy_upcast_noop(self):
        """_lazy_upcast returns row unchanged for current schema."""
        row = {"id": "test", "status": "succeeded"}
        result = _lazy_upcast(row, "1.0")
        assert result == row

    def test_reconstruct_attribution_defaults(self):
        """_reconstruct_attribution returns None for all-default values."""
        row = {
            "attr_total_factor_return": 0.0,
            "attr_residual_return": 0.0,
            "attr_r_squared": 0.0,
            "attr_factor_returns": "{}",
            "attr_residual_returns": "[]",
        }
        result = _reconstruct_attribution(row)
        assert result is None

    def test_reconstruct_attribution_with_values(self):
        """_reconstruct_attribution returns AttributionResult when non-default."""
        row = {
            "attr_total_factor_return": 0.05,
            "attr_residual_return": 0.01,
            "attr_r_squared": 0.75,
            "attr_factor_returns": json.dumps({"1": 0.03, "2": 0.02}),
            "attr_residual_returns": json.dumps([0.01, 0.02]),
        }
        result = _reconstruct_attribution(row)
        assert result is not None
        assert result.total_factor_return == 0.05
        assert result.r_squared == 0.75
        assert 1 in result.factor_returns


# ---------------------------------------------------------------------------
# Legacy run_backtest tests
# ---------------------------------------------------------------------------


class TestLegacyRunBacktest:
    """Test the legacy run_backtest API for additional coverage."""

    def _make_series_data(self, n_stocks=30, n_days=60, seed=42):
        rng = np.random.RandomState(seed)
        dates = pd.bdate_range("2023-01-01", periods=n_days)
        tickers = [f"STK{i:02d}" for i in range(n_stocks)]
        idx = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])
        fv = pd.Series(rng.randn(len(idx)), index=idx, name="factor")
        fr = pd.Series(rng.randn(len(idx)) * 0.01, index=idx, name="fwd_ret")
        return fv, fr

    def test_run_backtest_sufficient_data(self):
        """Legacy API with enough data produces succeeded result."""
        fv, fr = self._make_series_data(n_stocks=50, n_days=120)
        config = BacktestConfig(
            universe="test", benchmark="ew", start_date="2023-01-01",
            end_date="2023-06-30", rebalance_frequency="monthly",
            transaction_cost_bps=10, slippage_bps=5,
        )
        engine = BacktestEngine()
        result = engine.run_backtest(fv, fr, config)
        assert result.status == "succeeded"
        assert len(result.trades) > 0

    def test_run_backtest_insufficient_data(self):
        """Legacy API with too little data returns failed."""
        fv = pd.Series([1.0], index=pd.MultiIndex.from_tuples(
            [(pd.Timestamp("2023-01-01"), "A")], names=["date", "ticker"]
        ))
        fr = pd.Series([0.01], index=pd.MultiIndex.from_tuples(
            [(pd.Timestamp("2023-01-01"), "A")], names=["date", "ticker"]
        ))
        config = BacktestConfig(
            universe="test", benchmark="ew", start_date="2023-01-01",
            end_date="2023-01-01", rebalance_frequency="monthly",
            transaction_cost_bps=10, slippage_bps=5,
        )
        engine = BacktestEngine()
        result = engine.run_backtest(fv, fr, config)
        assert result.status == "failed"


# ---------------------------------------------------------------------------
# MetricsCalculator standalone tests
# ---------------------------------------------------------------------------


class TestMetricsCalculatorCoverage:
    """Target uncovered paths in metrics.py."""

    def test_compute_empty_returns(self):
        """MetricsCalculator with empty array returns default metrics."""
        calc = MetricsCalculator()
        result = calc.compute(np.array([]))
        assert result == PerformanceMetrics()

    def test_compute_single_return(self):
        """MetricsCalculator with a single return."""
        calc = MetricsCalculator()
        result = calc.compute(np.array([0.01]))
        assert result.annual_return != 0.0
        assert result.win_rate == 1.0

    def test_compute_with_benchmark(self):
        """MetricsCalculator with benchmark returns."""
        calc = MetricsCalculator()
        result = calc.compute(np.array([0.01, 0.008, 0.002]), benchmark_returns=np.array([0.005, 0.003, 0.001]))
        assert result.excess_return != 0.0
        assert result.information_ratio != 0.0

    def test_compute_zero_volatility(self):
        """MetricsCalculator with constant returns (zero volatility)."""
        calc = MetricsCalculator()
        result = calc.compute(np.array([0.01, 0.01, 0.01, 0.01]))
        assert result.sharpe == 0.0  # zero std => sharpe = 0

    def test_compute_mismatched_benchmark(self):
        """MetricsCalculator with mismatched benchmark length."""
        calc = MetricsCalculator()
        result = calc.compute(np.array([0.01, 0.008, 0.002]), benchmark_returns=np.array([0.005, 0.003]))
        # Benchmark length mismatch => treated as no benchmark
        assert result.excess_return == 0.0

    def test_compute_legacy_wrapper(self):
        """compute_metrics standalone function."""
        portfolio = np.array([0.01, -0.005, 0.008])
        benchmark = np.array([0.005, 0.003, 0.001])
        result = compute_metrics(portfolio, benchmark)
        assert isinstance(result, BacktestMetrics)
        assert result.annual_return != 0.0

    def test_compute_legacy_empty(self):
        """compute_metrics with empty arrays."""
        result = compute_metrics(np.array([]), np.array([]))
        assert result.annual_return == 0

    def test_compute_all_losses(self):
        """MetricsCalculator with all negative returns."""
        calc = MetricsCalculator()
        result = calc.compute(np.array([-0.01, -0.02, -0.005]))
        assert result.win_rate == 0.0
        assert result.max_drawdown < 0


# ---------------------------------------------------------------------------
# AttributionEngine edge cases
# ---------------------------------------------------------------------------


class TestAttributionCoverage:
    """Target uncovered paths in attribution.py."""

    def test_empty_factor_returns(self):
        """AttributionEngine with empty inputs returns default."""
        from synapse.backtest.attribution import AttributionEngine
        engine = AttributionEngine()
        pr = pd.Series(dtype=float)
        fr = pd.DataFrame(dtype=float)
        result = engine.compute(pr, fr)
        assert result == AttributionResult()

    def test_no_common_dates(self):
        """AttributionEngine with no overlapping dates."""
        from synapse.backtest.attribution import AttributionEngine
        engine = AttributionEngine()
        pr = pd.Series([0.01], index=[pd.Timestamp("2023-01-01")])
        fr = pd.DataFrame({1: [0.02]}, index=[pd.Timestamp("2023-06-01")])
        result = engine.compute(pr, fr)
        assert result == AttributionResult()

    def test_insufficient_data_points(self):
        """AttributionEngine with fewer observations than factors."""
        from synapse.backtest.attribution import AttributionEngine
        engine = AttributionEngine()
        idx = [pd.Timestamp("2023-01-01")]
        pr = pd.Series([0.01], index=idx)
        fr = pd.DataFrame({1: [0.02], 2: [0.03]}, index=idx)
        result = engine.compute(pr, fr)
        assert result == AttributionResult()


# ---------------------------------------------------------------------------
# Spread edge cases
# ---------------------------------------------------------------------------


class TestSpreadCoverage:
    """Target uncovered paths in spread.py."""

    def test_empty_quintile_returns(self):
        """LongShortSpread with empty DataFrame."""
        spread = LongShortSpread()
        result = spread.compute(pd.DataFrame())
        assert result == LongShortSpreadResult()

    def test_spread_with_benchmark(self):
        """LongShortSpread with benchmark returns."""
        spread = LongShortSpread(benchmark_returns=pd.Series([0.01, 0.005, 0.002]))
        q_df = pd.DataFrame({
            "Q1": [0.01, 0.005, 0.002],
            "Q5": [0.03, 0.02, 0.01],
        })
        result = spread.compute(q_df)
        assert len(result.spread_returns) == 3
        assert len(result.benchmark_returns) == 3
        assert len(result.excess_returns) == 3
        assert result.annual_spread_return != 0.0

    def test_spread_to_dict_from_dict(self):
        """LongShortSpreadResult survives roundtrip."""
        result = LongShortSpreadResult(
            spread_returns=(0.01, 0.02),
            annual_spread_return=0.15,
        )
        d = result.to_dict()
        restored = LongShortSpreadResult.from_dict(d)
        assert restored.spread_returns == result.spread_returns
        assert restored.annual_spread_return == result.annual_spread_return


# ---------------------------------------------------------------------------
# Config validation edge cases
# ---------------------------------------------------------------------------


class TestConfigValidationCoverage:
    """Target uncovered validation paths in config.py."""

    def test_transaction_cost_bps_none(self):
        """BacktestConfig rejects None transaction_cost_bps."""
        with pytest.raises(ValueError, match="transaction_cost_bps must be explicitly set"):
            BacktestConfig(
                universe="u", benchmark="b", start_date="2023-01-01",
                end_date="2023-12-31", rebalance_frequency="monthly",
                transaction_cost_bps=None, slippage_bps=2.0,
            )

    def test_slippage_bps_none(self):
        """BacktestConfig rejects None slippage_bps."""
        with pytest.raises(ValueError, match="slippage_bps must be explicitly set"):
            BacktestConfig(
                universe="u", benchmark="b", start_date="2023-01-01",
                end_date="2023-12-31", rebalance_frequency="monthly",
                transaction_cost_bps=5.0, slippage_bps=None,
            )


# ---------------------------------------------------------------------------
# Engine edge cases for additional coverage
# ---------------------------------------------------------------------------


class TestEngineEdgeCases:
    """Additional engine edge cases for coverage."""

    def test_no_rebalance_dates_in_range(self):
        """Engine returns failed when no rebalance dates found."""
        # Use a date range where all dates are holidays
        # 2024-10-01 to 2024-10-07 are all holidays
        rng = np.random.RandomState(42)
        # Use dates that exist in factor data but no trading days in range
        dates = [pd.Timestamp("2024-10-01")]
        tickers = [f"S{i}" for i in range(10)]
        idx = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])
        fv_df = pd.DataFrame(rng.randn(len(idx)), index=idx, columns=["factor"])
        fr = pd.Series(rng.randn(len(idx)) * 0.01, index=idx, name="fwd_ret")

        config = BacktestConfig(
            universe="test", benchmark="CSI300",
            start_date="2024-10-01", end_date="2024-10-07",
            rebalance_frequency="daily",
            transaction_cost_bps=10.0, slippage_bps=5.0,
        )
        engine = BacktestEngine()
        result = engine.run(BacktestRequest(
            factor_values=fv_df, forward_returns=fr, config=config,
        ))
        assert result.status == "failed"

    def test_config_to_dict_method(self):
        """Engine._config_to_dict produces correct output."""
        config = BacktestConfig(
            universe="test", benchmark="CSI300",
            start_date="2023-01-01", end_date="2023-12-31",
            rebalance_frequency="monthly",
            transaction_cost_bps=10.0, slippage_bps=5.0,
        )
        d = BacktestEngine._config_to_dict(config)
        assert d["universe"] == "test"
        assert d["n_quintiles"] == 5
        assert d["rebalance_frequency"] == "monthly"

    def test_df_to_series_with_series_input(self):
        """Engine._df_to_series handles Series input."""
        s = pd.Series([1.0, 2.0], name="factor")
        result = BacktestEngine._df_to_series(s)
        assert isinstance(result, pd.Series)

    def test_df_to_series_with_multi_column_raises(self):
        """Engine._df_to_series raises for multi-column DataFrame."""
        df = pd.DataFrame({"a": [1], "b": [2]})
        with pytest.raises(ValueError, match="exactly one column"):
            BacktestEngine._df_to_series(df)

    def test_select_rebalance_dates_daily(self):
        """_select_rebalance_dates with daily frequency returns all days."""
        days = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]
        result = BacktestEngine._select_rebalance_dates(days, "daily")
        assert result == days

    def test_select_rebalance_dates_empty(self):
        """_select_rebalance_dates with empty list."""
        result = BacktestEngine._select_rebalance_dates([], "monthly")
        assert result == []

    def test_normalize_dates_empty(self):
        """_normalize_dates with empty list."""
        s = pd.Series(dtype=float)
        s.index = pd.MultiIndex.from_tuples([], names=["date", "ticker"])
        result = BacktestEngine._normalize_dates([], s)
        assert result == []


# ---------------------------------------------------------------------------
# ICAnalyzer edge cases
# ---------------------------------------------------------------------------


class TestICAnalyzerCoverage:
    """Target uncovered paths in ic_analyzer.py."""

    def test_empty_inputs(self):
        """ICAnalyzer with empty DataFrames."""
        analyzer = ICAnalyzer()
        fv = pd.DataFrame(columns=["factor"])
        fv.index = pd.MultiIndex.from_tuples([], names=["date", "ticker"])
        fr = pd.Series(dtype=float)
        fr.index = pd.MultiIndex.from_tuples([], names=["date", "ticker"])
        result = analyzer.compute_ic(fv, fr, factor_id="test")
        assert result.factor_id == "test"
        assert len(result.ic_series) == 0

    def test_no_common_index(self):
        """ICAnalyzer with no overlapping index."""
        analyzer = ICAnalyzer()
        idx1 = pd.MultiIndex.from_tuples(
            [(pd.Timestamp("2023-01-01"), "A")], names=["date", "ticker"]
        )
        idx2 = pd.MultiIndex.from_tuples(
            [(pd.Timestamp("2023-06-01"), "A")], names=["date", "ticker"]
        )
        fv = pd.DataFrame({"factor": [1.0]}, index=idx1)
        fr = pd.Series([0.01], index=idx2)
        result = analyzer.compute_ic(fv, fr)
        assert len(result.ic_series) == 0

    def test_insufficient_stocks_per_date(self):
        """ICAnalyzer skips dates with too few stocks."""
        analyzer = ICAnalyzer(min_stocks=10)
        dates = [pd.Timestamp("2023-01-01")]
        tickers = [f"S{i}" for i in range(5)]  # only 5 < min_stocks=10
        idx = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])
        fv = pd.DataFrame({"factor": range(5)}, index=idx, dtype=float)
        fr = pd.Series(range(5), index=idx, dtype=float)
        result = analyzer.compute_ic(fv, fr)
        assert len(result.ic_series) == 0
