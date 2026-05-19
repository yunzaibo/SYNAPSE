# Implementation Plan: P1 Market Semantics Foundation

**Session**: WFS-synapse-p1-market-semantics
**Created**: 2026-05-19
**Complexity**: Medium
**Total Tasks**: 6
**Execution Waves**: 2

---

## Overview

This plan implements the P1 Market Semantics Foundation for SYNAPSE — four independent modules that form the A-share market semantics layer. All changes are strictly additive: no existing API signatures change, no existing tests break.

### Scope

| Feature | Module | Type |
|---------|--------|------|
| F-017 TradingCalendar Enhancement | calendar.py (upgrade) | Extend existing |
| F-018 Ex-Right Adjustment (复权) | adjustment.py (new) | New module + data_loader integration |
| F-019 Northbound Flow (北向资金) | northbound.py (new) | New module + DataSource adapter |
| F-020 Index Constituent (指数成分) | constituent.py (new) | New module |

### Key Constraints

1. **Zero breaking changes** — all existing public APIs preserved unchanged
2. **Frozen dataclasses** with `slots=True` for all new data models
3. **`__future__.annotations`** at top of every file
4. **`to_dict()` / `from_dict()`** serialization pattern where applicable
5. **Decimal with `ROUND_HALF_UP`** for all financial calculations
6. **`source` field** on all data for provenance tracking
7. **Parquet-based storage** for adjustment factors, northbound flow, index constituents
8. **Test command**: `py -m pytest -p no:asyncio`

---

## Architecture

### Module Layout (after implementation)

```
synapse/core/market/
├── __init__.py          # Updated: all new exports
├── calendar.py          # Upgraded: TradingSession, TradingCalendar, bisect
├── semantics.py         # Unchanged
├── data_loader.py       # Modified: adj_type parameter added
├── adjustment.py        # NEW: Ex-right adjustment
├── northbound.py        # NEW: Northbound flow
└── constituent.py       # NEW: Index constituent

tests/unit/
├── test_market_calendar.py      # Extended
├── test_market_semantics.py     # Unchanged
├── test_market_adjustment.py    # NEW
├── test_market_northbound.py    # NEW
└── test_market_constituent.py   # NEW
```

### Dependency Graph

```
IMPL-001 (Calendar)       ──┐
IMPL-002 (Adjustment)     ──┤
IMPL-003 (Northbound)     ──┼──> IMPL-005 (Integration) ──> IMPL-006 (Regression)
IMPL-004 (Constituent)    ──┘
```

All four feature tasks (IMPL-001 through IMPL-004) have zero inter-dependencies and could execute in parallel. However, single-module execution is preferred for simplicity.

---

## Implementation Strategy

### Wave 1: Core Feature Implementation

Four independent modules, executed sequentially. Each task produces working code + tests. All existing tests must pass after each task.

### Wave 2: Integration & Verification

Package-level exports update and full regression. Depends on all Wave 1 tasks completing.

---

## Task Breakdown

### Wave 1 — Core Features

#### IMPL-001: TradingCalendar Enhancement (F-017)

**File**: `synapse/core/market/calendar.py` (upgrade)
**Tests**: `tests/unit/test_market_calendar.py` (extend)
**Estimated**: 1.5-2 hours

**What to implement**:

1. **TradingSession frozen dataclass** — `(date, session: Literal["AM","PM"])`
2. **TradingCalendar frozen dataclass** — holds `holidays`, `special_trading_days`, pre-sorted `_sorted_days` tuple
3. **`load_holidays(source="default")`** — load from cache or hardcoded `CHINA_HOLIDAYS` fallback
4. **`refresh_calendar(year)`** — fetch from API, write cache (stub in P1)
5. **`is_trading_session(d, session="AM")`** — session-level check
6. **`trading_sessions_between(start, end)`** — all AM/PM sessions in range
7. **`add_trading_days(d, n)`** — O(log n) via `bisect` on sorted tuple
8. **`trading_day_offset(d, target)`** — trading days from d to target
9. **Optional `data/calendar_overrides.yaml`** — custom early-closes, holiday-shifted trading days
10. **`CHINA_TRADING_DAYS`** override set for compensation workdays

