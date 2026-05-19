"""Integration tests for P1 TradingCalendar -> BacktestEngine integration.

Validates that the backtest engine correctly uses TradingCalendar to
select rebalance dates, ensuring no rebalance on weekends/holidays.

Covers IMPL-008 P1 calendar integration requirements:
- Rebalance dates are valid trading days
- Monthly rebalance uses first trading day of each month
- No rebalance on weekends or holidays
- TradingCalendar functions are correctly integrated
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from synapse.backtest.config import BacktestConfig
from synapse.backtest.engine import BacktestEngine, BacktestRequest
from synapse.core.market.calendar import (
    CHINA_HOLIDAYS,
    CHINA_TRADING_DAYS,
    is_trading_day,
    trading_days_between,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_data_for_dates(
    start_date: str,
    end_date: str,
    n_stocks: int = 30,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.Series]:
    """Create factor data and forward returns for a specific date range.

    Uses TradingCalendar dates to ensure alignment with rebalance dates.
    """
    rng = np.random.RandomState(seed)
    # Get actual trading days and take first of each month
    tdays = trading_days_between(
        date.fromisoformat(start_date), date.fromisoformat(end_date)
    )
    monthly_dates = []
    seen_months = set()
    for d in tdays:
        key = (d.year, d.month)
        if key not in seen_months:
            monthly_dates.append(pd.Timestamp(d))
            seen_months.add(key)
    tickers = [f"SZ{str(i).zfill(6)}" for i in range(n_stocks)]
    idx = pd.MultiIndex.from_product([monthly_dates, tickers], names=["date", "ticker"])

    fv_df = pd.DataFrame(rng.randn(len(idx)), index=idx, columns=["factor"])
    fr = pd.Series(rng.randn(len(idx)) * 0.01, index=idx, name="fwd_ret")

    return fv_df, fr


def _run_backtest(
    fv_df: pd.DataFrame,
    fr: pd.Series,
    start_date: str,
    end_date: str,
    rebalance_frequency: str = "monthly",
    **config_overrides,
):
    """Helper to run a backtest with given data and config."""
    config = BacktestConfig(
        universe="calendar-test",
        benchmark="CSI300",
        start_date=start_date,
        end_date=end_date,
        rebalance_frequency=rebalance_frequency,
        transaction_cost_bps=10.0,
        slippage_bps=5.0,
        **config_overrides,
    )
    engine = BacktestEngine()
    return engine.run(BacktestRequest(
        factor_values=fv_df,
        forward_returns=fr,
        config=config,
    ))


# ---------------------------------------------------------------------------
# Test 1: Rebalance dates match calendar
# ---------------------------------------------------------------------------


class TestRebalanceDatesMatchCalendar:
    """Verify rebalance dates are valid trading days."""

    def test_rebalance_dates_match_calendar(self):
        """All quintile portfolio dates should be valid trading days."""
        fv_df, fr = _make_data_for_dates("2024-01-01", "2024-12-31")
        result = _run_backtest(fv_df, fr, "2024-01-01", "2024-12-31")

        assert result.status == "succeeded"
        assert len(result.quintile_portfolios) > 0

        for qp in result.quintile_portfolios:
            d = qp.date
            # date object: check weekday (Mon=0 .. Fri=4)
            assert d.weekday() < 5, f"Portfolio date {d} falls on a weekend"
            # Should not be a Chinese holiday
            assert d not in CHINA_HOLIDAYS, f"Portfolio date {d} is a holiday"

    def test_no_weekend_rebalance(self):
        """No rebalance should occur on Saturday or Sunday."""
        # Use a 2-year range to get more data points
        fv_df, fr = _make_data_for_dates("2024-01-01", "2025-12-31", n_stocks=40)
        result = _run_backtest(fv_df, fr, "2024-01-01", "2025-12-31")

        assert result.status == "succeeded"
        for qp in result.quintile_portfolios:
            assert qp.date.weekday() < 5, f"Weekend date in portfolio: {qp.date}"

    def test_no_holiday_rebalance(self):
        """No rebalance should occur on Chinese public holidays."""
        # Check specifically around known holiday periods
        fv_df, fr = _make_data_for_dates("2024-01-01", "2024-12-31", n_stocks=40)
        result = _run_backtest(fv_df, fr, "2024-01-01", "2024-12-31")

        holiday_dates_in_range = [
            d for d in CHINA_HOLIDAYS
            if date(2024, 1, 1) <= d <= date(2024, 12, 31)
        ]

        portfolio_dates = {qp.date for qp in result.quintile_portfolios}
        overlap = portfolio_dates & set(holiday_dates_in_range)

        assert len(overlap) == 0, f"Rebalance on holiday(s): {overlap}"


# ---------------------------------------------------------------------------
# Test 2: Monthly rebalance uses first trading day
# ---------------------------------------------------------------------------


class TestMonthlyRebalanceFirstDay:
    """Verify monthly rebalance uses the first trading day of each month."""

    def test_monthly_rebalance_first_day(self):
        """Monthly rebalance should use the first trading day of each month."""
        # Use 2024 data where we know the calendar
        fv_df, fr = _make_data_for_dates("2024-01-01", "2024-12-31", n_stocks=50)
        result = _run_backtest(fv_df, fr, "2024-01-01", "2024-12-31")

        assert result.status == "succeeded"
        assert len(result.quintile_portfolios) > 0

        for qp in result.quintile_portfolios:
            d = qp.date
            # Verify this date is the first trading day of its month
            # Get all trading days in that month
            month_start = d.replace(day=1)
            if d.month == 12:
                month_end = d.replace(year=d.year + 1, month=1, day=1)
            else:
                month_end = d.replace(month=d.month + 1, day=1)

            trading_days_in_month = trading_days_between(month_start, month_end)
            if trading_days_in_month:
                assert d == trading_days_in_month[0], (
                    f"Rebalance date {d} is not the first trading day "
                    f"of its month (expected {trading_days_in_month[0]})"
                )

    def test_monthly_rebalance_covers_all_months(self):
        """Monthly rebalance should produce a portfolio for each month in range."""
        fv_df, fr = _make_data_for_dates("2024-01-01", "2024-12-31", n_stocks=50)
        result = _run_backtest(fv_df, fr, "2024-01-01", "2024-12-31")

        assert result.status == "succeeded"

        # Collect months covered by rebalance dates
        months_covered = {(qp.date.year, qp.date.month) for qp in result.quintile_portfolios}

        # Expect 12 months (or close to it, depending on data availability)
        # Factor data is generated on business month starts, so we should get
        # at least 10 months
        assert len(months_covered) >= 10, (
            f"Expected at least 10 months, got {len(months_covered)}: {months_covered}"
        )


# ---------------------------------------------------------------------------
# Test 3: Non-trading days excluded
# ---------------------------------------------------------------------------


class TestNonTradingDaysExcluded:
    """Verify no rebalance on weekends/holidays."""

    def test_non_trading_days_excluded(self):
        """Trading days between function excludes weekends and holidays."""
        # January 2024: 1st is holiday (New Year), 6-7 are weekend
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        trading_days = trading_days_between(start, end)

        # Jan 1 (Monday) is a holiday -- should not be in list
        assert date(2024, 1, 1) not in trading_days

        # Jan 6 (Saturday) and Jan 7 (Sunday) should not be in list
        assert date(2024, 1, 6) not in trading_days
        assert date(2024, 1, 7) not in trading_days

        # All dates in the list should be valid trading days
        for d in trading_days:
            assert is_trading_day(d), f"{d} is not a trading day"

    def test_compensation_workdays_included(self):
        """Compensation workdays (weekend trading days) are included."""
        # Feb 4, 2024 is a Sunday but is a compensation workday for Spring Festival
        assert is_trading_day(date(2024, 2, 4)) is True

        # Sep 14, 2024 is a Saturday but is a compensation workday for National Day
        assert is_trading_day(date(2024, 9, 14)) is True

    def test_spring_festival_holidays_excluded(self):
        """Spring Festival holiday period (Feb 10-17, 2024) has no trading days."""
        spring_dates = [
            date(2024, 2, 10),
            date(2024, 2, 11),
            date(2024, 2, 12),
            date(2024, 2, 13),
            date(2024, 2, 14),
            date(2024, 2, 15),
            date(2024, 2, 16),
            date(2024, 2, 17),
        ]
        for d in spring_dates:
            assert is_trading_day(d) is False, f"{d} should be a holiday"

    def test_national_day_holidays_excluded(self):
        """National Day holiday period (Oct 1-7, 2024) has no trading days."""
        national_dates = [
            date(2024, 10, 1),
            date(2024, 10, 2),
            date(2024, 10, 3),
            date(2024, 10, 4),
            date(2024, 10, 5),
            date(2024, 10, 6),
            date(2024, 10, 7),
        ]
        for d in national_dates:
            assert is_trading_day(d) is False, f"{d} should be a holiday"

    def test_backtest_respects_calendar(self):
        """Backtest engine does not create portfolios on holidays."""
        # Use a range that includes Chinese holidays
        fv_df, fr = _make_data_for_dates("2024-01-01", "2024-12-31", n_stocks=40)
        result = _run_backtest(fv_df, fr, "2024-01-01", "2024-12-31")

        assert result.status == "succeeded"

        for qp in result.quintile_portfolios:
            assert is_trading_day(qp.date), (
                f"Rebalance date {qp.date} is not a trading day"
            )

    def test_weekly_rebalance_respects_calendar(self):
        """Weekly rebalance also respects trading calendar."""
        fv_df, fr = _make_data_for_dates("2024-01-01", "2024-06-30", n_stocks=40)
        result = _run_backtest(
            fv_df, fr, "2024-01-01", "2024-06-30",
            rebalance_frequency="weekly",
        )

        assert result.status == "succeeded"
        for qp in result.quintile_portfolios:
            assert is_trading_day(qp.date), (
                f"Weekly rebalance on non-trading day: {qp.date}"
            )
