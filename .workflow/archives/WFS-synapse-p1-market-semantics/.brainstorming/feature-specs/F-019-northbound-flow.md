# F-019: Northbound Flow (北向资金)

## Overview

New module `synapse/core/market/northbound.py` for HK-SH/SZ capital flow data. Provides load/fetch/momentum functions. Parquet monthly files. Signal producers for watchlist integration. Data definitions only (no real-time streaming in P1).

## Data Model

```python
class NorthChannel(str, Enum):
    HGT = "沪股通"    # Shanghai-Hong Kong Stock Connect
    SGT = "深股通"    # Shenzhen-Hong Kong Stock Connect

@dataclass(frozen=True, slots=True)
class NorthboundFlow:
    date: date
    channel: NorthChannel
    buy_amount: Decimal        # net buy in 100M yuan
    sell_amount: Decimal
    net_amount: Decimal        # buy - sell
    total_buy: Decimal         # cumulative buy
    total_sell: Decimal        # cumulative sell
    quota_used_pct: Decimal    # daily quota usage percentage
```

## Interface Design

| Function | Signature | Purpose |
|----------|-----------|---------|
| `load_northbound_flow` | `(start, end, channel, data_dir) -> pd.DataFrame` | Load from `data/market/northbound/` CSV |
| `fetch_northbound_flow` | `(adapter, start, end, channel) -> pd.DataFrame` | Fetch via DataSource adapter |
| `northbound_momentum` | `(df, window=5) -> pd.Series` | Rolling net flow momentum |
| `northbound_to_signals` | `(records, threshold=1e9) -> list[Signal]` | Large flow → Signal for watchlist |
| `index_change_to_signals` | `(old, new) -> list[Signal]` | Index changes → Signal for watchlist |

## Acceptance Criteria

- [ ] `NorthChannel` enum: HGT (沪股通) and SGT (深股通)
- [ ] `load_northbound_flow` returns DataFrame with columns matching `NorthboundFlow` fields
- [ ] `fetch_northbound_flow` works with any `DataSource` supporting `data_type="northbound_flow"`
- [ ] `northbound_momentum` computes rolling sum over configurable window
- [ ] Signal producers return `list[Signal]` compatible with `watchlist_generator.py`
- [ ] Missing local file → `FileNotFoundError` with clear path guidance
- [ ] API failure → log warning, return empty DataFrame (never None)
- [ ] All data includes `source` field for provenance tracking

## Dependencies

- `DataSource` ABC from `synapse/event/datasource.py` (existing)
- `EastMoneyAdapter` (existing, may need `data_type="northbound_flow"` extension)
- `Signal` dataclass from existing codebase

## Priority

P1 (Foundation)

## Cross-References

- **System Architect**: NorthChannel enum, immutable dataclass, DataSource integration
- **Data Architect**: Monthly Parquet files `data/northbound/YYYY-MM.parquet`, signal_producers.py
- **Subject Matter Expert**: 净流入 vs 成交额 distinction, 520B quota rules, 假北向 detection (P2)
