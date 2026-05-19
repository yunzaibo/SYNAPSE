# F-030: Backtest Engine Core

**Priority**: High
**Related Roles**: system-architect, data-architect

## Overview

Event-driven backtest engine with dependency injection, supporting configurable rebalancing and component composition.

## Requirements

### Functional Requirements

1. The system MUST implement event-driven architecture with Data, Signal, Execution layers
2. The system MUST support dependency injection for sorter, metrics, IC analyzer, attribution engine
3. The system MUST generate rebalancing dates using TradingCalendar
4. The system MUST preserve backward compatibility with existing `run_backtest()` interface
5. The system MUST support both batch and point-in-time (PIT) data access patterns

### Core Interfaces

```python
class BacktestEngine:
    """Main backtest engine with dependency injection."""
    
    def __init__(
        self,
        sorter: QuintileSorter,
        metrics: MetricsCalculator,
        ic_analyzer: Optional[ICAnalyzer] = None,
        attribution: Optional[AttributionEngine] = None,
        cost_model: Optional[CostModel] = None,
    ): ...
    
    def run(
        self,
        factor_values: pd.DataFrame,
        price_data: pd.DataFrame,
        start_date: date,
        end_date: date,
        rebalance_freq: str = "monthly",
    ) -> BacktestResult: ...
```

### Data Flow

```
FactorEngine Output (DataFrame MultiIndex)
    ↓
TradingCalendar → Rebalancing Dates
    ↓
QuintileSorter → Portfolio Assignments
    ↓
Portfolio Simulation → Return Series
    ↓
MetricsCalculator → Performance Metrics
    ↓
ICAnalyzer → Factor IC Analysis
    ↓
AttributionEngine → Return Attribution
    ↓
BacktestResult (frozen dataclass)
```

### Integration Points

- **P6 FactorEngine**: Consumes factor values via DataFrame contract
- **P1 Market Semantics**: Uses TradingCalendar, ExRightAdjustment
- **Backward Compatibility**: Legacy `run_backtest()` preserved as wrapper

### Acceptance Criteria

- [ ] Engine accepts FactorEngine output without transformation
- [ ] Rebalancing dates follow TradingCalendar
- [ ] Component injection works correctly
- [ ] Legacy interface maintains compatibility
- [ ] PIT data access prevents look-ahead bias

## Implementation Notes

- Use composition pattern for flexibility
- Vectorized operations for performance (5-10x speedup over loops)
- PartialBacktestResult for graceful degradation on errors