**Acceptance criteria**:
- `add_trading_days(d, 5) - 5 steps back = d` (symmetry test)
- `is_trading_day`, `next_trading_day`, `trading_days_between` unchanged behavior
- All existing tests pass unchanged

**Key decisions**:
- Binary search via Python `bisect` module on `_sorted_days` tuple
- `_sorted_days` computed at `TradingCalendar` init from `CHINA_HOLIDAYS` range
- YAML override is optional; missing file = silent fallback to hardcoded

---

#### IMPL-002: Ex-Right Adjustment Module (F-018)

**File**: `synapse/core/market/adjustment.py` (new)
**Modified**: `synapse/core/market/data_loader.py` (add adj_type param)
**Tests**: `tests/unit/test_market_adjustment.py` (new)
**Estimated**: 1.5-2 hours

**What to implement**:

1. **`AdjustmentType` enum** — FORWARD, BACKWARD, NONE
2. **`AdjustmentEvent` frozen dataclass** — date, factor (Decimal), event_type, cash_dividend, stock_dividend
3. **`AdjustmentFactors` frozen dataclass** — symbol, events tuple, cumulative tuple
4. **`get_adjustment_factors(symbol, start, end, data_dir)`** — load from `data/adjustments/{symbol}.parquet`
5. **`adjust_prices(df, factors, adj_type)`** — add adj_open/adj_high/adj_low/adj_close columns
6. **`adjust_single_price(price, target_date, factors, adj_type)`** — single point adjustment
7. **`data_loader.py` modification** — `load_daily()` gains `adj_type: AdjustmentType = AdjustmentType.NONE` parameter

**Acceptance criteria**:
- Original OHLCV columns preserved (non-destructive)
- Forward-adjusted default for display; backward for cumulative returns
- Missing adjustment file -> log warning, return empty factors (no adjustment)
- Invalid factor (< 0 or > 10) -> log warning, skip that event
- `ROUND_HALF_UP` for all Decimal math
- Default `adj_type=NONE` preserves `load_daily()` backward compatibility

---

#### IMPL-003: Northbound Flow Module (F-019)

**File**: `synapse/core/market/northbound.py` (new)
**Tests**: `tests/unit/test_market_northbound.py` (new)
**Estimated**: 1.5-2 hours

**What to implement**:

1. **`NorthChannel` enum** — HGT (沪股通), SGT (深股通)
2. **`NorthboundFlow` frozen dataclass** — date, channel, buy_amount, sell_amount, net_amount, total_buy, total_sell, quota_used_pct (all Decimal)
3. **`load_northbound_flow(start, end, channel, data_dir)`** — load from `data/market/northbound/` Parquet monthly files
4. **`fetch_northbound_flow(adapter, start, end, channel)`** — fetch via DataSource adapter with `data_type="northbound_flow"`
5. **`northbound_momentum(df, window=5)`** — rolling net flow momentum as pd.Series
6. **`northbound_to_signals(records, threshold=1e9)`** — large flow -> list of Signal-compatible dicts
7. **`index_change_to_signals(old, new)`** — index changes -> list of Signal-compatible dicts

**Acceptance criteria**:
- `NorthChannel` enum covers HGT and SGT
- Load returns DataFrame matching `NorthboundFlow` fields
- Missing local file -> `FileNotFoundError` with clear path guidance
- API failure -> log warning, return empty DataFrame (never None)
- All data includes `source` field for provenance tracking
- Signal output compatible with `watchlist_generator.py` format

**Dependencies on existing code**:
- `DataSource` ABC from `synapse/event/datasource.py`
- `Signal` dataclass pattern from `synapse/core/schemas/signal.py`

---

#### IMPL-004: Index Constituent Module (F-020)

**File**: `synapse/core/market/constituent.py` (new)
**Tests**: `tests/unit/test_market_constituent.py` (new)
**Estimated**: 1.5-2 hours

