"""Trading Calendar — China A-Shares trading days.

P1: Hardcoded holidays 2024-2026 (no API calls).
SSE/SZSE trading calendar with weekend and holiday detection.

P1.1: TradingSession/TradingCalendar dataclasses, binary-search T+N,
session awareness (AM/PM), optional YAML holiday override.
"""

from __future__ import annotations

import bisect
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hardcoded China public holidays (non-trading days) 2024-2026
# Source: State Council holiday announcements
# ---------------------------------------------------------------------------
CHINA_HOLIDAYS: set[date] = {
    # 2024
    date(2024, 1, 1),    # 元旦
    date(2024, 2, 10),   # 春节
    date(2024, 2, 11),
    date(2024, 2, 12),
    date(2024, 2, 13),
    date(2024, 2, 14),
    date(2024, 2, 15),
    date(2024, 2, 16),
    date(2024, 2, 17),
    date(2024, 4, 4),    # 清明节
    date(2024, 4, 5),
    date(2024, 4, 6),
    date(2024, 5, 1),    # 劳动节
    date(2024, 5, 2),
    date(2024, 5, 3),
    date(2024, 5, 4),
    date(2024, 5, 5),
    date(2024, 6, 8),    # 端午节
    date(2024, 6, 9),
    date(2024, 6, 10),
    date(2024, 9, 15),   # 中秋节
    date(2024, 9, 16),
    date(2024, 9, 17),
    date(2024, 10, 1),   # 国庆节
    date(2024, 10, 2),
    date(2024, 10, 3),
    date(2024, 10, 4),
    date(2024, 10, 5),
    date(2024, 10, 6),
    date(2024, 10, 7),
    # 2025
    date(2025, 1, 1),    # 元旦
    date(2025, 1, 28),   # 春节
    date(2025, 1, 29),
    date(2025, 1, 30),
    date(2025, 1, 31),
    date(2025, 2, 1),
    date(2025, 2, 2),
    date(2025, 2, 3),
    date(2025, 2, 4),
    date(2025, 4, 4),    # 清明节
    date(2025, 4, 5),
    date(2025, 4, 6),
    date(2025, 5, 1),    # 劳动节
    date(2025, 5, 2),
    date(2025, 5, 3),
    date(2025, 5, 4),
    date(2025, 5, 5),
    date(2025, 5, 31),   # 端午节
    date(2025, 6, 1),
    date(2025, 6, 2),
    date(2025, 10, 1),   # 国庆节
    date(2025, 10, 2),
    date(2025, 10, 3),
    date(2025, 10, 4),
    date(2025, 10, 5),
    date(2025, 10, 6),
    date(2025, 10, 7),
    date(2025, 10, 8),
    # 2026
    date(2026, 1, 1),    # 元旦
    date(2026, 2, 17),   # 春节
    date(2026, 2, 18),
    date(2026, 2, 19),
    date(2026, 2, 20),
    date(2026, 2, 21),
    date(2026, 2, 22),
    date(2026, 2, 23),
    date(2026, 4, 5),    # 清明节
    date(2026, 4, 6),
    date(2026, 4, 7),
    date(2026, 5, 1),    # 劳动节
    date(2026, 5, 2),
    date(2026, 5, 3),
    date(2026, 5, 4),
    date(2026, 5, 5),
    date(2026, 6, 19),   # 端午节
    date(2026, 6, 20),
    date(2026, 6, 21),
    date(2026, 10, 1),   # 国庆节
    date(2026, 10, 2),
    date(2026, 10, 3),
    date(2026, 10, 4),
    date(2026, 10, 5),
    date(2026, 10, 6),
    date(2026, 10, 7),
}

# Compensation workdays — weekends designated as trading days by State Council
# Source: State Council holiday-adjustment announcements 2024-2026
CHINA_TRADING_DAYS: frozenset[date] = frozenset({
    # 2024 Spring Festival compensation
    date(2024, 2, 4),    # Sun → work
    date(2024, 2, 18),   # Sun → work
    # 2024 National Day compensation
    date(2024, 9, 14),   # Sat → work
    date(2024, 9, 29),   # Sun → work
    # 2025 Spring Festival compensation
    date(2025, 1, 26),   # Sun → work
    date(2025, 2, 8),    # Sun → work
    # 2025 National Day compensation
    date(2025, 9, 28),   # Sun → work
    date(2025, 10, 11),  # Sat → work
})

