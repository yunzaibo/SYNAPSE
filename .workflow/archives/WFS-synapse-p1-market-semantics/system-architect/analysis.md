# P1 Market Semantics Foundation - System Architecture Analysis

## Current State Summary

`synapse/core/market/` contains three modules with minimal surface area:

| Module | Lines | Key Functions |
|--------|-------|---------------|
| `calendar.py` | 162 | `is_trading_day`, `next_trading_day`, `trading_days_between` |
| `semantics.py` | 110 | `price_limit`, `validate_t1_settlement`, `is_suspended` |
| `data_loader.py` | 102 | `load_daily`, `load_daily_from_api` (stub) |

Existing integration points: `DataSource` ABC (event/datasource.py), `EastMoneyAdapter` with capital-flow fetch, `AkshareAdapter` placeholder.

---

## 1. Trading Calendar Enhancement

### Problem

Hardcoded `CHINA_HOLIDAYS` set covers only 2024-2026. No session awareness (AM/PM). T+N arithmetic is O(n) scan.

### Data Model

```python
@dataclass(frozen=True, slots=True)
class TradingSession:
    """One trading session within a day."""
    date: date
    session: Literal["AM", "PM"]  # AM=09:30-11:30, PM=13:00-15:00

@dataclass(frozen=True, slots=True)
class TradingCalendar:
    """Immutable snapshot of known trading days for a year range."""
    holidays: frozenset[date]          # non-trading weekdays
    special_trading_days: frozenset[date]  # weekend make-up days
    _sorted_days: tuple[date, ...]     # pre-sorted trading days, for binary search
```

### Interface Design

```python
# calendar.py - extend existing

# -- Dynamic loading (replaces hardcoded set) --
def load_holidays(source: str = "default") -> set[date]:
    """Load holidays from cache file or hardcoded fallback.

    source="default" -> use CHINA_HOLIDAYS constant
    source="cache" -> load from data/market/calendar/{year}.json
    """

def refresh_calendar(year: int) -> None:
    """Fetch holiday schedule from API and write cache.
    Uses EastMoneyAdapter or AkshareAdapter for live data.
    """

# -- Session awareness --
def is_trading_session(d: date, session: Literal["AM", "PM"] = "AM") -> bool:
    """Check if a specific session on date d is a trading session."""

def trading_sessions_between(start: date, end: date) -> list[TradingSession]:
    """Return all trading sessions in range."""

# -- Fast T+N arithmetic --
def add_trading_days(d: date, n: int) -> date:
    """Add n trading days to d. n < 0 goes backwards.
    Uses binary search on _sorted_days tuple.
    """

def trading_day_offset(d: date, target: date) -> int:
    """Return number of trading days from d to target. Negative if target < d."""
```

### State Management

- `TradingCalendar` is a frozen dataclass, rebuilt once per session or on `refresh_calendar()`.
- Cache format: `data/market/calendar/{year}.json` -- simple `{"holidays": [...], "special": [...]}`.
- Fallback: hardcoded `CHINA_HOLIDAYS` constant (current behavior).
- `_sorted_days` tuple enables binary search via `bisect` for O(log n) T+N.

### Integration Points

- `semantics.py` `validate_t1_settlement` calls `add_trading_days(buy_date, 1)` instead of `next_trading_day` -- avoids O(n) scan.
- Backtest engine can use `trading_sessions_between` for session-level simulation.
- No changes to `DataSource` ABC -- calendar is pure local computation.

### Error Handling

- `refresh_calendar` catches network errors, logs warning, falls back to cached/hardcoded data.
- `load_holidays` raises `FileNotFoundError` with clear message if cache file missing and no hardcoded fallback for that year.

---

## 2. Ex-Right Adjustment (fu quan)

### Problem

No adjustment support. `load_daily` returns raw prices. Factor engine needs adjusted prices for return calculations.

### Data Model

```python
class AdjustmentType(str, Enum):
    FORWARD = "forward"    # qian fu quan - adjust historical to current base
    BACKWARD = "backward"  # hou fu quan - adjust current to historical base
    NONE = "none"          # raw prices

@dataclass(frozen=True, slots=True)
class AdjustmentEvent:
    """Single corporate action event."""
    date: date
    factor: Decimal          # cumulative adjustment factor
    event_type: str          # "dividend", "split", "bonus"
    cash_dividend: Decimal   # yuan per share before tax
    stock_dividend: Decimal  # shares per 10 shares

@dataclass(frozen=True, slots=True)
class AdjustmentFactors:
    """All adjustment factors for one symbol, sorted by date."""
    symbol: str
    events: tuple[AdjustmentEvent, ...]  # sorted by date ascending
    _cumulative: tuple[Decimal, ...]     # running product of factors
```

