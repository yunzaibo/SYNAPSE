# F-018: Ex-Right Adjustment (复权)

## Overview

New module `synapse/core/market/adjustment.py` providing forward/backward price adjustment for dividends, splits, bonus shares, and rights issues. Integrates with `data_loader.py` via optional `adj_type` parameter. Parquet-based storage in `data/adjustments/`.

## Data Model

```python
class AdjustmentType(str, Enum):
    FORWARD = "forward"    # 前复权: adjust historical to current base
    BACKWARD = "backward"  # 后复权: adjust current to historical base
    NONE = "none"          # raw prices

@dataclass(frozen=True, slots=True)
class AdjustmentEvent:
    date: date
    factor: Decimal
    event_type: str          # "dividend", "split", "bonus"
    cash_dividend: Decimal   # yuan per share before tax
    stock_dividend: Decimal  # shares per 10 shares

@dataclass(frozen=True, slots=True)
class AdjustmentFactors:
    symbol: str
    events: tuple[AdjustmentEvent, ...]  # sorted by date ascending
    _cumulative: tuple[Decimal, ...]     # running product
```

## Interface Design

| Function | Signature | Purpose |
|----------|-----------|---------|
| `get_adjustment_factors` | `(symbol, start, end, data_dir) -> AdjustmentFactors` | Load from `data/adjustments/{symbol}.parquet` |
| `adjust_prices` | `(df, factors, adj_type) -> pd.DataFrame` | Add adj_open/adj_high/adj_low/adj_close columns |
| `adjust_single_price` | `(price, target_date, factors, adj_type) -> float` | Single price point adjustment |

## Acceptance Criteria

- [ ] `adjust_prices` adds `adj_open`, `adj_high`, `adj_low`, `adj_close` columns
- [ ] Original OHLCV columns preserved (non-destructive)
- [ ] Forward-adjusted default for display; backward for cumulative returns
- [ ] Missing adjustment file → log warning, return empty factors (no adjustment)
- [ ] Invalid factor (< 0 or > 10) → log warning, skip that event
- [ ] `data_loader.py` gains `adj_type: AdjustmentType = AdjustmentType.NONE` parameter
- [ ] Default `adj_type=NONE` preserves backward compatibility
- [ ] All Decimal calculations use `ROUND_HALF_UP` (四舍五入)

## Dependencies

- None (P1 foundation module, extends existing `data_loader.py`)

## Priority

P1 (Foundation)

## Cross-References

- **System Architect**: `AdjustmentType` enum, immutable dataclasses, error handling
- **Data Architect**: Parquet storage `data/adjustments/{ticker}.parquet`, `load_adjusted_daily()` wrapper
- **Subject Matter Expert**: Forward vs backward adjustment rules, high-bonus edge cases, factor validation
