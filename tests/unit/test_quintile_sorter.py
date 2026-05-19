"""Unit tests for QuintileSorter and frozen dataclass result models."""

import dataclasses
from datetime import date

import numpy as np
import pandas as pd
import pytest

from synapse.backtest.quintile import QuintileSorter
from synapse.backtest.result import (
    AttributionResult,
    BacktestRunResult,
    ICAnalysisResult,
    PerformanceMetrics,
    QuintilePortfolio,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_factor_series(
    n_stocks: int = 100,
    dates: list[date] | None = None,
    seed: int = 42,
) -> pd.Series:
    """Create a synthetic factor Series with MultiIndex (date, ticker)."""
    if dates is None:
        dates = [date(2024, 1, 15)]
    tickers = [f"STK{i:03d}" for i in range(n_stocks)]
    idx = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])
    rng = np.random.RandomState(seed)
    values = rng.randn(len(idx))
    return pd.Series(values, index=idx, name="factor_value")


def _make_multi_date_factor(
    n_stocks: int = 50,
    n_dates: int = 3,
    seed: int = 42,
) -> tuple[pd.Series, list[date]]:
    """Create a factor Series spanning multiple dates."""
    dates = [date(2024, 1, 15 + i) for i in range(n_dates)]
    return _make_factor_series(n_stocks=n_stocks, dates=dates, seed=seed), dates


# ---------------------------------------------------------------------------
# QuintileSorter tests
# ---------------------------------------------------------------------------


class TestQuintileSorterSort:
    """Tests for QuintileSorter.sort()."""

    def test_normal_5_quintile_sorting(self):
        """100 stocks should produce 5 groups of ~20 each."""
        factor = _make_factor_series(n_stocks=100)
        sorter = QuintileSorter()
        portfolio = sorter.sort(factor, date(2024, 1, 15))

        assert portfolio is not None
        assert isinstance(portfolio, QuintilePortfolio)
        assert len(portfolio.quintiles) == 5
        # Each quintile should have ~20 stocks (exact due to pd.qcut with ties)
        for q_id, tickers in portfolio.quintiles.items():
            assert 1 <= q_id <= 5
            assert len(tickers) == 20

    def test_equal_weight_sum_to_one(self):
        """Weights within each quintile must sum to 1.0."""
        factor = _make_factor_series(n_stocks=100)
        sorter = QuintileSorter()
        portfolio = sorter.sort(factor, date(2024, 1, 15))

        assert portfolio is not None
        for q_id, weight_dict in portfolio.weights.items():
            total = sum(weight_dict.values())
            assert abs(total - 1.0) < 1e-10, (
                f"Quintile {q_id} weights sum to {total}, expected 1.0"
            )

    def test_each_stock_gets_correct_weight(self):
        """Each stock in a quintile of size N should have weight 1/N."""
        factor = _make_factor_series(n_stocks=25)
        sorter = QuintileSorter()
        portfolio = sorter.sort(factor, date(2024, 1, 15))

        assert portfolio is not None
        for q_id, weight_dict in portfolio.weights.items():
            n = len(portfolio.quintiles[q_id])
            expected_weight = 1.0 / n
            for ticker, w in weight_dict.items():
                assert abs(w - expected_weight) < 1e-10

    def test_missing_factor_values_excluded(self):
        """Stocks with NaN factor values should be excluded from sorting."""
        factor = _make_factor_series(n_stocks=20)
        # Inject NaN for some stocks
        factor.iloc[:5] = np.nan
        sorter = QuintileSorter()
        portfolio = sorter.sort(factor, date(2024, 1, 15))

        assert portfolio is not None
        assert portfolio.valid_count == 15
        assert portfolio.universe_size == 20
        # All 15 valid stocks should be distributed across quintiles
        total_assigned = sum(len(t) for t in portfolio.quintiles.values())
        assert total_assigned == 15

    def test_no_data_for_date_returns_none(self):
        """Requesting a date with no data should return None."""
        factor = _make_factor_series(n_stocks=10, dates=[date(2024, 1, 15)])
        sorter = QuintileSorter()
        portfolio = sorter.sort(factor, date(2024, 6, 1))

        assert portfolio is None

    def test_fewer_than_n_stocks_returns_none(self):
        """Fewer valid stocks than quintiles should return None."""
        factor = _make_factor_series(n_stocks=3)
        sorter = QuintileSorter()
        portfolio = sorter.sort(factor, date(2024, 1, 15), n_quintiles=5)

        assert portfolio is None

    def test_all_nan_returns_none(self):
        """All-NaN factor values should return None."""
        factor = _make_factor_series(n_stocks=10)
        factor.iloc[:] = np.nan
        sorter = QuintileSorter()
        portfolio = sorter.sort(factor, date(2024, 1, 15))

        assert portfolio is None

    def test_exactly_n_stocks(self):
        """Exactly 5 stocks should produce 5 quintiles of 1 each."""
        factor = _make_factor_series(n_stocks=5)
        sorter = QuintileSorter()
        portfolio = sorter.sort(factor, date(2024, 1, 15))

        assert portfolio is not None
        assert len(portfolio.quintiles) == 5
        for q_id, tickers in portfolio.quintiles.items():
            assert len(tickers) == 1

    def test_factor_name_propagated(self):
        """The factor_name argument should appear in the portfolio."""
        factor = _make_factor_series(n_stocks=10)
        sorter = QuintileSorter()
        portfolio = sorter.sort(
            factor, date(2024, 1, 15), factor_name="momentum"
        )

        assert portfolio is not None
        assert portfolio.factor_name == "momentum"

    def test_single_stock_returns_none(self):
        """A single stock is fewer than 5 quintiles, should return None."""
        factor = _make_factor_series(n_stocks=1)
        sorter = QuintileSorter()
        portfolio = sorter.sort(factor, date(2024, 1, 15), n_quintiles=5)

        assert portfolio is None