### Interface Design

```python
# adjustment.py (new file in synapse/core/market/)

def get_adjustment_factors(
    symbol: str,
    start: date,
    end: date,
    data_dir: str | Path = "data/market",
) -> AdjustmentFactors:
    """Load adjustment factors for a symbol from local file.
    Expected: {data_dir}/adj/{symbol}.csv
    Columns: [date, event_type, cash_dividend, stock_dividend, factor]
    """

def adjust_prices(
    df: pd.DataFrame,
    factors: AdjustmentFactors,
    adj_type: AdjustmentType = AdjustmentType.FORWARD,
) -> pd.DataFrame:
    """Apply adjustment to OHLCV DataFrame.

    Adds columns: adj_open, adj_high, adj_low, adj_close.
    Original columns preserved.
    """

def adjust_single_price(
    price: float,
    target_date: date,
    factors: AdjustmentFactors,
    adj_type: AdjustmentType = AdjustmentType.FORWARD,
) -> float:
    """Adjust a single price point. Useful for real-time quote adjustment."""
```

### State Management

- `AdjustmentFactors` is immutable. Loaded once per symbol, cached by caller.
- No global state. `data_loader.py` gains an optional `adj_type` parameter.
- File-based: `data/market/adj/{symbol}.csv` -- matches existing local-first pattern.

### Integration Points

- `data_loader.py` `load_daily` gains `adj_type: AdjustmentType = AdjustmentType.NONE` parameter.
  - When `adj_type != NONE`, calls `get_adjustment_factors` + `adjust_prices` internally.
  - Backward compatible: default is `NONE`.
- `EastMoneyAdapter` can provide raw factor data via extended `data_type="adjustment"`.
- Factor engine uses `load_daily(symbol, ..., adj_type=FORWARD)` for return calculations.

### Error Handling

- Missing adjustment file: log warning, return `AdjustmentFactors` with empty events (no adjustment applied).
- Invalid factor value (< 0 or > 10): log warning, skip that event, continue with remaining.

---

## 3. Northbound Flow (bei xiang zi jin)

### Problem

No structured schema for northbound capital flow. EastMoneyAdapter already fetches per-stock capital flow but not the aggregate northbound channel data.

### Data Model

```python
class NorthChannel(str, Enum):
    HGT = "沪股通"    # Shanghai-Hong Kong Stock Connect
    SGT = "深股通"    # Shenzhen-Hong Kong Stock Connect

@dataclass(frozen=True, slots=True)
class NorthboundFlow:
    """Daily northbound capital flow record."""
    date: date
    channel: NorthChannel
    buy_amount: Decimal        # net buy in 100M yuan
    sell_amount: Decimal
    net_amount: Decimal        # buy - sell
    total_buy: Decimal         # cumulative buy
    total_sell: Decimal        # cumulative sell
    quota_used_pct: Decimal    # daily quota usage percentage
```

### Interface Design

```python
# northbound.py (new file in synapse/core/market/)

def load_northbound_flow(
    start: date,
    end: date,
    channel: NorthChannel | None = None,  # None = both channels
    data_dir: str | Path = "data/market",
) -> pd.DataFrame:
    """Load northbound flow from local CSV.
    Expected: {data_dir}/northbound/{channel.value}.csv
    Columns: [date, buy_amount, sell_amount, net_amount, total_buy, total_sell, quota_used_pct]
    """

def fetch_northbound_flow(
    adapter: DataSource,
    start: date,
    end: date,
    channel: NorthChannel | None = None,
) -> pd.DataFrame:
    """Fetch northbound flow from a DataSource adapter.
    Adapter must support data_type='northbound_flow'.
    """

def northbound_momentum(
    df: pd.DataFrame,
    window: int = 5,
) -> pd.Series:
    """Compute rolling net flow momentum (sum of net_amount over window days).
    Returns Series with same index as input.
    """
```

### State Management

- File-based local storage: `data/market/northbound/沪股通.csv`, `data/market/northbound/深股通.csv`.
- No in-memory cache. DataFrame returned directly, caller decides caching.
- `DataSource` extension: adapters return `MarketData` with `data_type="northbound_flow"`.

### Integration Points

- `EastMoneyAdapter` gains `fetch_northbound_flow()` method.
  - Endpoint: `push2.eastmoney.com/api/qt/kamt.rtmin/get` or similar.
  - Returns `MarketData(data_type="northbound_flow", payload={...})`.
- `AkshareAdapter` can wrap `ak.stock_hsgt_north_net_flow_in_em()`.
- Factor engine can consume `northbound_momentum()` as an alpha signal.

