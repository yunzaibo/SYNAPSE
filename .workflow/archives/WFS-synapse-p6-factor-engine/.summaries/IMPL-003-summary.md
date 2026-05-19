# Task: IMPL-003 IC/RankIC Auditor

## Implementation Summary

### Files Modified
- `synapse/factor/audit.py` — Added F-012 IC/RankIC auditor functions and FactorAuditReport dataclass while keeping legacy audit_factor backward-compatible
- `synapse/factor/__init__.py` — Added exports for new audit functions and FactorAuditReport
- `tests/unit/test_factor_audit.py` — Added 20 new tests for all new functions (24 total)

### Content Added

**`synapse/factor/audit.py`**:
- **FactorAuditReport** (dataclass, line 14) — Comprehensive audit report: factor_name, ic_mean, ic_std, icir, rank_ic_mean, turnover, decay_half_life, coverage, rating
- **compute_ic()** (line 29) — Pearson IC: aligns Series, drops NaN, returns np.corrcoef value
- **compute_rank_ic()** (line 37) — Spearman RankIC: aligns Series, drops NaN, returns scipy.stats.spearmanr value
- **compute_rolling_ic()** (line 46) — Rolling Pearson IC over DataFrame with "factor" and "forward_return" columns; numpy-based window loop for correctness
- **compute_icir()** (line 79) — ICIR = ic_mean / ic_std with zero/nan guard
- **rate_factor()** (line 86) — ICIR-based rating: A (>=0.5), B (>=0.3), C (>=0.1), D (<0.1); uses abs(icir)

**`synapse/factor/__init__.py`**:
- Exports: compute_ic, compute_rank_ic, compute_rolling_ic, compute_icir, rate_factor, FactorAuditReport

### Backward Compatibility
- **FactorAuditResult** and **audit_factor()** are untouched and remain functional
- All 4 original tests pass unchanged

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.factor.audit import (
    compute_ic,           # (factor_values, forward_returns) -> float
    compute_rank_ic,      # (factor_values, forward_returns) -> float
    compute_rolling_ic,   # (DataFrame, window=60) -> pd.Series
    compute_icir,         # (ic_mean, ic_std) -> float
    rate_factor,          # (FactorAuditReport) -> "A"|"B"|"C"|"D"
    FactorAuditReport,    # dataclass with all F-012 fields
)
```

### Integration Points
- **IMPL-002 (compute.py)**: Can call compute_ic/compute_rank_ic to evaluate factor quality during computation
- **FactorAuditReport**: Use rate_factor() to assign A/B/C/D rating based on ICIR

## Status: Complete
