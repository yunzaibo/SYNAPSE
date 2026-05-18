# Factor Contract

## Purpose

Define factor metadata and audit output schema.

## P0 Implemented: FactorSpec

```python
@dataclass
class FactorSpec:
    factor_id: str
    name: str
    description: str
    domain: str             # cross_sectional_equity
    inputs: list[str]
    formula: str
    frequency: str          # daily | intraday
    direction: str          # positive | negative | unknown
    universe: str
    created_by: str         # human | ai | mixed
    version: str            # e.g. "1.0"
```

Source: `synapse/factor/spec.py`

## P0 Implemented: FactorAuditResult

```python
@dataclass
class FactorAuditResult:
    factor_id: str
    version: str
    coverage: float         # % of non-NaN values
    missing_rate: float     # % of NaN values
    ic: float               # Pearson correlation with forward returns
    rank_ic: float          # Spearman rank correlation with forward returns
    leakage_risk: str       # low | medium | high | unknown
    notes: str
```

Source: `synapse/factor/audit.py`

## API

```python
from synapse.factor.spec import FactorSpec
from synapse.factor.compute import compute_factor
from synapse.factor.audit import audit_factor

spec = FactorSpec.from_yaml("factors/momentum-20d.yaml")
values = compute_factor(spec, data)
audit = audit_factor(values, forward_returns, factor_id=spec.factor_id)
```