### Error Handling

- Missing local file: raise `FileNotFoundError` with clear path guidance.
- API failure: log warning, return empty DataFrame (never None).
- Invalid data (negative net_amount for cumulative fields): log warning, return as-is (data provider responsibility).

---

## 4. Index Constituent (zhi shu cheng fen)

### Problem

No tracking of which stocks belong to which index. Factor engine needs this for sector-relative calculations and index-weight constraints.

### Data Model

```python
class IndexCode(str, Enum):
    CSI300 = "000300.SH"
    CSI500 = "000905.SH"
    CSI1000 = "000852.SH"
    SSE50 = "000016.SH"
    CUSTOM = "custom"

@dataclass(frozen=True, slots=True)
class ConstituentSnapshot:
    """Point-in-time index membership."""
    index_code: str
    date: date
    members: frozenset[str]              # ticker set
    weights: dict[str, Decimal] | None   # None if weight data unavailable

@dataclass(frozen=True, slots=True)
class ConstituentChange:
    """Single membership change event."""
    date: date
    ticker: str
    action: Literal["add", "remove"]
    index_code: str
    reason: str  # "rebalance", "ipo", "delist", "suspend"
```

### Interface Design

```python
# constituent.py (new file in synapse/core/market/)

def load_constituents(
    index_code: str,
    d: date,
    data_dir: str | Path = "data/market",
) -> ConstituentSnapshot:
    """Load index constituents for a specific date.
    Expected: {data_dir}/index/{index_code}/members.csv
    Columns: [date, ticker, weight]
    Returns snapshot for the most recent date <= d.
    """

def load_constituent_changes(
    index_code: str,
    start: date,
    end: date,
    data_dir: str | Path = "data/market",
) -> list[ConstituentChange]:
    """Load all membership changes in a date range."""

def is_member(
    index_code: str,
    ticker: str,
    d: date,
) -> bool:
    """Quick membership check. Loads snapshot internally.
    For batch checks, use load_constituents + set membership.
    """

def constituent_tickers(
    index_code: str,
    d: date,
) -> frozenset[str]:
    """Return set of member tickers. Thin wrapper for readability."""
```

### State Management

- File-based: `data/market/index/{code}/members.csv`, `data/market/index/{code}/changes.csv`.
- No global cache. `ConstituentSnapshot` is immutable, suitable for caller-level caching.
- Historical snapshots: each rebalance date creates a new row set. Query resolves to latest before `d`.

### Integration Points

- `EastMoneyAdapter` / `AkshareAdapter` can provide constituent data via extended `data_type="index_constituent"`.
- Factor engine uses `is_member(CSI300, ticker, d)` for universe filtering.
- Backtest engine uses `constituent_tickers` for position constraints.

### Error Handling

- Missing index directory: raise `FileNotFoundError` with path suggestion.
- Empty members file: return snapshot with empty `members` frozenset.
- Future date requested: use latest available snapshot, log info.

---

## Cross-Cutting Concerns

### Module Organization

```
synapse/core/market/
  __init__.py          # re-exports all public APIs
  calendar.py          # existing + TradingCalendar, add_trading_days
  semantics.py         # existing (unchanged)
  data_loader.py       # existing + adj_type parameter
  adjustment.py        # NEW: ex-right adjustment
  northbound.py        # NEW: northbound flow
  constituent.py       # NEW: index constituent
  models.py            # NEW: shared dataclasses (all frozen dataclasses above)
```

`models.py` centralizes all data models to avoid circular imports.

### Dependency Direction

```
factor/  -->  market/adjustment  (adjusted prices for factors)
factor/  -->  market/constituent (universe filtering)
factor/  -->  market/northbound  (flow momentum signal)
backtest/ --> market/calendar    (trading day arithmetic)
backtest/ --> market/constituent (position constraints)
event/   --> market/northbound   (adapter integration)
```

No reverse dependencies. `market/` is a leaf module.

### Migration Strategy

1. **calendar.py** -- add `TradingCalendar` class and `add_trading_days` without breaking existing `is_trading_day` API.
2. **data_loader.py** -- add `adj_type` parameter with default `NONE`. Zero breakage.
3. **New files** -- `adjustment.py`, `northbound.py`, `constituent.py` are additive only.
4. **__init__.py** -- add new exports progressively.

### Testing Approach

Each module gets a `tests/test_market_{module}.py`:
- Unit tests with frozen fixture data (no API calls).
- Property-based tests for `add_trading_days` symmetry (adding then subtracting = identity).
- Integration tests gated behind `@pytest.mark.integration` for live adapter calls.