**What to implement**:

1. **`IndexCode` enum** — CSI300 (000300.SH), CSI500 (000905.SH), CSI1000 (000852.SH), SSE50 (000016.SH), CUSTOM
2. **`ConstituentSnapshot` frozen dataclass** — index_code, date, members (frozenset[str]), weights (dict[str, Decimal] | None)
3. **`ConstituentChange` frozen dataclass** — date, ticker, action (add/remove), index_code, reason
4. **`load_constituents(index_code, d, data_dir)`** — load latest snapshot <= target date
5. **`load_constituent_changes(index_code, start, end, data_dir)`** — all changes in range, sorted by date
6. **`is_member(index_code, ticker, d)`** — quick membership check
7. **`constituent_tickers(index_code, d)`** — frozenset[str] of member tickers

**Acceptance criteria**:
- `IndexCode` enum covers all 4 major indices + CUSTOM
- `load_constituents` resolves to latest snapshot <= target date
- Missing index directory -> `FileNotFoundError` with path suggestion
- Empty members file -> snapshot with empty `frozenset`
- Future date requested -> use latest available, log info
- File layout: `data/market/index/{code}/members.csv` and `changes.csv`

---

### Wave 2 — Integration & Verification

#### IMPL-005: Market Package Integration & Exports

**File**: `synapse/core/market/__init__.py` (update)
**Depends on**: IMPL-001, IMPL-002, IMPL-003, IMPL-004
**Estimated**: 0.5 hours

Update `__init__.py` to export all new public symbols:
- From calendar: `TradingSession`, `TradingCalendar`, `add_trading_days`, `trading_day_offset`, `is_trading_session`, `trading_sessions_between`, `load_holidays`
- From adjustment: `AdjustmentType`, `AdjustmentEvent`, `AdjustmentFactors`, `adjust_prices`, `adjust_single_price`, `get_adjustment_factors`
- From northbound: `NorthChannel`, `NorthboundFlow`, `load_northbound_flow`, `fetch_northbound_flow`, `northbound_momentum`
- From constituent: `IndexCode`, `ConstituentSnapshot`, `ConstituentChange`, `load_constituents`, `is_member`, `constituent_tickers`

Verify no circular imports.

---

#### IMPL-006: Regression Verification & Cleanup

**Depends on**: IMPL-005
**Estimated**: 0.5 hours

1. Run `py -m pytest -p no:asyncio` — confirm 0 failures
2. Grep for hardcoded user paths (`/Users/`, personal info)
3. Verify all new code has `__future__.annotations`
4. Confirm frozen dataclass convention: `@dataclass(frozen=True, slots=True)`
5. Check docstrings match implementation
6. Update CHANGELOG.md if new version warranted
7. Generate test report

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Calendar bisect breaks existing API | Low | Existing functions unchanged; new functions are additive |
| Adjustment ROUND_HALF_UP precision drift | Low | Use Decimal throughout; test with known dividend/split data |
| Northbound adapter mismatch | Medium | Design for DataSource ABC; test with mock adapter |
| Parquet schema evolution | Low | P1 uses simple schemas; version field in data |
| Circular imports on __init__.py | Low | Import at function level if needed |

---

## File Inventory

### New Files (6)

| File | Purpose |
|------|---------|
| `synapse/core/market/adjustment.py` | Ex-right price adjustment |
| `synapse/core/market/northbound.py` | Northbound flow data |
| `synapse/core/market/constituent.py` | Index constituent tracking |
| `tests/unit/test_market_adjustment.py` | Adjustment tests |
| `tests/unit/test_market_northbound.py` | Northbound tests |
| `tests/unit/test_market_constituent.py` | Constituent tests |

### Modified Files (3)

| File | Change |
|------|--------|
| `synapse/core/market/calendar.py` | Upgrade with frozen dataclass, bisect, session awareness |
| `synapse/core/market/data_loader.py` | Add adj_type parameter to load_daily() |
| `synapse/core/market/__init__.py` | Add new exports to __all__ |
