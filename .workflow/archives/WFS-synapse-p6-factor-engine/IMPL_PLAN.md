# IMPL_PLAN: P6 因子研究引擎

**Session**: WFS-synapse-p6-factor-engine
**Date**: 2026-05-19
**Complexity**: High
**Execution Model**: Phased (4 waves)

---

## 1. Overview

基于 P3 事件系统 + P4 社交情绪 + P5 数据源适配器，构建量化因子计算、IC/RankIC 审计、因子组合优化引擎。

### Features

| ID | Title | Priority | Wave |
|----|-------|----------|------|
| F-010 | FactorSpec & Registry | P0 | 1 |
| F-011 | FactorEngine Core | P0 | 2 |
| F-012 | IC/RankIC Auditor | P0 | 2 |
| F-013 | Traditional Factors | P1 | 3 |
| F-014 | Factor Portfolio Optimizer | P1 | 3 |
| F-015 | Factor Decay Analysis | P2 | 3 |
| F-016 | Event Factor Integration | P2 | 4 |

### Dependencies

```
F-010 (Registry) ──┬──→ F-011 (Engine) ──┬──→ F-013 (Factors)
                    │                     │
                    └──→ F-012 (Auditor) ──┼──→ F-014 (Portfolio)
                                          │
                                          └──→ F-015 (Decay)
                                          
F-010 ──→ F-016 (Event Factor) [needs P3+P4]
```

### Waves

| Wave | Tasks | Parallel |
|------|-------|----------|
| 1 | IMPL-001 | No |
| 2 | IMPL-002, IMPL-003 | Yes |
| 3 | IMPL-004, IMPL-005, IMPL-006 | Yes |
| 4 | IMPL-007 | No |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FactorEngine                             │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ FactorRegistry│  │ComputeOrchestr│  │ AuditPipeline         │ │
│  │  (register,   │  │  (batch,     │  │  (IC, RankIC,         │ │
│  │   lookup,     │  │   parallel)  │  │   ICIR, decay)        │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘ │
│         │                 │                      │              │
│  ┌──────▼─────────────────▼──────────────────────▼───────────┐  │
│  │                  Factor Computation Layer                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐  │  │
│  │  │ BaseFactor   │  │ FormulaFactor│  │ EventFactor      │  │  │
│  │  │ (ABC)        │  │ (pandas)     │  │ (event->signal)  │  │  │
│  │  └─────────────┘  └─────────────┘  └──────────────────┘  │  │
│  └────────────────────────┬──────────────────────────────────┘  │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ DataSource   │  │ Event System     │  │ Social Signals   │
│ (P5 adapters)│  │ (P3 detectors)   │  │ (P4 sentiment)   │
└─────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 3. Tasks

### Wave 1: Foundation

**IMPL-001: FactorSpec & Registry**
- Create `synapse/factor/spec.py` — FactorSpec dataclass
- Create `synapse/factor/registry.py` — FactorRegistry with register/unregister/get/list
- Create `synapse/factor/base.py` — BaseFactor ABC
- Create `tests/unit/test_factor_spec.py`
- Dependencies: None

### Wave 2: Core Engine (Parallel)

**IMPL-002: FactorEngine Core**
- Create `synapse/factor/engine.py` — FactorEngine with compute_factor/compute_batch/compute_all
- Implement DataSource → DataFrame conversion
- Implement point-in-time validation
- Create `tests/unit/test_factor_engine.py`
- Dependencies: IMPL-001

**IMPL-003: IC/RankIC Auditor**
- Create `synapse/factor/audit.py` — IC/RankIC computation + FactorAuditReport
- Implement ICIR-based rating (A/B/C/D)
- Implement rolling IC computation
- Create `tests/unit/test_factor_audit.py`
- Dependencies: IMPL-001

### Wave 3: Factor Library (Parallel)

**IMPL-004: Traditional Factors**
- Create `synapse/factor/factors/momentum.py` — 3 momentum factors
- Create `synapse/factor/factors/value.py` — 3 value factors
- Create `synapse/factor/factors/quality.py` — 3 quality factors
- Create `synapse/factor/factors/volatility.py` — 2 volatility factors
- Create `synapse/factor/factors/liquidity.py` — 2 liquidity factors
- Create `tests/unit/test_traditional_factors.py`
- Dependencies: IMPL-001, IMPL-002

**IMPL-005: Factor Portfolio Optimizer**
- Create `synapse/factor/portfolio.py` — equal_weight/ic_weighted/risk_parity
- Implement turnover control and constraint checking
- Create `tests/unit/test_factor_portfolio.py`
- Dependencies: IMPL-003

**IMPL-006: Factor Decay Analysis**
- Create `synapse/factor/decay.py` — IC decay curve + half-life computation
- Implement decay categorization
- Create `tests/unit/test_factor_decay.py`
- Dependencies: IMPL-003

### Wave 4: Event Integration

**IMPL-007: Event Factor Integration**
- Create `synapse/factor/factors/event_factor.py` — EventFactor base + implementations
- Implement enrich_with_events() bridge
- Integrate with P3 Event system + P4 Social Sentiment
- Create `tests/unit/test_event_factors.py`
- Dependencies: IMPL-001, P3 Event, P4 Social

---

## 4. Implementation Strategy

- **Execution Model**: Phased (4 waves)
- **Parallelization**: Wave 2 (IMPL-002 + IMPL-003), Wave 3 (IMPL-004 + IMPL-005 + IMPL-006)
- **Critical Path**: IMPL-001 → IMPL-002 → IMPL-004
- **Test Strategy**: Each task includes unit tests, IMPL-007 validates integration

---

## 5. Convergence Criteria

- [ ] All 7 tasks completed
- [ ] 100+ unit tests passing
- [ ] IC/RankIC computation verified against known values
- [ ] 13+ traditional factors registered and computable
- [ ] Event factor integration with P3/P4 systems
- [ ] `py -m pytest -p no:asyncio` 全量通过
