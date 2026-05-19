"""Tests for Trading Calendar (China A-Shares)."""

from datetime import date, timedelta

import pytest

from synapse.core.market.calendar import (
    is_trading_day,
    next_trading_day,
    trading_days_between,
    is_trading_session,
    trading_sessions_between,
    add_trading_days,
    trading_day_offset,
    load_holidays,
    _build_calendar,
    CHINA_HOLIDAYS,
    CHINA_TRADING_DAYS,
    HALF_DAYS,
    TradingSession,
    TradingCalendar,
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


class TestCompensationWorkdays:
    """Tests for CHINA_TRADING_DAYS (weekend compensation workdays)."""

    def test_sunday_compensation_2024(self):
        # 2024-02-04 is a Sunday, but is a Spring Festival compensation workday
        assert is_trading_day(date(2024, 2, 4)) is True

    def test_sunday_compensation_2024_national_day(self):
        # 2024-09-29 is a Sunday, National Day compensation
        assert is_trading_day(date(2024, 9, 29)) is True

    def test_saturday_compensation_2024(self):
        # 2024-09-14 is a Saturday, National Day compensation
        assert is_trading_day(date(2024, 9, 14)) is True

    def test_sunday_compensation_2025(self):
        # 2025-01-26 is a Sunday, Spring Festival compensation
        assert is_trading_day(date(2025, 1, 26)) is True

    def test_regular_weekend_not_trading(self):
        # 2026-01-03 is a Saturday, no compensation
        assert is_trading_day(date(2026, 1, 3)) is False

    def test_compensation_set_is_frozen(self):
        assert isinstance(CHINA_TRADING_DAYS, frozenset)
        assert len(CHINA_TRADING_DAYS) > 0


class TestTradingSession:
    """Tests for TradingSession frozen dataclass."""

    def test_creation(self):
        ts = TradingSession(date=date(2026, 1, 5), session="AM")
        assert ts.date == date(2026, 1, 5)
        assert ts.session == "AM"

    def test_frozen(self):
        ts = TradingSession(date=date(2026, 1, 5), session="AM")
        with pytest.raises(AttributeError):
            ts.session = "PM"  # type: ignore[misc]

    def test_to_dict(self):
        ts = TradingSession(date=date(2026, 3, 15), session="PM")
        d = ts.to_dict()
        assert d == {"date": "2026-03-15", "session": "PM"}

    def test_from_dict(self):
        ts = TradingSession.from_dict({"date": "2026-03-15", "session": "PM"})
        assert ts.date == date(2026, 3, 15)
        assert ts.session == "PM"

    def test_roundtrip(self):
        original = TradingSession(date=date(2026, 6, 1), session="AM")
        restored = TradingSession.from_dict(original.to_dict())
        assert original == restored

    def test_slots(self):
        ts = TradingSession(date=date(2026, 1, 1), session="AM")
        assert not hasattr(ts, "__dict__")


class TestTradingCalendar:
    """Tests for TradingCalendar frozen dataclass."""

    def test_creation(self):
        holidays = frozenset({date(2026, 1, 1)})
        special = frozenset({date(2026, 2, 8)})
        cal = TradingCalendar(holidays=holidays, special_trading_days=special)
        assert cal.holidays == holidays
        assert cal.special_trading_days == special

    def test_frozen(self):
        cal = TradingCalendar(holidays=frozenset(), special_trading_days=frozenset())
        with pytest.raises(AttributeError):
            cal.holidays = frozenset()  # type: ignore[misc]

    def test_slots(self):
        cal = TradingCalendar(holidays=frozenset(), special_trading_days=frozenset())
        assert not hasattr(cal, "__dict__")

    def test_build_calendar(self):
        cal = _build_calendar()
        assert len(cal._sorted_days) > 500  # ~750 trading days in 3 years
        # All elements should be dates and sorted
        for i in range(len(cal._sorted_days) - 1):
            assert cal._sorted_days[i] <= cal._sorted_days[i + 1]

    def test_calendar_is_trading_day(self):
        cal = _build_calendar()
        # Monday 2026-01-05 should be trading
        assert cal.is_trading_day(date(2026, 1, 5)) is True
        # Saturday should not be
        assert cal.is_trading_day(date(2026, 1, 3)) is False
        # Holiday should not be
        assert cal.is_trading_day(date(2026, 1, 1)) is False

    def test_calendar_special_trading_day(self):
        cal = _build_calendar()
        # Compensation workday should be trading
        assert cal.is_trading_day(date(2024, 2, 4)) is True

    def test_calendar_trading_day_offset_positive(self):
        cal = _build_calendar()
        # From Mon 2026-01-05, +1 = Tue 2026-01-06
        result = cal.trading_day_offset(date(2026, 1, 5), 1)
        assert result == date(2026, 1, 6)

    def test_calendar_trading_day_offset_negative(self):
        cal = _build_calendar()
        # From Wed 2026-01-07, -2 = Mon 2026-01-05
        result = cal.trading_day_offset(date(2026, 1, 7), -2)
        assert result == date(2026, 1, 5)

    def test_calendar_trading_day_offset_zero(self):
        cal = _build_calendar()
        result = cal.trading_day_offset(date(2026, 1, 5), 0)
        assert result == date(2026, 1, 5)


class TestAddTradingDays:
    """Tests for add_trading_days with bisect-based binary search."""

    def test_add_one_day(self):
        # 2026-01-05 (Mon) + 1 = 2026-01-06 (Tue)
        result = add_trading_days(date(2026, 1, 5), 1)
        assert result == date(2026, 1, 6)

    def test_add_across_weekend(self):
        # 2026-01-09 (Fri) + 1 = 2026-01-12 (Mon)
        result = add_trading_days(date(2026, 1, 9), 1)
        assert result == date(2026, 1, 12)

    def test_add_across_holiday(self):
        # 2025-12-31 (Wed) + 1 = 2026-01-02 (Fri) — skips Jan 1 holiday
        result = add_trading_days(date(2025, 12, 31), 1)
        assert result == date(2026, 1, 2)

    def test_add_multiple_days(self):
        # 2026-01-05 (Mon) + 5 = 2026-01-12 (Mon)
        result = add_trading_days(date(2026, 1, 5), 5)
        assert result == date(2026, 1, 12)

    def test_subtract_days(self):
        # 2026-01-12 (Mon) - 1 = 2026-01-09 (Fri)
        result = add_trading_days(date(2026, 1, 12), -1)
        assert result == date(2026, 1, 9)

    def test_add_zero(self):
        result = add_trading_days(date(2026, 1, 5), 0)
        assert result == date(2026, 1, 5)

    def test_symmetry(self):
        """add_trading_days(d, n) followed by add_trading_days(result, -n) == d."""
        d = date(2026, 3, 10)
        for n in [1, 5, 20, -3, -10]:
            result = add_trading_days(d, n)
            back = add_trading_days(result, -n)
            assert back == d, f"Symmetry failed for n={n}: {d} -> {result} -> {back}"

    def test_large_offset(self):
        """Add 100 trading days — binary search correctness."""
        d = date(2026, 1, 5)
        result = add_trading_days(d, 100)
        # Manually verify by counting
        count = 0
        current = d
        while count < 100:
            current = current + timedelta(days=1)
            if is_trading_day(current):
                count += 1
        assert result == current

    def test_large_negative_offset(self):
        d = date(2026, 6, 15)
        result = add_trading_days(d, -50)
        count = 0
        current = d
        while count < 50:
            current = current - timedelta(days=1)
            if is_trading_day(current):
                count += 1
        assert result == current


class TestTradingDayOffset:
    """Tests for trading_day_offset()."""

    def test_same_day(self):
        assert trading_day_offset(date(2026, 1, 5), date(2026, 1, 5)) == 0

    def test_next_day(self):
        assert trading_day_offset(date(2026, 1, 5), date(2026, 1, 6)) == 1

    def test_one_week(self):
        # Mon to Fri = 4 trading day offset
        assert trading_day_offset(date(2026, 1, 5), date(2026, 1, 9)) == 4

    def test_negative_offset(self):
        assert trading_day_offset(date(2026, 1, 9), date(2026, 1, 5)) == -4

    def test_across_weekend(self):
        # Fri to Mon = 1 trading day offset
        assert trading_day_offset(date(2026, 1, 9), date(2026, 1, 12)) == 1

    def test_offset_consistency_with_add(self):
        """offset(d, target) should equal n where add_trading_days(d, n) == target."""
        d = date(2026, 1, 5)
        for n in [1, 3, 7, 15, -2, -5]:
            target = add_trading_days(d, n)
            offset = trading_day_offset(d, target)
            assert offset == n, f"Inconsistency: n={n}, offset={offset}"


class TestIsTradingSession:
    """Tests for is_trading_session()."""

    def test_am_on_normal_day(self):
        assert is_trading_session(date(2026, 1, 5), "AM") is True

    def test_pm_on_normal_day(self):
        assert is_trading_session(date(2026, 1, 5), "PM") is True

    def test_am_on_weekend(self):
        assert is_trading_session(date(2026, 1, 3), "AM") is False

    def test_pm_on_weekend(self):
        assert is_trading_session(date(2026, 1, 3), "PM") is False

    def test_am_on_holiday(self):
        assert is_trading_session(date(2026, 1, 1), "AM") is False

    def test_pm_on_holiday(self):
        assert is_trading_session(date(2026, 1, 1), "PM") is False

    def test_am_on_compensation_workday(self):
        assert is_trading_session(date(2024, 2, 4), "AM") is True

    def test_pm_on_compensation_workday(self):
        assert is_trading_session(date(2024, 2, 4), "PM") is True


class TestTradingSessionsBetween:
    """Tests for trading_sessions_between()."""

    def test_single_day(self):
        result = trading_sessions_between(date(2026, 1, 5), date(2026, 1, 5))
        assert len(result) == 2
        assert result[0].session == "AM"
        assert result[1].session == "PM"

    def test_empty_range(self):
        result = trading_sessions_between(date(2026, 1, 5), date(2026, 1, 1))
        assert result == []

    def test_week_range(self):
        # Mon to Fri = 5 trading days = 10 sessions
        result = trading_sessions_between(date(2026, 1, 5), date(2026, 1, 9))
        assert len(result) == 10
        # All should be TradingSession instances
        for s in result:
            assert isinstance(s, TradingSession)

    def test_excludes_weekend(self):
        # Mon to Mon (7 calendar days) = 5 trading days = 10 sessions
        result = trading_sessions_between(date(2026, 1, 5), date(2026, 1, 12))
        dates = {s.date for s in result}
        assert date(2026, 1, 10) not in dates  # Saturday
        assert date(2026, 1, 11) not in dates  # Sunday

    def test_result_type(self):
        result = trading_sessions_between(date(2026, 1, 5), date(2026, 1, 6))
        assert all(isinstance(s, TradingSession) for s in result)


class TestLoadHolidays:
    """Tests for load_holidays()."""

    def test_default_source(self):
        holidays = load_holidays("default")
        assert isinstance(holidays, frozenset)
        assert date(2026, 1, 1) in holidays

    def test_yaml_source_without_pyyaml(self):
        # Should fall back gracefully even if pyyaml is not installed
        holidays = load_holidays("yaml")
        assert isinstance(holidays, frozenset)
        # Should at least have the hardcoded holidays
        assert date(2026, 1, 1) in holidays
