# F-031: Performance Metrics

**Priority**: High
**Related Roles**: subject-matter-expert, system-architect

## Overview

8 core performance metrics computation in a single pass through return series, with extensible design for additional metrics.

## Requirements

### Functional Requirements

1. The system MUST compute all 8 core metrics in a single pass
2. The system MUST support configurable risk-free rate (default: 0.03 for China)
3. The system MUST handle edge cases (zero volatility, single period, negative returns)
4. The system MUST return frozen `PerformanceMetrics` dataclass
5. The system SHOULD support additional metrics via extension

### Core Metrics

| Metric | Formula | Description |
|--------|---------|-------------|
| Annualized Return | `(1 + total_return) ** (252 / n_days) - 1` | Annual return rate |
| Sharpe Ratio | `(mean_return - rf) / std_return * sqrt(252)` | Risk-adjusted return |
| Max Drawdown | `max(1 - value / peak_value)` | Maximum peak-to-trough decline |
| Win Rate | `n_positive_days / n_total_days` | Proportion of positive returns |
| Profit/Loss Ratio | `mean_positive_return / abs(mean_negative_return)` | Average win / average loss |
| Calmar Ratio | `annualized_return / abs(max_drawdown)` | Return per unit of drawdown |
| Information Ratio | `mean_excess_return / tracking_error` | Active return per unit of active risk |
| Turnover Rate | `sum(abs(new_weight - old_weight)) / 2` | Portfolio turnover |

### Data Model

```python
@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    """8 core backtest performance metrics."""
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_loss_ratio: float
    calmar_ratio: float
    information_ratio: float
    turnover_rate: float
    # Extended metrics
    cumulative_return: float
    annual_turnover: float
    volatility: float
    tracking_error: float
```

### Integration Points

- **Input**: Daily return series from portfolio simulation
- **Output**: PerformanceMetrics for each quintile and long-short spread
- **Dependencies**: None (standalone computation)

### Acceptance Criteria

- [ ] All 8 core metrics computed correctly
- [ ] Edge cases handled (zero vol, single period)
- [ ] Frozen dataclass ensures immutability
- [ ] Single-pass computation for efficiency
- [ ] Legacy `compute_metrics()` wrapper preserved

## Implementation Notes

- Use vectorized NumPy operations
- Accumulate statistics during iteration (stateful calculator)
- Handle division by zero gracefully
