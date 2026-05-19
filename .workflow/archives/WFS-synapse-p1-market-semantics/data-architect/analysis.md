# P1 Market Semantics — Data Architecture Analysis

## 1. Data Schema Design

### 1.1 Existing Foundations

The codebase already defines two relevant temporal primitives:

- **`MarketSession`** enum in `synapse/core/temporal.py` — `NORMAL | HALF_DAY | HOLIDAY | SUSPENDED`
- **`MarketContext`** dataclass in `synapse/core/schemas/base.py` — `research_date`, `market_date`, `trading_session`

These are embedded in every research object via `BaseSchema.market_context`. The new schemas below complement (not replace) these.

### 1.2 Proposed Dataclasses

All new dataclasses live in `synapse/core/market/schemas.py`. They follow the project convention: `@dataclass`, `to_dict()` / `from_dict()` class methods, `__future__.annotations`.

```python
@dataclass
class TradingSession:
    """A single trading session within a day."""
    date: date
    session_type: str  # "morning" | "afternoon" | "full"
    is_trading_day: bool
    holiday_name: str | None = None  # populated for non-trading days

@dataclass
class AdjustmentRecord:
    """A single price adjustment factor (ex-dividend, split, etc.)."""
    date: date
    factor: float        # forward adjustment: >1.0; backward: <1.0
    adj_type: str        # "forward" | "backward"
    source: str          # e.g. "eastmoney", "akshare"
    ticker: str = ""     # empty = market-wide (rare)

@dataclass
class NorthboundFlowRecord:
    """Daily northbound (HK-SH/SZ) capital flow record."""
    date: date
    direction: str       # "north" (HK->A) | "south" (A->HK)
    net_flow: float      # net buy in CNY (positive = net inflow)
    buy_amount: float    # total buy
    sell_amount: float   # total sell
    source: str
    timestamp: datetime | None = None

@dataclass
class IndexConstituent:
    """Point-in-time index membership snapshot."""
    index_id: str        # e.g. "000300.SH" (CSI 300)
    ticker: str          # member stock ticker
    effective_date: date # when this membership started
    weight: float = 0.0  # weight in the index (0 = unknown)
    source: str = ""
```

### 1.3 Design Decisions

| Decision | Rationale |
|----------|-----------|
| `adj_type: str` not `Enum` | Matches `SymbolType` pattern but keeps serialization simple; P1 has only two types |
| `factor: float` not `Decimal` | Consistent with `FactorEngine` which works in `pd.Series(float)`. `Decimal` is used only in `semantics.py` for price limits (exact boundary checks) |
| `NorthboundFlowRecord` includes `buy_amount`/`sell_amount` | Enables net flow derivation and gross flow analysis without re-fetching |
| `IndexConstituent.weight: float = 0.0` | Default 0.0 signals "weight unknown" rather than None, avoiding Optional in hot paths |
| Separate from `BaseSchema` | These are raw market data records, not research objects. They don't need `id`, `status`, `created_at`, `market_context` |

---

## 2. Storage Strategy

### 2.1 Trading Calendar

**Recommendation: Keep hardcoded, add file override.**

| Aspect | Decision |
|--------|----------|
| Primary source | `CHINA_HOLIDAYS` set in `calendar.py` (already works) |
| Override mechanism | Optional `data/calendar_overrides.yaml` for custom early-closes, late-opens |
| File format | YAML (matches project convention in `DatasetMetadata.to_yaml()`) |
| Why not API | Calendar is deterministic 1-2 years ahead; API adds latency + failure mode for zero benefit |

The existing `is_trading_day()` / `next_trading_day()` / `trading_days_between()` functions remain unchanged. `TradingSession` dataclass adds session granularity (morning/afternoon/full) on top.

### 2.2 Adjustment Factors

**Recommendation: Parquet files in `data/adjustments/`.**

| Aspect | Decision |
|--------|----------|
| Format | Parquet (columnar, efficient for date-range scans) |
| File layout | `data/adjustments/{ticker}.parquet` — one file per ticker |
| Schema | `(date, factor, adj_type, source)` per row |
| Why not SQLite | Adjustment data is append-only and read in bulk for price correction. Parquet integrates directly with `pd.read_parquet()` and the existing `data_loader.py` pattern |
| Fallback | If ticker has no adjustment file, treat factor as 1.0 (no adjustment) |