# Half-day (PM session only) dates — year-end early close etc.
HALF_DAYS: frozenset[date] = frozenset()

# Weekend days (Saturday=5, Sunday=6)
_WEEKEND = {5, 6}


def is_trading_day(d: date) -> bool:
    """Check if a date is a China A-Shares trading day.

    A trading day is a weekday (Mon-Fri) that is not a public holiday.

    Args:
        d: The date to check.

    Returns:
        True if the date is a trading day.
    """
    # Compensation workdays override weekend check
    if d in CHINA_TRADING_DAYS:
        return True
    if d.weekday() in _WEEKEND:
        return False
    return d not in CHINA_HOLIDAYS


def next_trading_day(d: date) -> date:
    """Get the next trading day after the given date.

    If d is a trading day, returns the next trading day after d.
    If d is not a trading day, returns the next trading day.

    Args:
        d: The starting date.

    Returns:
        The next trading day.
    """
    next_day = d + timedelta(days=1)
    while not is_trading_day(next_day):
        next_day += timedelta(days=1)
    return next_day


def trading_days_between(start: date, end: date) -> list[date]:
    """Get all trading days between start and end (inclusive).

    Args:
        start: Start date (inclusive).
        end: End date (inclusive).

    Returns:
        List of trading days in the range.
    """
    if start > end:
        return []

    days: list[date] = []
    current = start
    while current <= end:
        if is_trading_day(current):
            days.append(current)
        current += timedelta(days=1)
    return days


# ---------------------------------------------------------------------------
# TradingSession — single AM or PM session on a trading day
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class TradingSession:
    """One AM or PM trading session."""

    date: date
    session: Literal["AM", "PM"]

    def to_dict(self) -> dict:
        return {"date": self.date.isoformat(), "session": self.session}

    @classmethod
    def from_dict(cls, data: dict) -> TradingSession:
        return cls(date=date.fromisoformat(data["date"]), session=data["session"])


# ---------------------------------------------------------------------------
# TradingCalendar — pre-computed sorted trading day list for binary search
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class TradingCalendar:
    """Immutable trading calendar with binary-search ready sorted tuple."""

    holidays: frozenset[date]
    special_trading_days: frozenset[date]
    _sorted_days: tuple[date, ...] = field(default_factory=tuple)

    def is_trading_day(self, d: date) -> bool:
        if d in self.special_trading_days:
            return True
        if d.weekday() in _WEEKEND:
            return False
        return d not in self.holidays

    def trading_day_offset(self, d: date, n: int) -> date:
        """Return the n-th trading day from d (negative for backward)."""
        if n == 0:
            return d
        if n > 0:
            idx = bisect.bisect_right(self._sorted_days, d)
            target = idx + n - 1
            if target < len(self._sorted_days):
                return self._sorted_days[target]
            # Fallback: extend forward from last known trading day
            last = self._sorted_days[-1] if self._sorted_days else d
            step = n - (len(self._sorted_days) - idx)
            current = last + timedelta(days=1)
            while step > 0:
                while not is_trading_day(current):
                    current += timedelta(days=1)
                step -= 1
                if step > 0:
                    current += timedelta(days=1)
            return current
        else:
            # backward
            abs_n = -n
            idx = bisect.bisect_left(self._sorted_days, d)
            target = idx - abs_n
            if target >= 0:
                return self._sorted_days[target]
            # Fallback: extend backward
            first = self._sorted_days[0] if self._sorted_days else d
            step = abs_n - idx
            current = first - timedelta(days=1)
            while step > 0:
                while not is_trading_day(current):
                    current -= timedelta(days=1)
                step -= 1
                if step > 0:
                    current -= timedelta(days=1)
            return current


