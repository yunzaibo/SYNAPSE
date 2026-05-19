# Task: IMPL-002 FactorEngine Core

## Implementation Summary

### Files Modified
- `synapse/factor/engine.py` — New file: FactorEngine class implementing F-011 design
- `synapse/factor/__init__.py` — Added FactorEngine and PartialResult exports

### Files Created
- `tests/unit/test_factor_engine.py` — 20 tests covering all FactorEngine functionality

### Content Added

**FactorEngine** (`synapse/factor/engine.py`):
- `FactorEngine.__init__(registry, data_source)` — Takes FactorRegistry and DataSource
- `FactorEngine._to_dataframe(market_data)` — Static method converting MarketData list to DataFrame, handles both `records` payload and flat payload formats
- `FactorEngine._filter_point_in_time(df, compute_date, publication_lag)` — Static method filtering rows by date cutoff to prevent look-ahead bias
- `FactorEngine.compute_factor(factor_id, tickers, date)` — Single factor computation, returns pd.Series
- `FactorEngine.compute_batch(factor_ids, tickers, date)` — Batch factor computation, returns pd.DataFrame
- `FactorEngine.compute_all(tickers, date)` — Compute all registered factors
- `FactorEngine._compute_with_error_handling(...)` — Internal helper wrapping compute_factor with PartialResult error containment

**PartialResult** (`synapse/factor/engine.py`):
- `PartialResult` dataclass with fields: factor_id, success, value (Optional[pd.Series]), error (Optional[str])
- Single factor failures do not block other factors in batch computation

**Exports** (`synapse/factor/__init__.py`):
- Added `FactorEngine` and `PartialResult` to module exports

## Test Coverage (20 tests)

| Test Class | Tests | Description |
|---|---|---|
| TestFactorEngineCreation | 1 | Engine creation with registry + data_source |
| TestToDataframe | 4 | MarketData-to-DataFrame conversion (empty, single, multi, flat) |
| TestComputeFactor | 4 | Single factor computation (returns Series, values present, unregistered raises, empty fetch) |
| TestComputeBatch | 2 | Batch computation (returns DataFrame, empty factor_ids) |
| TestComputeAll | 2 | All-factor computation (all registered, empty registry) |
| TestPartialResult | 2 | Error containment (failing factor doesn't block others, dataclass fields) |
| TestPointInTime | 5 | Point-in-time validation (excludes future data, zero lag, no date column, empty df, publication_lag integration) |

## Key Design Decisions

1. **_to_dataframe dual format**: Handles both `payload={"records": [...]}` (multi-row) and flat payload (single-row) formats for flexibility
2. **Point-in-time cutoff**: `cutoff = compute_date - publication_lag days`, data must be `<= cutoff`
3. **PartialResult pattern**: Errors caught per-factor in compute_batch, logged as warnings, excluded from output
4. **Empty data handling**: Returns empty pd.Series/pd.DataFrame rather than raising exceptions

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.factor.engine import FactorEngine, PartialResult

engine = FactorEngine(registry, data_source)
result = engine.compute_factor("factor_id", ["600519"], date(2024, 1, 10))
batch = engine.compute_batch(["f1", "f2"], ["600519"], date(2024, 1, 10))
all_factors = engine.compute_all(["600519"], date(2024, 1, 10))
```

### Integration Points
- **FactorEngine**: Requires `FactorRegistry` (from IMPL-001) and `DataSource` (from P5)
- **IMPL-004 (Traditional Factors)**: Will use FactorEngine for computing factor values
- **IMPL-003 (Audit)**: Can use FactorEngine output for IC/RankIC computation

## Status: Complete
