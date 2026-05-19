# F-032: Factor IC Analysis

**Priority**: High
**Related Roles**: subject-matter-expert, data-architect

## Overview

Rolling IC/RankIC/ICIR computation with configurable window, integrating with P6 FactorEngine's existing IC infrastructure.

## Requirements

### Functional Requirements

1. The system MUST compute cross-sectional IC (multiple stocks at single date)
2. The system MUST support rolling IC with configurable window (default: 20 days)
3. The system MUST compute ICIR (IC mean / IC standard deviation)
4. The system MUST integrate with P6's existing IC computation where possible
5. The system MUST return frozen `ICAnalysisResult` dataclass

### Data Model

```python
@dataclass(frozen=True, slots=True)
class ICAnalysisResult:
    """Factor IC analysis results."""
    factor_name: str
    ic_series: pd.Series              # Rolling IC values
    rank_ic_series: pd.Series         # Rolling RankIC values
    ic_mean: float                    # Mean IC
    ic_std: float                     # IC standard deviation
    icir: float                       # IC Information Ratio
    ic_positive_pct: float            # Percentage of positive IC
    half_life: Optional[float]        # IC decay half-life (days)
    window: int                       # Rolling window size
```

### Integration Points

- **P6 FactorEngine**: Reuses `compute_rolling_ic()` for time-series IC
- **New Function**: Cross-sectional IC (multiple stocks at single date)
- **P6 IC Audit**: Leverages existing ICIR and factor rating (A/B/C/D)

### Acceptance Criteria

- [ ] Cross-sectional IC computed correctly
- [ ] Rolling window configurable
- [ ] ICIR computed as mean/std
- [ ] Integration with P6 IC infrastructure
- [ ] Frozen dataclass ensures immutability

## Implementation Notes

- Cross-sectional IC: `corr(factor_values[t], forward_returns[t])` for each date
- Time-series IC: Already exists in P6 audit.py
- Use `pd.rolling_apply()` for efficient windowed computation