def load_holidays(source: str = "default") -> frozenset[date]:
    """Load holiday set from YAML override or hardcoded fallback.

    Args:
        source: "default" uses CHINA_HOLIDAYS; "yaml" tries data/calendar_overrides.yaml.

    Returns:
        Frozenset of holiday dates.
    """
    if source == "yaml":
        yaml_path = Path(__file__).resolve().parents[2] / "data" / "calendar_overrides.yaml"
        if yaml_path.exists():
            try:
                import yaml
                with open(yaml_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                extra = set()
                for entry in data.get("extra_holidays", []):
                    extra.add(date.fromisoformat(entry))
                holidays = CHINA_HOLIDAYS | extra
                logger.info("Loaded %d holidays from %s", len(holidays), yaml_path)
                return frozenset(holidays)
            except Exception as exc:
                logger.warning("Failed to load YAML overrides: %s, falling back to default", exc)
    return frozenset(CHINA_HOLIDAYS)


def refresh_calendar(year: int) -> None:
    """Stub for future API-based calendar refresh.

    Logs that calendar refresh is not yet implemented in P1.
    """
    logger.info("refresh_calendar(%d): not implemented in P1", year)


def _build_calendar(
    holidays: frozenset[date] | None = None,
    special_trading_days: frozenset[date] | None = None,
) -> TradingCalendar:
    """Build a TradingCalendar with pre-sorted trading day tuple.

    Generates all weekdays in 2024-2026 that are not holidays
    (plus any special_trading_days), sorted for binary search.
    """
    if holidays is None:
        holidays = load_holidays()
    if special_trading_days is None:
        special_trading_days = CHINA_TRADING_DAYS

    # Build sorted list of all trading days across the known range
    start_date = date(2024, 1, 1)
    end_date = date(2026, 12, 31)
    days: list[date] = []
    current = start_date
    while current <= end_date:
        if current in special_trading_days:
            days.append(current)
        elif current.weekday() not in _WEEKEND and current not in holidays:
            days.append(current)
        current += timedelta(days=1)

    return TradingCalendar(
        holidays=holidays,
        special_trading_days=special_trading_days,
        _sorted_days=tuple(days),
    )


# Module-level default calendar instance
_default_calendar: TradingCalendar | None = None


def _get_default_calendar() -> TradingCalendar:
    global _default_calendar
    if _default_calendar is None:
        _default_calendar = _build_calendar()
    return _default_calendar


def is_trading_session(d: date, session: Literal["AM", "PM"] = "AM") -> bool:
    """Check if a given session (AM/PM) is active on date d.

    AM sessions are available on all trading days.
    PM sessions are available on all trading days except HALF_DAYS.

    Args:
        d: The date to check.
        session: "AM" or "PM".

    Returns:
        True if the session is active.
    """
    if not is_trading_day(d):
        return False
    if session == "AM":
        return True
    # PM: unavailable on half-days
    return d not in HALF_DAYS


def trading_sessions_between(start: date, end: date) -> list[TradingSession]:
    """Return all AM/PM TradingSession objects in [start, end].

    Args:
        start: Start date (inclusive).
        end: End date (inclusive).

    Returns:
        List of TradingSession, ordered by date then AM before PM.
    """
    if start > end:
        return []

    sessions: list[TradingSession] = []
    current = start
    while current <= end:
        if is_trading_session(current, "AM"):
            sessions.append(TradingSession(date=current, session="AM"))
        if is_trading_session(current, "PM"):
            sessions.append(TradingSession(date=current, session="PM"))
        current += timedelta(days=1)
    return sessions


def add_trading_days(d: date, n: int) -> date:
    """Add n trading days to date d using binary search on the default calendar.

    Uses bisect on the pre-sorted _sorted_days tuple for O(log k) lookup
    where k is the total number of known trading days.

    Args:
        d: The starting date.
        n: Number of trading days to add (negative to subtract).

    Returns:
        The resulting date.
    """
    cal = _get_default_calendar()
    return cal.trading_day_offset(d, n)


def trading_day_offset(d: date, target: date) -> int:
    """Return the number of trading days from d to target.

    Positive if target is after d, negative if before.

    Args:
        d: The starting date.
        target: The target date.

    Returns:
        Integer offset in trading days.
    """
    if d == target:
        return 0

    cal = _get_default_calendar()
    idx_d = bisect.bisect_left(cal._sorted_days, d)
    idx_target = bisect.bisect_left(cal._sorted_days, target)

    # Adjust for exact match: if target is in the sorted list, idx_target is correct
    # If d is in the sorted list, idx_d is correct
    # If not found, bisect_left gives insertion point which is the next trading day
    if idx_d < len(cal._sorted_days) and cal._sorted_days[idx_d] == d:
        pass  # exact
    # If not found, offset by whether we're before or after
    if idx_target < len(cal._sorted_days) and cal._sorted_days[idx_target] == target:
        pass  # exact

    return idx_target - idx_d
