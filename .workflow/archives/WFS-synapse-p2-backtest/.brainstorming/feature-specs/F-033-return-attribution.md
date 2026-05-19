# F-033: Return Attribution

**Priority**: Medium
**Related Roles**: subject-matter-expert, system-architect

## Overview

Barra-style factor model return attribution, decomposing portfolio returns into factor exposure and residual components.

## Requirements

### Functional Requirements

1. The system MUST decompose returns into factor exposure and residual components
2. The system MUST support multi-factor attribution (not just single factor)
3. The system MUST compute factor exposure for each stock
4. The system MUST return frozen `AttributionResult` dataclass
5. The system SHOULD support factor correlation analysis

### Data Model

```python
@dataclass(frozen=True, slots=True)
class AttributionResult:
    """Barra-style return attribution."""
    factor_returns: dict[str, float]   # {factor: return_contribution}
    residual_return: float             # Unexplained return
    factor_exposures: dict[str, float] # {factor: exposure}
    r_squared: float                   # Model fit
    factor_contributions: dict[str, float]  # {factor: contribution_pct}
```

### Attribution Formula

```
R_portfolio = Σ(β_i * F_i) + ε

Where:
- R_portfolio: Portfolio return
- β_i: Factor exposure to factor i
- F_i: Factor return
- ε: Residual return
```

### Integration Points

- **Input**: Factor values from FactorEngine, portfolio returns from simulation
- **Output**: AttributionResult for each period
- **Dependencies**: FactorEngine for factor returns

### Acceptance Criteria

- [ ] Factor exposure computed correctly
- [ ] Residual return calculated
- [ ] R-squared indicates model fit
- [ ] Multi-factor support works
- [ ] Frozen dataclass ensures immutability

## Implementation Notes

- Use OLS regression for factor model estimation
- Vectorized computation across all periods
- Handle multicollinearity with VIF analysis
