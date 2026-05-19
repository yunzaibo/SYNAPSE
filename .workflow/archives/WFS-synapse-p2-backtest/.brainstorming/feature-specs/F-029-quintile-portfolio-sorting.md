# F-029: Quintile Portfolio Sorting

**Priority**: High
**Related Roles**: subject-matter-expert, system-architect

## Overview

5-quintile portfolio sorting with equal-weight allocation, dividing universe into 5 groups based on factor values.

## Requirements

### Functional Requirements

1. The system MUST sort stock universe into 5 equal groups (quintiles) based on factor values
2. The system MUST use equal-weight allocation within each quintile (1/N per stock)
3. The system MUST support configurable rebalancing periods (daily, weekly, monthly)
4. The system MUST handle missing factor values by excluding stocks from sorting
5. The system MUST return frozen `QuintilePortfolio` dataclass with group assignments

### Data Model

```python
@dataclass(frozen=True, slots=True)
class QuintilePortfolio:
    """5-quintile portfolio assignment."""
    date: date                          # Portfolio date
    quintiles: dict[int, list[str]]     # {1: [tickers], 2: [tickers], ...}
    weights: dict[int, dict[str, float]]  # {1: {ticker: 0.02}, ...}
    factor_name: str                    # Factor used for sorting
    universe_size: int                  # Total stocks in universe
    valid_count: int                    # Stocks with valid factor values
```

### Integration Points

- **Input**: FactorEngine output DataFrame (MultiIndex: date, ticker)
- **Output**: QuintilePortfolio for each rebalancing date
- **Dependencies**: TradingCalendar for rebalancing date generation

### Acceptance Criteria

- [ ] Sorting produces 5 groups with approximately equal size (±1 stock)
- [ ] Equal-weight allocation sums to 1.0 within each quintile
- [ ] Missing factor values are handled gracefully
- [ ] Rebalancing dates align with TradingCalendar
- [ ] Frozen dataclass ensures immutability

## Implementation Notes

- Use `pd.qcut()` for efficient quintile assignment
- Vectorized operations for performance
- Handle edge cases: all NaN values, single stock, fewer than 5 stocks
