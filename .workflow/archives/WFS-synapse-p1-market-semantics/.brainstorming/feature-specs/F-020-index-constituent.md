# F-020: Index Constituent (指数成分)

## Overview

New module `synapse/core/market/constituent.py` for tracking index membership. Provides point-in-time snapshots, change detection, and membership checks. Parquet snapshot files. Supports CSI 300, CSI 500, CSI 1000 indices.

## Data Model

```python
class IndexCode(str, Enum):
    CSI300 = "000300.SH"
    CSI500 = "000905.SH"
    CSI1000 = "000852.SH"
    SSE50 = "000016.SH"
    CUSTOM = "custom"

@dataclass(frozen=True, slots=True)
class ConstituentSnapshot:
    index_code: str
    date: date
    members: frozenset[str]              # ticker set
    weights: dict[str, Decimal] | None   # None if weight data unavailable

@dataclass(frozen=True, slots=True)
class ConstituentChange:
    date: date
    ticker: str
    action: Literal["add", "remove"]
    index_code: str
    reason: str  # "rebalance", "ipo", "delist", "suspend"
```

## Interface Design

| Function | Signature | Purpose |
|----------|-----------|---------|
| `load_constituents` | `(index_code, d, data_dir) -> ConstituentSnapshot` | Load for specific date (latest <= d) |
| `load_constituent_changes` | `(index_code, start, end, data_dir) -> list[ConstituentChange]` | All changes in range |
| `is_member` | `(index_code, ticker, d) -> bool` | Quick membership check |
| `constituent_tickers` | `(index_code, d) -> frozenset[str]` | Set of member tickers |

## Acceptance Criteria

- [ ] `IndexCode` enum covers CSI 300, CSI 500, CSI 1000, SSE 50
- [ ] `load_constituents` resolves to latest snapshot <= target date
- [ ] `load_constituent_changes` returns changes sorted by date
- [ ] `is_member` works correctly for all supported indices
- [ ] Missing index directory → `FileNotFoundError` with path suggestion
- [ ] Empty members file → snapshot with empty `frozenset`
- [ ] Future date requested → use latest available, log info
- [ ] File layout: `data/market/index/{code}/members.csv` and `changes.csv`

## Dependencies

- None (P1 foundation module)

## Priority

P1 (Foundation)

## Cross-References

- **System Architect**: IndexCode enum, immutable dataclasses, state management
- **Data Architect**: Parquet snapshot files `data/index/{index_id}_{date}.parquet`, query pattern
- **Subject Matter Expert**: Semi-annual/quarterly rebalance, ST/delisting removal, free-float weighting, announcement vs effective date gap
