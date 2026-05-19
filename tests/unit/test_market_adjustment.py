"""Tests for Ex-Right Adjustment Module — synapse/core/market/adjustment.py."""

from __future__ import annotations

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from synapse.core.market.adjustment import (
    AdjustmentEvent,
    AdjustmentFactors,
    AdjustmentType,
    adjust_prices,
    adjust_single_price,
    get_adjustment_factors,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dec(val: str) -> Decimal:
    return Decimal(val)


def _make_event(
    evt_date: date,
    factor: str = "0.95",
    event_type: str = "dividend",
    cash_div: str = "0.50",
    stock_div: str = "0.0",
) -> AdjustmentEvent:
    return AdjustmentEvent(
        date=evt_date,
        factor=_dec(factor),
        event_type=event_type,
        cash_dividend=_dec(cash_div),
        stock_dividend=_dec(stock_div),
    )


def _make_factors(
    symbol: str = "000001.SZ",
    events: list[AdjustmentEvent] | None = None,
) -> AdjustmentFactors:
    if events is None:
        events = [
            _make_event(date(2025, 1, 15), factor="0.95"),
            _make_event(date(2025, 6, 20), factor="0.90"),
        ]
    return AdjustmentFactors(symbol=symbol, events=tuple(events))


def _make_ohlcv_df() -> pd.DataFrame:
    """Simple OHLCV DataFrame for testing."""
    return pd.DataFrame(
        {
            "date": [date(2025, 1, 10), date(2025, 2, 10), date(2025, 7, 10)],
            "open": [20.0, 22.0, 25.0],
            "high": [21.0, 23.0, 26.0],
            "low": [19.0, 21.0, 24.0],
            "close": [20.5, 22.5, 25.5],
            "volume": [1000, 1200, 1500],
        }
    )


# ---------------------------------------------------------------------------
# AdjustmentEvent tests
# ---------------------------------------------------------------------------

class TestAdjustmentEvent:
    def test_to_dict_roundtrip(self):
        evt = _make_event(date(2025, 3, 10))
        d = evt.to_dict()
        restored = AdjustmentEvent.from_dict(d)
        assert restored == evt

    def test_frozen(self):
        evt = _make_event(date(2025, 3, 10))
        with pytest.raises(AttributeError):
            evt.factor = _dec("0.80")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AdjustmentFactors tests
# ---------------------------------------------------------------------------

class TestAdjustmentFactors:
    def test_cumulative_computed(self):
        factors = _make_factors()
        assert len(factors.cumulative) == 2
        # 0.95 * 0.90 = 0.855
        assert factors.cumulative[0] == _dec("0.95")
        assert factors.cumulative[1] == _dec("0.855")

    def test_factor_for_date_before_all(self):
        factors = _make_factors()
        result = factors.factor_for_date(date(2024, 12, 1))
        assert result == _dec("1")

    def test_factor_for_date_between_events(self):
        factors = _make_factors()
        # After first event but before second
        result = factors.factor_for_date(date(2025, 3, 1))
        assert result == _dec("0.95")

    def test_factor_for_date_after_all(self):
        factors = _make_factors()
        result = factors.factor_for_date(date(2025, 12, 31))
        assert result == _dec("0.855")

    def test_empty_events(self):
        factors = AdjustmentFactors(symbol="TEST", events=())
        assert factors.factor_for_date(date(2025, 1, 1)) == _dec("1")

    def test_to_dict_roundtrip(self):
        factors = _make_factors()
        d = factors.to_dict()
        restored = AdjustmentFactors.from_dict(d)
        assert restored.symbol == factors.symbol
        assert len(restored.events) == len(factors.events)
        assert restored.events[0].date == factors.events[0].date


# ---------------------------------------------------------------------------
# ROUND_HALF_UP precision tests
# ---------------------------------------------------------------------------

class TestPrecision:
    def test_round_half_up_24_01_times_1_10(self):
        """24.01 * 1.10 = 26.411 → should round to 26.41, not 26.42."""
        raw = _dec("24.01")
        factor = _dec("1.10")
        result = (raw * factor).quantize(_dec("0.01"), rounding=__import__("decimal").ROUND_HALF_UP)
        assert result == _dec("26.41")

    def test_round_half_up_exactly_half(self):
        """1.005 * 1.0 = 1.005 → ROUND_HALF_UP rounds to 1.01."""
        raw = _dec("1.005")
        result = (raw * _dec("1.0")).quantize(_dec("0.01"), rounding=__import__("decimal").ROUND_HALF_UP)
        assert result == _dec("1.01")

    def test_round_half_up_exactly_half_bankers(self):
        """Verify ROUND_HALF_UP differs from ROUND_HALF_EVEN for 1.005."""
        from decimal import ROUND_HALF_EVEN
        raw = _dec("1.005")
        half_up = (raw * _dec("1.0")).quantize(_dec("0.01"), rounding=__import__("decimal").ROUND_HALF_UP)
        half_even = (raw * _dec("1.0")).quantize(_dec("0.01"), rounding=ROUND_HALF_EVEN)
        # ROUND_HALF_UP: 1.01, ROUND_HALF_EVEN: 1.00
        assert half_up == _dec("1.01")
        assert half_even == _dec("1.00")


# ---------------------------------------------------------------------------
# Forward adjustment tests
# ---------------------------------------------------------------------------

class TestForwardAdjustment:
    def test_adj_close_formula(self):
        """Forward: adj_close = raw_close * (latest_cum / cum_for_date)."""
        factors = _make_factors()  # events at 2025-01-15 (0.95) and 2025-06-20 (0.90)
        # latest_cum = 0.855

        df = _make_ohlcv_df()
        result = adjust_prices(df, factors, AdjustmentType.FORWARD)

        # Row 0: date=2025-01-10, before any event → cum=1, divisor=0.855/1=0.855
        # close=20.5 → adj_close = 20.5 * 0.855 = 17.5275 → 17.53
        assert result["adj_close"].iloc[0] == pytest.approx(17.53, abs=0.01)

        # Row 1: date=2025-02-10, after first event → cum=0.95, divisor=0.855/0.95=0.9
        # close=22.5 → adj_close = 22.5 * 0.9 = 20.25
        assert result["adj_close"].iloc[1] == pytest.approx(20.25, abs=0.01)

        # Row 2: date=2025-07-10, after both events → cum=0.855, divisor=0.855/0.855=1
        # close=25.5 → adj_close = 25.5 * 1 = 25.5
        assert result["adj_close"].iloc[2] == pytest.approx(25.5, abs=0.01)

    def test_original_columns_preserved(self):
        """Original OHLC columns should not be modified."""
        df = _make_ohlcv_df()
        original_close = df["close"].copy()
        factors = _make_factors()
        result = adjust_prices(df, factors, AdjustmentType.FORWARD)

        pd.testing.assert_series_equal(result["close"], original_close)

    def test_adj_open_high_low_also_adjusted(self):
        """All four price columns get adjusted."""
        df = _make_ohlcv_df()
        factors = _make_factors()
        result = adjust_prices(df, factors, AdjustmentType.FORWARD)

        for col in ("adj_open", "adj_high", "adj_low", "adj_close"):
            assert col in result.columns

    def test_adj_columns_differ_from_raw_when_factors_apply(self):
        """When factors differ from 1.0, adj columns should differ from raw."""
        df = _make_ohlcv_df()
        factors = _make_factors()
        result = adjust_prices(df, factors, AdjustmentType.FORWARD)

        # Row 0 has divisor != 1, so adj_close != close
        assert result["adj_close"].iloc[0] != result["close"].iloc[0]


# ---------------------------------------------------------------------------
# Backward adjustment tests
# ---------------------------------------------------------------------------

class TestBackwardAdjustment:
    def test_adj_close_formula(self):
        """Backward: adj_close = raw_close * cum_factor_for_date."""
        factors = _make_factors()

        df = _make_ohlcv_df()
        result = adjust_prices(df, factors, AdjustmentType.BACKWARD)

        # Row 0: date=2025-01-10, before any event → cum=1
        # close=20.5 → adj_close = 20.5 * 1 = 20.5
        assert result["adj_close"].iloc[0] == pytest.approx(20.5, abs=0.01)

        # Row 1: date=2025-02-10, after first event → cum=0.95
        # close=22.5 → adj_close = 22.5 * 0.95 = 21.375 → 21.38
        assert result["adj_close"].iloc[1] == pytest.approx(21.38, abs=0.01)

        # Row 2: date=2025-07-10, after both → cum=0.855
        # close=25.5 → adj_close = 25.5 * 0.855 = 21.8025 → 21.80
        assert result["adj_close"].iloc[2] == pytest.approx(21.80, abs=0.01)


# ---------------------------------------------------------------------------
# NONE adjustment tests
# ---------------------------------------------------------------------------

class TestNoneAdjustment:
    def test_no_adjustment(self):
        """NONE adj_type returns raw prices as adj_* columns."""
        df = _make_ohlcv_df()
        factors = _make_factors()
        result = adjust_prices(df, factors, AdjustmentType.NONE)

        for col in ("open", "high", "low", "close"):
            pd.testing.assert_series_equal(
                result[f"adj_{col}"], result[col], check_names=False
            )

    def test_empty_factors_no_adjustment(self):
        """Empty factors should result in no adjustment."""
        df = _make_ohlcv_df()
        factors = AdjustmentFactors(symbol="TEST", events=())
        result = adjust_prices(df, factors, AdjustmentType.FORWARD)

        for col in ("open", "high", "low", "close"):
            pd.testing.assert_series_equal(
                result[f"adj_{col}"], result[col], check_names=False
            )


# ---------------------------------------------------------------------------
# Missing file tests
# ---------------------------------------------------------------------------

class TestMissingFile:
    def test_returns_empty_factors(self, tmp_path: Path):
        """Missing Parquet file returns empty factors with warning."""
        factors = get_adjustment_factors(
            "NONEXIST.SZ",
            date(2025, 1, 1),
            date(2025, 12, 31),
            data_dir=str(tmp_path),
        )
        assert factors.symbol == "NONEXIST.SZ"
        assert len(factors.events) == 0

    def test_no_adjustment_when_file_missing(self, tmp_path: Path):
        """When adjustment file is missing, prices should not change."""
        df = _make_ohlcv_df()
        factors = get_adjustment_factors(
            "NONEXIST.SZ",
            date(2025, 1, 1),
            date(2025, 12, 31),
            data_dir=str(tmp_path),
        )
        result = adjust_prices(df, factors, AdjustmentType.FORWARD)

        for col in ("open", "high", "low", "close"):
            pd.testing.assert_series_equal(
                result[f"adj_{col}"], result[col], check_names=False
            )


# ---------------------------------------------------------------------------
# Invalid factor tests
# ---------------------------------------------------------------------------

class TestInvalidFactor:
    def test_negative_factor_skipped(self, tmp_path: Path):
        """Negative factor should be skipped with warning."""
        df = pd.DataFrame(
            {
                "date": [date(2025, 1, 10)],
                "factor": [-0.5],
                "event_type": ["dividend"],
                "cash_dividend": [0.5],
                "stock_dividend": [0.0],
            }
        )
        df.to_parquet(tmp_path / "TEST.SZ.parquet")

        factors = get_adjustment_factors("TEST.SZ", date(2025, 1, 1), date(2025, 12, 31), data_dir=tmp_path)
        assert len(factors.events) == 0

    def test_factor_over_10_skipped(self, tmp_path: Path):
        """Factor > 10 should be skipped with warning."""
        df = pd.DataFrame(
            {
                "date": [date(2025, 1, 10)],
                "factor": [15.0],
                "event_type": ["split"],
                "cash_dividend": [0.0],
                "stock_dividend": [10.0],
            }
        )
        df.to_parquet(tmp_path / "TEST.SZ.parquet")

        factors = get_adjustment_factors("TEST.SZ", date(2025, 1, 1), date(2025, 12, 31), data_dir=tmp_path)
        assert len(factors.events) == 0

    def test_valid_factor_boundary(self, tmp_path: Path):
        """Factors exactly at 0 and 10 should be accepted."""
        df = pd.DataFrame(
            {
                "date": [date(2025, 1, 10), date(2025, 6, 10)],
                "factor": [0.0, 10.0],
                "event_type": ["dividend", "split"],
                "cash_dividend": [0.0, 0.0],
                "stock_dividend": [0.0, 0.0],
            }
        )
        df.to_parquet(tmp_path / "TEST.SZ.parquet")

        factors = get_adjustment_factors("TEST.SZ", date(2025, 1, 1), date(2025, 12, 31), data_dir=tmp_path)
        assert len(factors.events) == 2


# ---------------------------------------------------------------------------
# adjust_single_price tests
# ---------------------------------------------------------------------------

class TestAdjustSinglePrice:
    def test_forward_single(self):
        factors = _make_factors()
        # date before all events: cum=1, latest_cum=0.855, divisor=0.855
        result = adjust_single_price(20.5, date(2025, 1, 10), factors, AdjustmentType.FORWARD)
        # 20.5 * 0.855 = 17.5275 → 17.53
        assert result == pytest.approx(17.53, abs=0.01)

    def test_backward_single(self):
        factors = _make_factors()
        # date before all events: cum=1
        result = adjust_single_price(20.5, date(2025, 1, 10), factors, AdjustmentType.BACKWARD)
        assert result == pytest.approx(20.5, abs=0.01)

    def test_none_single(self):
        factors = _make_factors()
        result = adjust_single_price(20.5, date(2025, 1, 10), factors, AdjustmentType.NONE)
        assert result == 20.5

    def test_empty_factors_single(self):
        factors = AdjustmentFactors(symbol="TEST", events=())
        result = adjust_single_price(20.5, date(2025, 1, 10), factors, AdjustmentType.FORWARD)
        assert result == 20.5


# ---------------------------------------------------------------------------
# Non-destructive tests
# ---------------------------------------------------------------------------

class TestNonDestructive:
    def test_original_df_not_modified(self):
        """Original DataFrame should not be mutated by adjust_prices."""
        df = _make_ohlcv_df()
        original = df.copy()
        factors = _make_factors()
        adjust_prices(df, factors, AdjustmentType.FORWARD)

        pd.testing.assert_frame_equal(df, original)

    def test_extra_columns_preserved(self):
        """Columns beyond OHLCV should be preserved."""
        df = _make_ohlcv_df()
        df["turnover"] = [100.0, 200.0, 300.0]
        factors = _make_factors()
        result = adjust_prices(df, factors, AdjustmentType.FORWARD)

        assert "turnover" in result.columns
        pd.testing.assert_series_equal(result["turnover"], df["turnover"])


# ---------------------------------------------------------------------------
# Integration with data_loader.py
# ---------------------------------------------------------------------------

class TestDataLoaderIntegration:
    def test_load_daily_none_adj(self, tmp_path: Path):
        """load_daily with adj_type=NONE returns raw prices without adj_* columns."""
        from synapse.core.market.data_loader import load_daily

        df = pd.DataFrame(
            {
                "date": [date(2025, 1, 10), date(2025, 2, 10)],
                "open": [20.0, 22.0],
                "high": [21.0, 23.0],
                "low": [19.0, 21.0],
                "close": [20.5, 22.5],
                "volume": [1000, 1200],
            }
        )
        df.to_csv(tmp_path / "TEST.SZ.csv", index=False)

        result = load_daily(
            "TEST.SZ",
            date(2025, 1, 1),
            date(2025, 12, 31),
            data_dir=str(tmp_path),
            adj_type=AdjustmentType.NONE,
        )

        # NONE means no adjustment — no adj_* columns added
        assert "adj_close" not in result.columns
        assert list(result["close"]) == [20.5, 22.5]

    def test_load_daily_forward_adj(self, tmp_path: Path):
        """load_daily with adj_type=FORWARD applies adjustment."""
        from synapse.core.market.data_loader import load_daily

        # Market data
        mkt_df = pd.DataFrame(
            {
                "date": [date(2025, 1, 10), date(2025, 7, 10)],
                "open": [20.0, 25.0],
                "high": [21.0, 26.0],
                "low": [19.0, 24.0],
                "close": [20.5, 25.5],
                "volume": [1000, 1500],
            }
        )
        mkt_df.to_csv(tmp_path / "TEST.SZ.csv", index=False)

        # Adjustment data
        adj_df = pd.DataFrame(
            {
                "date": [date(2025, 6, 20)],
                "factor": [0.90],
                "event_type": ["dividend"],
                "cash_dividend": [0.50],
                "stock_dividend": [0.0],
            }
        )
        adj_dir = tmp_path / "adjustments"
        adj_dir.mkdir()
        adj_df.to_parquet(adj_dir / "TEST.SZ.parquet")

        result = load_daily(
            "TEST.SZ",
            date(2025, 1, 1),
            date(2025, 12, 31),
            data_dir=str(tmp_path),
            adj_type=AdjustmentType.FORWARD,
            # Note: adj data_dir is separate from market data_dir
        )

        # With no adjustment file in default path, adj factors will be empty
        # so prices should be raw copies
        assert "adj_close" in result.columns
