"""Trading Calendar — China A-Shares trading days.

P1: Hardcoded holidays 2024-2026 (no API calls).
SSE/SZSE trading calendar with weekend and holiday detection.
"""

from __future__ import annotations

from datetime import date, timedelta


# China public holidays (non-trading days) 2024-2026
# Source: State Council holiday announcements
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
