# Task: IMPL-005 Factor Portfolio Optimizer

## Implementation Summary

### Files Created/Modified

- `synapse/factor/portfolio.py`: New module with portfolio optimization logic
- `synapse/factor/__init__.py`: Added exports for new classes and functions
- `tests/unit/test_factor_portfolio.py`: 26 tests covering all functionality

### Content Added

- **FactorPortfolio** (`synapse/factor/portfolio.py:18`): Dataclass holding portfolio name, weights dict, method string, expected_ic, expected_risk, rebalance_freq, and created_at timestamp.
- **FactorPortfolioOptimizer** (`synapse/factor/portfolio.py:37`): Class with three optimization methods:
  - `equal_weight(factor_values) -> dict[str, float]`: Equal weight (1/N) for each factor column.
  - `ic_weighted(factor_values, ic_history) -> dict[str, float]`: Weights proportional to |IC mean|, normalized to sum to 1. Falls back to equal weight when all ICs are zero.
  - `risk_parity(factor_values) -> dict[str, float]`: Weights inversely proportional to factor std (1/std), normalized to sum to 1. Handles zero-std columns via epsilon substitution.
- **compute_turnover(old_weights, new_weights) -> float** (`synapse/factor/portfolio.py:141`): Turnover = sum(|new - old|) / 2. Returns value in [0, 1].
- **check_constraints(portfolio, max_single_weight=0.3) -> list[str]** (`synapse/factor/portfolio.py:161`): Validates single-factor weight limit and total weight sum. Returns list of violation descriptions.

## Outputs for Dependent Tasks

### Available Components

```python
from synapse.factor.portfolio import (
    FactorPortfolio,
    FactorPortfolioOptimizer,
    compute_turnover,
    check_constraints,
)
```

### Integration Points

- **FactorPortfolioOptimizer**: Use to generate optimal factor weights given factor values and IC history.
- **compute_turnover**: Use before rebalancing to check if turnover is within acceptable limits (< 30%).
- **check_constraints**: Use to validate portfolio before execution, checking single-factor weight exposure.

### Usage Examples

```python
from synapse.factor.portfolio import (
    FactorPortfolio,
    FactorPortfolioOptimizer,
    compute_turnover,
    check_constraints,
)
import pandas as pd

# Create factor values DataFrame (index=ticker, columns=factor_ids)
factor_values = pd.DataFrame({
    "momentum_6m": [0.05, 0.03, -0.02],
    "ep_ratio":    [0.08, 0.06, 0.04],
    "roe":         [0.12, 0.10, 0.08],
}, index=["600519", "000001", "000002"])

# IC-weighted optimization
optimizer = FactorPortfolioOptimizer()
weights = optimizer.ic_weighted(factor_values, ic_history)

# Create portfolio
portfolio = FactorPortfolio(
    name="multi_factor_v1",
    weights=weights,
    method="ic_weighted",
    expected_ic=0.06,
    expected_risk=0.15,
)

# Check constraints
violations = check_constraints(portfolio, max_single_weight=0.3)
if violations:
    print(f"Constraint violations: {violations}")

# Compute turnover vs previous portfolio
old_weights = {"momentum_6m": 0.5, "ep_ratio": 0.3, "roe": 0.2}
turnover = compute_turnover(old_weights, weights)
if turnover > 0.30:
    print(f"Turnover {turnover:.2%} exceeds 30% threshold")
```

## Status: Complete