`AdjustmentRecord` serves as the in-memory schema. On disk, Parquet columns match the dataclass fields minus `ticker` (which is the file partition key).

### 2.3 Northbound Flow

**Recommendation: Append-only Parquet by month.**

| Aspect | Decision |
|--------|----------|
| Format | Parquet |
| File layout | `data/northbound/YYYY-MM.parquet` — one file per month |
| Schema | `(date, direction, net_flow, buy_amount, sell_amount, source, timestamp)` |
| Append strategy | Load existing month file, concat new row, write back. Monthly granularity keeps files small (~22 rows/month) |
| Query pattern | Load full month for analysis; load single date for daily watchlist |

Why monthly not daily: northbound flow is queried by date range (last N days) not random access. Monthly files reduce file count while keeping individual files under 1KB.

### 2.4 Index Constituents

**Recommendation: Parquet snapshot files in `data/index/`.**

| Aspect | Decision |
|--------|----------|
| Format | Parquet |
| File layout | `data/index/{index_id}_{YYYY-MM-DD}.parquet` — full snapshot per rebalance date |
| Schema | `(ticker, weight, source)` per row; `index_id` and `effective_date` are in filename |
| Query pattern | Find latest snapshot <= target_date via sorted filename scan |
| Why not SQLite | Point-in-time lookups need "latest snapshot before date" — filename-based approach is simpler than maintaining a SQLite index for ~4 rebalances/year |

For P1, 2-3 index files (CSI 300, CSI 500, CSI 1000) suffice. The `IndexConstituent` dataclass is the in-memory representation.

---

## 3. Data Pipeline

### 3.1 Architecture Overview

```
DataSource adapters (EastMoney, Akshare)
        |
        v
  MarketData records
        |
   +----+----+
   |         |
   v         v
FactorEngine   MarketSemanticsLayer
(compute)      (calendar, adjustments,
                northbound, index)
        |              |
        v              v
  Factor values    Watchlist generator
                   (daily research queue)
```

### 3.2 DataSource -> Market Semantics

The existing `DataSource.fetch()` returns `list[MarketData]`. The market semantics layer consumes this via **adapter-specific transformers**:

```python
# synapse/core/market/transformers.py (new)

def market_data_to_adjustments(
    records: list[MarketData], source: str
) -> list[AdjustmentRecord]:
    """Convert raw MarketData (data_type='adjustment') to AdjustmentRecord."""

def market_data_to_northbound(
    records: list[MarketData], source: str
) -> list[NorthboundFlowRecord]:
    """Convert raw MarketData (data_type='northbound') to NorthboundFlowRecord."""
```

These transformers are **pure functions** — no side effects, easy to test. They filter by `data_type` and map `payload` dicts to typed dataclasses.

### 3.3 FactorEngine Consumption

The `FactorEngine` currently receives `DataSource.fetch()` output directly. For P1, **no changes to FactorEngine are needed**. Adjusted prices are a pre-processing concern:

```python
# New function in synapse/core/market/data_loader.py

def load_adjusted_daily(
    symbol: str,
    start: date,
    end: date,
    data_dir: str | Path = "data/market",
    adj_dir: str | Path = "data/adjustments",
) -> pd.DataFrame:
    """Load daily OHLCV with forward-adjusted close prices.

    Wraps existing load_daily() and applies AdjustmentRecord factors.
    Backward-compatible: if no adjustment file exists, returns raw prices.
    """
    df = load_daily(symbol, start, end, data_dir)
    adj_path = Path(adj_dir) / f"{symbol}.parquet"
    if adj_path.exists():
        adj_df = pd.read_parquet(adj_path)
        # Apply forward adjustment: multiply close/open by cumulative factor
        ...
    return df
```

