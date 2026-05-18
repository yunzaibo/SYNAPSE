"""Tests for Trading Calendar (China A-Shares)."""

from datetime import date

import pytest

from synapse.core.market.calendar import (
    is_trading_day,
    next_trading_day,
    trading_days_between,
    CHINA_HOLIDAYS,
)


class TestIsTradingDay:
    """Tests for is_trading_day()."""

    def test_weekday_is_trading_day(self):
        # 2026-01-05 is a Monday
        assert is_trading_day(date(2026, 1, 5)) is True

    def test_weekend_not_trading_day(self):
        # 2026-01-03 is a Saturday
        assert is_trading_day(date(2026, 1, 3)) is False
        # 2026-01-04 is a Sunday
        assert is_trading_day(date(2026, 1, 4)) is False

    def test_new_year_2026_not_trading_day(self):
        # 2026-01-01 元旦
        assert is_trading_day(date(2026, 1, 1)) is False

    def test_new_year_2026_following_day(self):
        # 2026-01-02 is a trading day (元旦假期 only covers Jan 1)
        assert is_trading_day(date(2026, 1, 2)) is True

    def test_normal_trading_day_2026(self):
        # 2026-01-05 is a Monday, not a holiday
        assert is_trading_day(date(2026, 1, 5)) is True

    def test_spring_festival_2026(self):
        # 春节假期
        assert is_trading_day(date(2026, 2, 17)) is False
        assert is_trading_day(date(2026, 2, 18)) is False
        assert is_trading_day(date(2026, 2, 19)) is False

    def test_national_day_2025(self):
        # 国庆节假期
        assert is_trading_day(date(2025, 10, 1)) is False
        assert is_trading_day(date(2025, 10, 7)) is False

    def test_christmas_not_holiday_in_china(self):
        # 圣诞节不是中国法定假日
        assert is_trading_day(date(2026, 12, 25)) is True


class TestNextTradingDay:
    """Tests for next_trading_day()."""

    def test_next_from_weekday(self):
        # 2026-01-05 (Mon) -> 2026-01-06 (Tue)
        result = next_trading_day(date(2026, 1, 5))
        assert result == date(2026, 1, 6)

    def test_next_from_friday(self):
        # 2026-01-09 (Fri) -> 2026-01-12 (Mon)
        result = next_trading_day(date(2026, 1, 9))
        assert result == date(2026, 1, 12)

    def test_next_from_holiday(self):
        # 2026-01-01 (Holiday) -> 2026-01-02 (Fri) is next trading day
        result = next_trading_day(date(2026, 1, 1))
        assert result == date(2026, 1, 2)

    def test_next_across_spring_festival(self):
        # 2026-02-13 (Fri) -> 2026-02-16 (Mon) is next trading day
        result = next_trading_day(date(2026, 2, 13))
        assert result == date(2026, 2, 16)


class TestTradingDaysBetween:
    """Tests for trading_days_between()."""

    def test_single_day_range(self):
        # 2026-01-05 (Mon) is a trading day
        result = trading_days_between(date(2026, 1, 5), date(2026, 1, 5))
        assert result == [date(2026, 1, 5)]

    def test_week_range(self):
        # 2026-01-05 (Mon) to 2026-01-09 (Fri)
        result = trading_days_between(date(2026, 1, 5), date(2026, 1, 9))
        assert len(result) == 5
        assert result[0] == date(2026, 1, 5)
        assert result[-1] == date(2026, 1, 9)

    def test_holiday_excluded(self):
        # 2026-01-01 (Holiday) to 2026-01-05 (Mon)
        result = trading_days_between(date(2026, 1, 1), date(2026, 1, 5))
        assert date(2026, 1, 1) not in result
        assert date(2026, 1, 5) in result

    def test_empty_range(self):
        # start > end
        result = trading_days_between(date(2026, 1, 5), date(2026, 1, 1))
        assert result == []

    def test_spanning_holiday(self):
        # 2026-01-01 (Holiday) to 2026-01-09 (Fri)
        # Jan 1 (holiday), Jan 2 (trading), Jan 3-4 (weekend)
        # Trading days: Jan 2, 5, 6, 7, 8, 9 = 6 days
        result = trading_days_between(date(2026, 1, 1), date(2026, 1, 9))
        assert date(2026, 1, 1) not in result
        assert len(result) == 6
