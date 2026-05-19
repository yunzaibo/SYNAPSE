# Implementation Plan: F-007/F-008/F-009 Event-Driven Extensions

**Session**: WFS-synapse-p3-event-driven
**Created**: 2026-05-19
**Status**: Planning Complete

## Overview

Extend P3 event-driven infrastructure with three new features:
- **F-007**: Sentiment Viral Propagation (R0 coefficient, cascade detection)
- **F-008**: Capital Flow Divergence Tracking (institutional vs retail scoring)
- **F-009**: Cross-Event Correlation Engine (affinity matrix, combined impact)

All changes are **additive** -- no existing APIs are modified. Each feature creates its own module file.

## Architecture

### New Files (6 total)
| File | Feature | Lines (est.) | Purpose |
|------|---------|-------------|---------|
| `synapse/event/sentiment.py` | F-007 | ~120 | SentimentPropagation schema + R0 algorithm |
| `synapse/event/divergence.py` | F-008 | ~150 | CapitalFlowDivergence schema + scoring |
| `synapse/event/correlation.py` | F-009 | ~250 | EventCorrelation schema + affinity matrix + engine |
| `tests/unit/test_sentiment_propagation.py` | F-007 | ~150 | 8 tests |
| `tests/unit/test_capital_flow_divergence.py` | F-008 | ~120 | 6 tests |
| `tests/unit/test_cross_event_correlation.py` | F-009 | ~180 | 10 tests |

### Modified Files (0)
No existing files are modified. All integrations use existing extension points:
- `PropagationGraph.add_edge(edge_type=...)` -- existing parameter, no changes needed
- `EventContract.settle(result, metadata)` -- existing API, no changes needed
- `CATEGORY_HALF_LIVES["sentiment"]` -- already defined as 2.0

## Task Breakdown

### Wave 5: F-007 + F-008 (Parallel)

#### IMPL-001: F-007 Sentiment Propagation — schema + viral coefficient algorithm
- **Type**: feature
- **Depends**: none
- **CLI Strategy**: new
- **Deliverables**: `synapse/event/sentiment.py` with SentimentPropagation schema, compute_viral_coefficient(), detect_cascade(), build_sentiment_propagation()
- **Convergence**: 1 new file, 8-field schema, to_dict/from_dict round-trip, R0 calculation, cascade detection

#### IMPL-002: F-008 Capital Flow Divergence — schema + divergence scoring
- **Type**: feature
- **Depends**: none
- **CLI Strategy**: new
- **Deliverables**: `synapse/event/divergence.py` with CapitalFlowDivergence schema, compute_divergence_score(), classify_divergence(), build_divergence_from_flows(), settle_divergence_contract()
- **Convergence**: 1 new file, 10-field schema, to_dict/from_dict round-trip, divergence score [-1,1], classification thresholds

### Wave 5+6: Tests + Correlation

#### IMPL-003: F-007/F-008 Sentiment + Divergence tests
- **Type**: test-gen
- **Depends**: IMPL-001, IMPL-002
- **CLI Strategy**: merge_fork
- **Deliverables**: 14 tests (8 sentiment + 6 divergence) across 2 test files
- **Convergence**: 2 test files, 14 tests passing, class-based grouping, pytest.approx

#### IMPL-004: F-009 Cross-Event Correlation — schema + affinity matrix + engine
- **Type**: feature
- **Depends**: IMPL-001, IMPL-002
- **CLI Strategy**: merge_fork
- **Deliverables**: `synapse/event/correlation.py` with EventCorrelation schema, EVENT_TYPE_AFFINITY 8x8 matrix, compute_correlation_score(), classify_amplification(), compute_combined_impact(), find_correlations(), add_correlation_edges()
- **Convergence**: 1 new file, 8-field schema, 8x8 affinity matrix, correlation scoring, amplification/dampening, DAG-safe edge addition

#### IMPL-005: F-009 Cross-Event Correlation tests
- **Type**: test-gen
- **Depends**: IMPL-004
- **CLI Strategy**: resume
- **Deliverables**: 10 tests covering schema, affinity matrix, scoring, amplification, combined impact, DAG safety
- **Convergence**: 1 test file, 10 tests passing, class-based grouping, DAG safety verified

## Dependency Graph

```
IMPL-001 (F-007 Sentiment)     IMPL-002 (F-008 Divergence)
    |                                |
    +----------+  +------------------+
               |  |
               v  v
         IMPL-003 (Tests 14)
               |
    +----------+------------------+
    |                             |
    v                             v
IMPL-004 (F-009 Correlation)     |
    |                             |
    v                             |
IMPL-005 (Tests 10)              |
```

## Key Design Decisions

| Decision | Rationale | Revisit? |
|----------|-----------|----------|
| Separate module files per feature | Isolation, testability, no cross-feature coupling | No |
| Single-direction correlation edges | Preserves DAG property (bidirectional would create cycles) | No |
| 1e-9 epsilon in divergence formula | Prevents division by zero when both flows are zero | No |
| Max cluster size 10 for correlations | Performance bound for O(n^2) pairwise comparison | Maybe for large datasets |
| No new EventType entries needed | F-007/008/009 work with existing event types, compute derived metrics | No |

## Test Summary

| Wave | Tests | Files | Command |
|------|-------|-------|---------|
| Wave 5 (F-007) | 8 | test_sentiment_propagation.py | `py -m pytest tests/unit/test_sentiment_propagation.py -p no:asyncio -q` |
| Wave 5 (F-008) | 6 | test_capital_flow_divergence.py | `py -m pytest tests/unit/test_capital_flow_divergence.py -p no:asyncio -q` |
| Wave 6 (F-009) | 10 | test_cross_event_correlation.py | `py -m pytest tests/unit/test_cross_event_correlation.py -p no:asyncio -q` |
| **Total** | **24** | **3 files** | |

## Consolidated Constraints

1. Build on existing event module, no modifications to existing APIs
2. New schemas use to_dict()/from_dict() round-trip with Lazy Upcast defaults
3. Tests: `py -m pytest -p no:asyncio` (Windows)
4. F-009 depends on F-007 and F-008
5. All changes additive -- no breaking changes
6. Duck-typing with hasattr guards for cross-module imports
7. DAG property enforced on all graph edges (no cycles)
8. pytest.approx for all float comparisons in tests

## N+1 Context

### Decisions
| Decision | Rationale | Revisit? |
|----------|-----------|----------|
| 3 separate module files | Feature isolation, testability | No |
| 8x8 affinity matrix (hardcoded) | Static domain knowledge, no config needed | Yes if new event types added |
| Single-direction correlation edges | DAG preservation | No |

### Deferred
- (None -- all F-007/008/009 scope is captured)