`FactorEngine.compute_factor()` calls `DataSource.fetch()` which returns raw data. The factor's `compute()` method can call `load_adjusted_daily()` internally, or a future `AdjustedDataSource` wrapper can inject adjusted prices transparently. **P1 keeps it simple: factors that need adjusted prices call `load_adjusted_daily()` directly.**

### 3.4 Watchlist Generator Consumption

The existing `watchlist_generator.py` accepts `events`, `signals`, `positions`. For P1, northbound flow and index changes generate **Signal objects** that feed into the existing pipeline:

```python
# synapse/core/market/signal_producers.py (new)

def northbound_to_signals(
    records: list[NorthboundFlowRecord],
    threshold: float = 1e9,  # 10亿 CNY
) -> list[Signal]:
    """Convert large northbound flow into Signal objects for watchlist."""

def index_change_to_signals(
    old: list[IndexConstituent],
    new: list[IndexConstituent],
) -> list[Signal]:
    """Detect additions/removals between index snapshots, emit Signals."""
```

These producers return `list[Signal]` which plugs directly into `generate_daily(events, signals, positions)`. No changes to `watchlist_generator.py` needed.

---

## 4. Backward Compatibility

### 4.1 calendar.py

**Zero changes.** All existing functions (`is_trading_day`, `next_trading_day`, `trading_days_between`) remain as-is. New `TradingSession` dataclass is additive.

The `__init__.py` exports remain unchanged:
```python
# synapse/core/market/__init__.py — no modification needed
from synapse.core.market.calendar import is_trading_day, next_trading_day, trading_days_between
```

### 4.2 semantics.py

**Zero changes.** `price_limit()`, `validate_t1_settlement()`, `is_suspended()` remain as-is. `SymbolType` enum unchanged.

### 4.3 data_loader.py

**Additive only.** New `load_adjusted_daily()` function added alongside existing `load_daily()`. The `load_daily_from_api()` placeholder is **not replaced** in P1 — it remains as the future extension point. When a real API adapter is ready, `load_daily_from_api()` delegates to it, or callers switch to `load_adjusted_daily()` which chains through the adapter.

```python
# Existing exports preserved
from synapse.core.market.data_loader import load_daily, load_daily_from_api
# New export added
from synapse.core.market.data_loader import load_adjusted_daily
```

### 4.4 Migration Path

| Component | P1 Action | Future |
|-----------|-----------|--------|
| `calendar.py` | Keep hardcoded holidays | Add yearly update script |
| `data_loader.py` | Add `load_adjusted_daily()` | Replace `load_daily_from_api()` with adapter-backed implementation |
| `semantics.py` | No change | Add suspension data from DataSource |
| `watchlist_generator.py` | No change | Accept `northbound_signals` parameter directly |

---

## 5. File Layout Summary

```
synapse/core/market/
    __init__.py          # add exports for new schemas
    calendar.py          # unchanged
    semantics.py         # unchanged
    data_loader.py       # add load_adjusted_daily()
    schemas.py           # NEW: TradingSession, AdjustmentRecord, NorthboundFlowRecord, IndexConstituent
    transformers.py      # NEW: MarketData -> typed dataclass converters
    signal_producers.py  # NEW: typed dataclasses -> Signal objects

data/
    market/              # existing: {ticker}.csv / {ticker}.parquet
    adjustments/         # NEW: {ticker}.parquet (adjustment factors)
    northbound/          # NEW: YYYY-MM.parquet (monthly append)
    index/               # NEW: {index_id}_{date}.parquet (snapshots)
    calendar_overrides.yaml  # NEW (optional): custom session overrides
```

---

## 6. Key Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Adjustment factor data unavailable for some tickers | `load_adjusted_daily()` falls back to raw prices (factor=1.0) |
| Northbound flow data has gaps | `NorthboundFlowRecord` includes `source` field for provenance; signal producers skip records with missing data |
| Index constituent snapshots are stale | `IndexConstituent.effective_date` enables staleness check; warn if snapshot > 30 days old |
| Parquet files accumulate without cleanup | Monthly northbound files are small (<1KB); index snapshots are ~4/year. No cleanup needed for P1 scale |

---

*Analysis produced for WFS-synapse-p1-market-semantics. All recommendations are additive — no existing API contracts are broken.*
