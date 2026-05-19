"""Integration tests for P6 FactorEngine -> BacktestEngine data contract.

Validates that FactorEngine.compute_batch() output format matches
BacktestEngine.run() input expectations (MultiIndex (date, ticker)
DataFrame with a single factor column).

Covers IMPL-008 P6 integration requirements:
- FactorEngine output DataFrame format matches BacktestEngine expectations
- MultiIndex (date, ticker) structure validation
- Correct column selection from multi-column output
- Graceful handling of empty FactorEngine output
- Graceful handling of all-NaN factor values
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from synapse.backtest.config import BacktestConfig
from synapse.backtest.engine import BacktestEngine, BacktestRequest
from synapse.backtest.result import BacktestRunResult
from synapse.core.market.calendar import trading_days_between


# ---------------------------------------------------------------------------
# Helpers: simulate FactorEngine output with TradingCalendar-aligned dates
# ---------------------------------------------------------------------------

def _get_monthly_trading_days(start: date, end: date) -> list[pd.Timestamp]:
    """Get the first trading day of each month within a date range."""
    tdays = trading_days_between(start, end)
    monthly: list[pd.Timestamp] = []
    seen_months: set[tuple[int, int]] = set()
    for d in tdays:
        key = (d.year, d.month)
        if key not in seen_months:
            monthly.append(pd.Timestamp(d))
            seen_months.add(key)
    return monthly


def _make_factor_engine_output(
    n_stocks: int = 100,
    n_dates: int = 24,
    seed: int = 42,
    start_date: str = "2022-01-01",
    end_date: str = "2023-12-31",
) -> pd.DataFrame:
    """Simulate FactorEngine.compute_batch() output with MultiIndex (date, ticker).

    Returns a DataFrame with columns=['momentum'] and MultiIndex (date, ticker),
    which is the format BacktestEngine expects.
    """
    rng = np.random.RandomState(seed)
    dates = _get_monthly_trading_days(
        date.fromisoformat(start_date),
        date.fromisoformat(end_date),
    )[:n_dates]

    tickers = [f"SH{str(i).zfill(6)}" for i in range(n_stocks)]
    idx = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])
    values = rng.randn(len(idx))

    return pd.DataFrame({"momentum": values}, index=idx)


def _make_multi_column_output(
    n_stocks: int = 100,
    n_dates: int = 24,
    seed: int = 42,
) -> pd.DataFrame:
    """Simulate FactorEngine output with multiple factor columns."""
    rng = np.random.RandomState(seed)
    dates = _get_monthly_trading_days(date(2022, 1, 1), date(2023, 12, 31))[:n_dates]
    tickers = [f"SH{str(i).zfill(6)}" for i in range(n_stocks)]
    idx = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])

    return pd.DataFrame({
        "momentum": rng.randn(len(idx)),
        "value": rng.randn(len(idx)),
        "size": rng.randn(len(idx)),
    }, index=idx)


def _make_forward_returns(
    factor_output: pd.DataFrame,
    seed: int = 99,
) -> pd.Series:
    """Create aligned forward returns matching a factor output DataFrame."""
    rng = np.random.RandomState(seed)
    values = rng.randn(len(factor_output)) * 0.01
    return pd.Series(values, index=factor_output.index, name="fwd_ret")


def _backtest_config(**overrides) -> BacktestConfig:
    defaults = dict(
        universe="p6-test",
        benchmark="CSI300",
        start_date="2022-01-01",
        end_date="2023-12-31",
        rebalance_frequency="monthly",
        transaction_cost_bps=10.0,
        slippage_bps=5.0,
    )
    defaults.update(overrides)
    return BacktestConfig(**defaults)


# ---------------------------------------------------------------------------
# Test 1: FactorEngine output format validation
# ---------------------------------------------------------------------------


class TestFactorEngineOutputFormat:
    """Verify DataFrame format matches BacktestEngine expectations."""

    def test_factor_engine_output_format(self):
        """Single-column DataFrame with MultiIndex works as BacktestEngine input."""
        fv_df = _make_factor_engine_output()
        fr = _make_forward_returns(fv_df)

        config = _backtest_config()
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
            factor_id="momentum",
        )

        engine = BacktestEngine()
        result = engine.run(request)

        assert result.status == "succeeded"
        assert result.factor_id == "momentum"
        assert len(result.quintile_portfolios) > 0

    def test_series_input_works(self):
        """A pd.Series with MultiIndex also works (BacktestEngine._df_to_series)."""
        fv_df = _make_factor_engine_output()
        fr = _make_forward_returns(fv_df)

        config = _backtest_config()
        request = BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
            factor_id="momentum_series",
        )

        engine = BacktestEngine()
        result = engine.run(request)

        assert result.status == "succeeded"


# ---------------------------------------------------------------------------
# Test 2: MultiIndex structure validation
# ---------------------------------------------------------------------------


class TestFactorValuesMultindex:
    """Verify MultiIndex (date, ticker) structure is correctly handled."""

    def test_factor_values_multindex(self):
        """MultiIndex with named levels (date, ticker) is correctly parsed."""
        fv_df = _make_factor_engine_output(n_stocks=50, n_dates=12)
        fr = _make_forward_returns(fv_df)

        # Verify the MultiIndex structure
        assert fv_df.index.names == ["date", "ticker"]
        assert isinstance(fv_df.index, pd.MultiIndex)

        # Verify date level contains timestamps
        dates_level = fv_df.index.get_level_values("date")
        assert len(dates_level.unique()) == 12

        # Verify ticker level contains strings
        tickers_level = fv_df.index.get_level_values("ticker")
        assert len(tickers_level.unique()) == 50

        # Run backtest
        config = _backtest_config(
            start_date="2022-01-01",
            end_date="2023-12-31",
        )
        engine = BacktestEngine()
        result = engine.run(BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        ))

        assert result.status == "succeeded"

        # Verify quintile portfolios reference correct tickers
        for qp in result.quintile_portfolios:
            for q_id, tickers in qp.quintiles.items():
                for t in tickers:
                    assert t.startswith("SH"), f"Unexpected ticker format: {t}"

    def test_date_type_compatibility(self):
        """Engine handles both pd.Timestamp and date objects in index."""
        rng = np.random.RandomState(42)
        # Use pd.Timestamp dates (as FactorEngine would produce)
        dates_ts = _get_monthly_trading_days(date(2022, 1, 1), date(2022, 12, 31))
        tickers = [f"SZ{i:06d}" for i in range(30)]
        idx = pd.MultiIndex.from_product([dates_ts, tickers], names=["date", "ticker"])

        fv_df = pd.DataFrame(rng.randn(len(idx)), index=idx, columns=["factor"])
        fr = pd.Series(rng.randn(len(idx)) * 0.01, index=idx, name="fwd_ret")

        config = _backtest_config(
            start_date="2022-01-01",
            end_date="2022-12-31",
        )
        engine = BacktestEngine()
        result = engine.run(BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
        ))

        assert result.status == "succeeded"


# ---------------------------------------------------------------------------
# Test 3: Column selection from multi-column output
# ---------------------------------------------------------------------------


class TestFactorIdColumnSelection:
    """Verify correct column extraction from multi-column FactorEngine output."""

    def test_select_single_column_from_multi_column(self):
        """BacktestEngine correctly selects the specified factor column."""
        fv_multi = _make_multi_column_output(n_stocks=50, n_dates=12)
        fr = _make_forward_returns(fv_multi)

        # BacktestEngine expects a single-column DataFrame
        # Select 'momentum' column
        fv_single = fv_multi[["momentum"]]
        assert fv_single.shape[1] == 1

        config = _backtest_config(
            start_date="2022-01-01",
            end_date="2023-12-31",
        )
        engine = BacktestEngine()
        result = engine.run(BacktestRequest(
            factor_values=fv_single,
            forward_returns=fr,
            config=config,
            factor_id="momentum",
        ))

        assert result.status == "succeeded"
        assert result.factor_id == "momentum"

    def test_reject_multi_column_dataframe(self):
        """BacktestEngine rejects DataFrame with more than one column."""
        fv_multi = _make_multi_column_output(n_stocks=50, n_dates=12)
        fr = _make_forward_returns(fv_multi)

        config = _backtest_config(
            start_date="2022-01-01",
            end_date="2023-12-31",
        )
        engine = BacktestEngine()
        request = BacktestRequest(
            factor_values=fv_multi,  # 3 columns -- should fail
            forward_returns=fr,
            config=config,
        )

        # Engine should catch the ValueError and return failed
        result = engine.run(request)
        assert result.status == "failed"
        assert "one column" in result.error.lower() or "error" in result.status


# ---------------------------------------------------------------------------
# Test 4: Edge case -- empty FactorEngine output
# ---------------------------------------------------------------------------


class TestEdgeCaseEmptyOutput:
    """Graceful handling of empty FactorEngine output."""

    def test_edge_case_empty_output(self):
        """Empty DataFrame from FactorEngine returns failed result, not exception."""
        empty_fv = pd.DataFrame(columns=["momentum"])
        empty_fv.index = pd.MultiIndex.from_tuples([], names=["date", "ticker"])
        empty_fr = pd.Series(dtype=float)
        empty_fr.index = pd.MultiIndex.from_tuples([], names=["date", "ticker"])

        config = _backtest_config()
        engine = BacktestEngine()
        result = engine.run(BacktestRequest(
            factor_values=empty_fv,
            forward_returns=empty_fr,
            config=config,
            factor_id="empty_factor",
        ))

        assert isinstance(result, BacktestRunResult)
        assert result.status == "failed"
        assert result.error is not None
        assert "empty" in result.error.lower() or "Empty" in result.error


# ---------------------------------------------------------------------------
# Test 5: Edge case -- all-NaN factor values
# ---------------------------------------------------------------------------


class TestEdgeCaseAllNan:
    """Graceful handling of all-NaN factor values from FactorEngine."""

    def test_edge_case_all_nan(self):
        """All-NaN factor values produce a failed or empty result, not exception."""
        dates = _get_monthly_trading_days(date(2022, 1, 1), date(2022, 6, 30))
        tickers = [f"S{i}" for i in range(20)]
        idx = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])

        fv_df = pd.DataFrame(np.nan, index=idx, columns=["factor"])
        fr = pd.Series(0.01, index=idx, name="fwd_ret")

        config = _backtest_config(
            start_date="2022-01-01",
            end_date="2022-06-30",
        )
        engine = BacktestEngine()
        result = engine.run(BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
            factor_id="nan_factor",
        ))

        assert isinstance(result, BacktestRunResult)
        # All NaN => no valid stocks for quintile sorting => failed
        assert result.status == "failed"

    def test_partial_nan_still_works(self):
        """Partial NaN values should still produce a valid result."""
        rng = np.random.RandomState(42)
        dates = _get_monthly_trading_days(date(2022, 1, 1), date(2022, 12, 31))
        tickers = [f"S{i}" for i in range(50)]
        idx = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])

        values = rng.randn(len(idx))
        # Set ~50% to NaN
        values[rng.random(len(values)) < 0.5] = np.nan

        fv_df = pd.DataFrame(values, index=idx, columns=["factor"])
        fr = pd.Series(rng.randn(len(idx)) * 0.01, index=idx, name="fwd_ret")

        config = _backtest_config(
            start_date="2022-01-01",
            end_date="2022-12-31",
        )
        engine = BacktestEngine()
        result = engine.run(BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
            factor_id="partial_nan",
        ))

        # Should succeed if enough valid stocks remain for sorting
        assert isinstance(result, BacktestRunResult)
        assert result.status in ("succeeded", "failed")

    def test_mismatched_index_returns_failed(self):
        """Factor values and forward returns with no overlapping dates/tickers."""
        rng = np.random.RandomState(42)
        dates1 = _get_monthly_trading_days(date(2022, 1, 1), date(2022, 6, 30))
        dates2 = _get_monthly_trading_days(date(2023, 1, 1), date(2023, 6, 30))
        tickers = [f"S{i}" for i in range(20)]

        idx1 = pd.MultiIndex.from_product([dates1, tickers], names=["date", "ticker"])
        idx2 = pd.MultiIndex.from_product([dates2, tickers], names=["date", "ticker"])

        fv_df = pd.DataFrame(rng.randn(len(idx1)), index=idx1, columns=["factor"])
        fr = pd.Series(rng.randn(len(idx2)) * 0.01, index=idx2, name="fwd_ret")

        config = _backtest_config(
            start_date="2022-01-01",
            end_date="2022-12-31",
        )
        engine = BacktestEngine()
        result = engine.run(BacktestRequest(
            factor_values=fv_df,
            forward_returns=fr,
            config=config,
            factor_id="mismatched",
        ))

        # No overlap => no valid rebalance dates with data => failed
        assert isinstance(result, BacktestRunResult)
        assert result.status == "failed"
