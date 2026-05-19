# TODO_LIST: P6 因子研究引擎

**Session**: WFS-synapse-p6-factor-engine
**Generated**: 2026-05-19

---

## Wave 1: Foundation

- [x] **IMPL-001**: FactorSpec & Registry — `synapse/factor/spec.py`, `registry.py`, `base.py`
  - Dependencies: None
  - Test: `tests/unit/test_factor_spec.py`
  - Summary: [IMPL-001-summary.md](./.summaries/IMPL-001-summary.md)

## Wave 2: Core Engine (Parallel)

- [x] **IMPL-002**: FactorEngine Core — `synapse/factor/engine.py`
  - Dependencies: IMPL-001
  - Test: `tests/unit/test_factor_engine.py`

- [x] **IMPL-003**: IC/RankIC Auditor — `synapse/factor/audit.py`
  - Dependencies: IMPL-001
  - Test: `tests/unit/test_factor_audit.py`
  - Summary: [IMPL-003-summary.md](./.summaries/IMPL-003-summary.md)

## Wave 3: Factor Library (Parallel)

- [x] **IMPL-004**: Traditional Factors — `synapse/factor/factors/momentum.py`, `value.py`, `quality.py`, `volatility.py`, `liquidity.py`
  - Dependencies: IMPL-001, IMPL-002
  - Test: `tests/unit/test_traditional_factors.py`
  - Summary: [IMPL-004-summary.md](./.summaries/IMPL-004-summary.md)

- [x] **IMPL-005**: Factor Portfolio Optimizer — `synapse/factor/portfolio.py`
  - Dependencies: IMPL-003
  - Test: `tests/unit/test_factor_portfolio.py`
  - Summary: [IMPL-005-summary.md](./.summaries/IMPL-005-summary.md)

- [ ] **IMPL-006**: Factor Decay Analysis — `synapse/factor/decay.py`
  - Dependencies: IMPL-003
  - Test: `tests/unit/test_factor_decay.py`

## Wave 4: Event Integration

- [x] **IMPL-007**: Event Factor Integration — `synapse/factor/factors/event_factor.py`
  - Dependencies: IMPL-001, P3 Event, P4 Social
  - Test: `tests/unit/test_event_factors.py`
