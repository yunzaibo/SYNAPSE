# Security Review: SYNAPSE P2 Long-Short Quintile Backtest Engine

**Session**: WFS-synapse-p2-backtest
**Date**: 2026-05-19
**Reviewer**: Security Review Agent
**Score**: 6.5 / 10

## Executive Summary

The `synapse/backtest/` module demonstrates solid security fundamentals: no use of `eval`/`exec`/`pickle`, immutable frozen dataclasses for results, and clean separation of concerns via DI. However, the **persistence layer has a path traversal vulnerability** where user-controlled `factor_id` and `run_id` values are interpolated directly into filesystem paths without sanitization. Additionally, the `from_dict` deserialization methods perform no type validation on data loaded from Parquet files, and `BacktestConfig` lacks bounds checking on several numeric fields.

---

## Vulnerabilities Found

### HIGH: Path Traversal in Persistence Layer

**File**: `synapse/backtest/persistence.py`

**Issue**: `factor_id` and `run_id` are used directly in path construction without sanitization.

- Line 97: `summary_path = base / "results" / factor_id / f"{run_id}.parquet"`
- Line 144: `qr_path = base / "quintile_returns" / factor_id / f"{run_id}.parquet"`
- Line 161: `ic_path = base / "ic_analysis" / factor_id / f"{run_id}.parquet"`

A malicious `factor_id` value like `../../etc/cron.d/backdoor` would write files outside the intended `base_dir`.

**Current Mitigation**: `run_id` is generated as `uuid.uuid4().hex[:12]`, and `factor_id` originates from caller. No external input currently flows through CLI.

**Risk Level**: HIGH (latent -- exploitable if API is consumed by web service)

**Recommendation**:
```python
import re

def _sanitize_path_component(value: str, label: str) -> str:
    if not re.fullmatch(r'[a-zA-Z0-9_\-]+', value):
        raise ValueError(
            f"{label} must contain only alphanumeric, hyphens, and underscores; "
            f"got: {value!r}"
        )
    return value
```

---

### MEDIUM: No Type Validation on Deserialization

**File**: `synapse/backtest/result.py`

**Issue**: All `from_dict()` classmethods accept raw dicts without type checking.

- Line 54: `QuintilePortfolio.from_dict()` trusts `v` is iterable with string elements
- Line 99: `PerformanceMetrics.from_dict()` passes any value matching slot name
- Lines 251-275: `BacktestRunResult.from_dict()` trusts input shape

If a Parquet file is tampered with, deserialized objects could contain corrupted data.

**Recommendation**: Add `isinstance` checks in `from_dict()` methods.

---

### MEDIUM: Incomplete Config Validation

**File**: `synapse/backtest/config.py`

**Issue**: `BacktestConfig.__post_init__()` validates only 3 of 10 parameters.

| Field | Validated? | Risk |
|---|---|---|
| `transaction_cost_bps` | Yes (None check) | Could be negative |
| `slippage_bps` | Yes (None check) | Could be negative |
| `n_quintiles` | Yes (>= 2) | OK |
| `rebalance_frequency` | Yes (enum) | OK |
| `position_limit` | **No** | Could be > 1.0 or negative |
| `output_dir` | **No** | Could be absolute/sensitive path |
| `ic_window` | **No** | Could be negative or zero |
| `ic_min_periods` | **No** | Could be negative |

**Recommendation**: Add bounds checks for numeric fields and date validation.

---

### LOW: Error Message Information Leakage

**File**: `synapse/backtest/engine.py`, line 153

Raw exception string stored in result and persisted to Parquet. Could expose internal paths or stack traces.

**Recommendation**: Sanitize error message, log full exception separately.

---

### LOW: Broad Exception Catching Hides Failures

**File**: `synapse/backtest/persistence.py`, lines 409 and 422

Catching bare `Exception` can mask security-relevant errors (permission denied, corrupted files).

**Recommendation**: Catch specific exceptions (`FileNotFoundError`, `pyarrow.ArrowInvalid`).

---

### LOW: `pyarrow` Missing from Declared Dependencies

**File**: `pyproject.toml` does not list `pyarrow` as dependency.

**Recommendation**: Add `"pyarrow>=12.0"` to `dependencies`.

---

## Security Best Practices (What's Done Well)

1. **No code injection vectors**: Zero use of `eval()`, `exec()`, `os.system()`, `subprocess`, `pickle`, `marshal`, `shelve`, or `yaml.load()`.

2. **Immutable result dataclasses**: All output types use `frozen=True, slots=True`.

3. **Division-by-zero protection**: `max(total_stocks, 1)` and `> 1e-10` guards throughout.

4. **Empty-data guards**: Every major function checks for empty input before processing.

5. **No external network calls**: Entirely local computation, no HTTP/API/socket operations.

6. **UUID-based run IDs**: `uuid.uuid4().hex[:12]` generates cryptographically random identifiers.

7. **Clean DI pattern**: Enables testing with mock objects, reduces external coupling.

8. **Structured JSON serialization**: Uses `json.dumps` with `ensure_ascii=False`, avoiding pickle risks.

---

## Recommendations Summary

| Priority | Action | Effort |
|---|---|---|
| **High** | Add path component sanitization for `factor_id` and `run_id` | Small |
| **Medium** | Add type validation in `from_dict()` methods | Medium |
| **Medium** | Extend `BacktestConfig.__post_init__()` with bounds checks | Small |
| **Low** | Sanitize error messages stored in BacktestRunResult | Small |
| **Low** | Narrow exception catching in `query_results()` | Small |
| **Low** | Add `pyarrow` to `pyproject.toml` dependencies | Trivial |
