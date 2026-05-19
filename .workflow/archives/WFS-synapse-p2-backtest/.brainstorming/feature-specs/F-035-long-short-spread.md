# F-035: Long-Short Spread

**Priority**: High
**Related Roles**: subject-matter-expert, system-architect

## Overview

Long-short portfolio spread calculation, computing the difference between top and bottom quintile returns.

## Requirements

### Functional Requirements

1. The system MUST compute long-short spread as Q1 return minus Q5 return
2. The system MUST compute cumulative long-short return
3. The system MUST support benchmark comparison (default: CSI 300)
4. The system MUST return frozen `LongShortResult` dataclass
5. The system SHOULD support custom benchmark selection

### Data Model

```python
@dataclass(frozen=True, slots=True)
class LongShortResult:
    """Long-short portfolio results."""
    spread_returns: pd.Series          # Daily spread returns
    cumulative_spread: pd.Series       # Cumulative spread
    benchmark_returns: Optional[pd.Series]  # Benchmark returns
    excess_returns: Optional[pd.Series]     # Spread - benchmark
    annual_spread_return: float         # Annualized spread return
    annual_benchmark_return: Optional[float]
    annual_excess_return: Optional[float]
```

### Calculation

```
Spread_Return_t = Q1_Return_t - Q5_Return_t
Cumulative_Spread = (1 + Spread_Return_1) * ... * (1 + Spread_Return_t) - 1
Excess_Return = Spread_Return - Benchmark_Return
```

### Integration Points

- **Input**: Quintile returns from portfolio simulation
- **Output**: LongShortResult for analysis
- **Dependencies**: Optional benchmark data

### Acceptance Criteria

- [ ] Spread computed as Q1 - Q5
- [ ] Cumulative spread calculated correctly
- [ ] Benchmark comparison works
- [ ] Annualized returns computed
- [ ] Frozen dataclass ensures immutability

## Implementation Notes

- Vectorized pandas operations for efficiency
- Handle missing benchmark data gracefully
- Support custom benchmark via parameter