class TestQuintileSorterTimeseries:
    """Tests for QuintileSorter.sort_timeseries()."""

    def test_multi_date_sorting(self):
        """sort_timeseries should produce a portfolio for each valid date."""
        factor, dates = _make_multi_date_factor(n_stocks=50, n_dates=3)
        sorter = QuintileSorter()
        result = sorter.sort_timeseries(factor, dates)

        assert len(result) == 3
        for d in dates:
            assert d in result
            assert isinstance(result[d], QuintilePortfolio)

    def test_skip_dates_with_no_data(self):
        """Dates not in the factor data should be skipped."""
        factor = _make_factor_series(n_stocks=30, dates=[date(2024, 1, 15)])
        sorter = QuintileSorter()
        dates = [date(2024, 1, 15), date(2024, 6, 1)]
        result = sorter.sort_timeseries(factor, dates)

        assert len(result) == 1
        assert date(2024, 1, 15) in result

    def test_dataframe_input(self):
        """sort_timeseries should accept a single-column DataFrame."""
        factor = _make_factor_series(n_stocks=30, dates=[date(2024, 1, 15)])
        df = factor.to_frame()
        sorter = QuintileSorter()
        result = sorter.sort_timeseries(df, [date(2024, 1, 15)])

        assert len(result) == 1

    def test_multi_column_dataframe_raises(self):
        """Multi-column DataFrame should raise ValueError."""
        factor = _make_factor_series(n_stocks=30, dates=[date(2024, 1, 15)])
        df = pd.concat([factor, factor.rename("other")], axis=1)
        sorter = QuintileSorter()

        with pytest.raises(ValueError, match="exactly one column"):
            sorter.sort_timeseries(df, [date(2024, 1, 15)])


# ---------------------------------------------------------------------------
# Frozen dataclass tests
# ---------------------------------------------------------------------------


class TestFrozenDataclasses:
    """Verify immutability of frozen dataclasses."""

    def test_quintile_portfolio_is_frozen(self):
        qp = QuintilePortfolio(
            date=date(2024, 1, 15),
            quintiles={1: ("A",)},
            weights={1: {"A": 1.0}},
            factor_name="test",
            universe_size=1,
            valid_count=1,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            qp.date = date(2024, 2, 1)

    def test_performance_metrics_is_frozen(self):
        pm = PerformanceMetrics(annual_return=0.1)
        with pytest.raises(dataclasses.FrozenInstanceError):
            pm.annual_return = 0.2

    def test_ic_analysis_result_is_frozen(self):
        ic = ICAnalysisResult(factor_id="f1", ic_mean=0.05)
        with pytest.raises(dataclasses.FrozenInstanceError):
            ic.ic_mean = 0.1

    def test_attribution_result_is_frozen(self):
        ar = AttributionResult(r_squared=0.8)
        with pytest.raises(dataclasses.FrozenInstanceError):
            ar.r_squared = 0.9

    def test_backtest_run_result_is_frozen(self):
        br = BacktestRunResult(id="test-001")
        with pytest.raises(dataclasses.FrozenInstanceError):
            br.id = "test-002"


# ---------------------------------------------------------------------------
# Serialization round-trip tests
# ---------------------------------------------------------------------------


class TestSerialization:
    """Verify to_dict/from_dict round-trips for all dataclasses."""

    def test_quintile_portfolio_round_trip(self):
        qp = QuintilePortfolio(
            date=date(2024, 1, 15),
            quintiles={1: ("AAPL", "MSFT"), 2: ("GOOG",)},
            weights={1: {"AAPL": 0.5, "MSFT": 0.5}, 2: {"GOOG": 1.0}},
            factor_name="momentum",
            universe_size=3,
            valid_count=3,
        )
        d = qp.to_dict()
        qp2 = QuintilePortfolio.from_dict(d)
        assert qp == qp2

    def test_performance_metrics_round_trip(self):
        pm = PerformanceMetrics(
            annual_return=0.15, volatility=0.2, sharpe=0.75, max_drawdown=-0.1
        )
        d = pm.to_dict()
        pm2 = PerformanceMetrics.from_dict(d)
        assert pm == pm2

    def test_performance_metrics_defaults_round_trip(self):
        pm = PerformanceMetrics()
        d = pm.to_dict()
        pm2 = PerformanceMetrics.from_dict(d)
        assert pm == pm2

    def test_ic_analysis_result_round_trip(self):
        ic = ICAnalysisResult(
            factor_id="f1",
            ic_series=(0.05, 0.03, 0.07),
            ic_mean=0.05,
            icir=1.2,
        )
        d = ic.to_dict()
        ic2 = ICAnalysisResult.from_dict(d)
        assert ic == ic2

    def test_attribution_result_round_trip(self):
        ar = AttributionResult(
            factor_returns={1: 0.1, 5: -0.05},
            r_squared=0.85,
        )
        d = ar.to_dict()
        ar2 = AttributionResult.from_dict(d)
        assert ar == ar2

    def test_backtest_run_result_round_trip(self):
        qp = QuintilePortfolio(
            date=date(2024, 1, 15),
            quintiles={1: ("A",)},
            weights={1: {"A": 1.0}},
            factor_name="test",
            universe_size=1,
            valid_count=1,
        )
        br = BacktestRunResult(
            id="run-001",
            factor_id="momentum",
            quintile_portfolios=(qp,),
            performance=PerformanceMetrics(annual_return=0.1),
            status="completed",
        )
        d = br.to_dict()
        br2 = BacktestRunResult.from_dict(d)
        assert br == br2
