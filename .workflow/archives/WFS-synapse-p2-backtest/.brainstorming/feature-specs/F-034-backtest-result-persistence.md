# F-034: Backtest Result Persistence

**Priority**: Medium
**Related Roles**: data-architect, system-architect

## Overview

Parquet storage for backtest results with efficient columnar queries and schema versioning.

## Requirements

### Functional Requirements

1. The system MUST persist backtest results in Parquet format
2. The system MUST support efficient columnar queries by date range, factor, or metric
3. The system MUST include schema versioning for backward compatibility
4. The system MUST support lazy upcast for schema evolution
5. The system SHOULD support compression for storage efficiency

### Storage Structure

```
backtest_results/
├── results/
│   └── {session_id}/
│       └── backtest_result.parquet
├── quintile_returns/
│   └── {session_id}/
│       └── quintile_returns.parquet
├── ic_analysis/
│   └── {session_id}/
│       └── ic_analysis.parquet
└── attribution/
    └── {session_id}/
        └── attribution.parquet
```

### Integration Points

- **Input**: BacktestResult, QuintilePortfolio, ICAnalysisResult, AttributionResult
- **Output**: Parquet files with query support
- **Dependencies**: Pandas/PyArrow for Parquet I/O

### Acceptance Criteria

- [ ] Results persisted in Parquet format
- [ ] Columnar queries work efficiently
- [ ] Schema versioning implemented
- [ ] Lazy upcast for backward compatibility
- [ ] Compression reduces storage size

## Implementation Notes

- Use `pd.DataFrame.to_parquet()` with compression
- Schema version in metadata for evolution tracking
- Query API: `load_results(start_date, end_date, factor_name)`
