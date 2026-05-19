# Task: IMPL-001 FactorSpec & Registry

## Implementation Summary

### Files Modified
- `synapse/factor/spec.py`: Replaced old FactorSpec (domain/formula/frequency/direction/universe/created_by) with new F-010 design (category/lookback_days/data_source/publication_lag/compute_fn). Updated YAML serialization and next_version to handle new fields.
- `synapse/factor/__init__.py`: Added exports for FactorSpec, BaseFactor, FactorRegistry.

### Files Created
- `synapse/factor/base.py`: BaseFactor ABC with factor_id(), spec(), compute(), required_columns().
- `synapse/factor/registry.py`: FactorRegistry with register/unregister/get_factor/list_factors/list_by_category.

### Files Updated (Tests)
- `tests/unit/test_factor_spec.py`: Rewritten with 18 tests covering FactorSpec creation, defaults, validation, YAML roundtrip, BaseFactor ABC, and FactorRegistry operations.
- `tests/unit/test_factor_compute.py`: Updated to use new FactorSpec fields (category, lookback_days, data_source, publication_lag). Tests expected to fail until IMPL-002 updates compute.py.

### Content Added
- **FactorSpec** (`synapse/factor/spec.py`): Dataclass with factor_id, name, description, category, inputs, lookback_days, data_source, publication_lag, compute_fn (Optional[Callable]), version (semver "1.0.0"). Includes from_yaml/to_yaml (skips compute_fn), next_version (bumps patch).
- **BaseFactor** (`synapse/factor/base.py`): ABC requiring factor_id(), spec(), compute(). Provides default required_columns() returning spec().inputs.
- **FactorRegistry** (`synapse/factor/registry.py`): Dictionary-based registry mapping factor_id -> factor class. Validates non-empty factor_id and uniqueness on register.

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.factor.spec import FactorSpec
from synapse.factor.base import BaseFactor
from synapse.factor.registry import FactorRegistry
```

### Integration Points
- **FactorSpec**: Use `FactorSpec(compute_fn=my_fn)` to attach computation logic
- **BaseFactor**: Subclass and implement factor_id(), spec(), compute()
- **FactorRegistry**: Call `registry.register(MyFactor)` to register, `registry.list_by_category("momentum")` to filter

### Known Breakage
- `compute.py` still references `spec.formula` (removed in new FactorSpec). Will be fixed in IMPL-002.
- `test_factor_compute.py` tests updated to new fields but will fail until compute.py is updated.

## Status: Complete
