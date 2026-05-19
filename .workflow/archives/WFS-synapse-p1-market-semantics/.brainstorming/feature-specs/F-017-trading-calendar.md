# F-017: TradingCalendar Enhancement

## Overview

Upgrade `synapse/core/market/calendar.py` with frozen dataclass, session awareness (AM/PM), binary search T+N arithmetic, and optional file-based holiday override. Zero breaking changes to existing `is_trading_day` / `next_trading_day` / `trading_days_between` API.

## Data Model

```python
@dataclass(frozen=True, slots=True)
class TradingSession:
    date: date
    session: Literal["AM", "PM"]  # AM=09:30-11:30, PM=13:00-15:00

@dataclass(frozen=True, slots=True)
class TradingCalendar:
    holidays: frozenset[date]
    special_trading_days: frozenset[date]
    _sorted_days: tuple[date, ...]  # pre-sorted for binary search
```

## Interface Design

| Function | Signature | Purpose |
|----------|-----------|---------|
| `load_holidays` | `(source: str = "default") -> set[date]` | Load from cache or hardcoded fallback |
| `refresh_calendar` | `(year: int) -> None` | Fetch from API, write cache |
| `is_trading_session` | `(d: date, session: Literal["AM","PM"] = "AM") -> bool` | Session-level check |
| `trading_sessions_between` | `(start: date, end: date) -> list[TradingSession]` | All sessions in range |
| `add_trading_days` | `(d: date, n: int) -> date` | O(log n) via bisect |
| `trading_day_offset` | `(d: date, target: date) -> int` | Trading days from d to target |

## Acceptance Criteria

- [ ] `TradingCalendar` is frozen dataclass, rebuilt once per session
- [ ] `add_trading_days` uses binary search on `_sorted_days` (O(log n))
- [ ] `is_trading_day` unchanged behavior, backward compatible
- [ ] Optional `data/calendar_overrides.yaml` for custom early-closes
- [ ] `CHINA_TRADING_DAYS` override set for holiday-shifted weekdays
- [ ] Cache format: `data/market/calendar/{year}.json`
- [ ] All existing tests pass unchanged
- [ ] New tests for `add_trading_days` symmetry (add then subtract = identity)

## Dependencies

- None (P1 foundation module)

## Priority

P1 (Foundation)

## Cross-References

- **System Architect**: TradingCalendar frozen dataclass, binary search, error handling
- **Data Architect**: YAML override file, Parquet-optional design
- **Subject Matter Expert**: Holiday-shifted weekday edge case, long-holiday gap normalization
