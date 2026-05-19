# F-036: Backtest Integration Tests

**Priority**: Medium
**Related Roles**: system-architect, data-architect

## Overview

End-to-end integration tests covering P1/P6 integration, data flow validation, and performance benchmarks.

## Requirements

### Functional Requirements

1. The system MUST test end-to-end backtest flow with P1/P6 integration
2. The system MUST validate data flow contracts between components
3. The system MUST test edge cases (missing data, empty universe, single stock)
4. The system MUST include performance benchmarks for large datasets
5. The system MUST achieve ≥90% code coverage

### Test Categories

1. **Unit Tests**: Individual component tests (sorter, metrics, IC analyzer)
2. **Integration Tests**: Component composition tests
3. **End-to-End Tests**: Full backtest flow with P1/P6
4. **Performance Tests**: Benchmarks for large datasets
5. **Edge Case Tests**: Missing data, empty universe, etc.

### Test Data

- Use synthetic factor values for deterministic testing
- Use real P1 market data for integration testing
- Use P6 FactorEngine output for contract validation

### Integration Points

- **P1 Market Semantics**: TradingCalendar, ExRightAdjustment
- **P6 FactorEngine**: Factor values, IC analysis
- **Existing Tests**: Extend test_backtest.py

### Acceptance Criteria

- [ ] All unit tests pass
- [ ] Integration tests validate P1/P6 contracts
- [ ] End-to-end tests cover full flow
- [ ] Performance benchmarks meet targets
- [ ] Code coverage ≥90%

## Implementation Notes

- Use pytest fixtures for test data
- Parametrize tests for multiple scenarios
- Mock external dependencies where needed
- Use real data for integration tests
