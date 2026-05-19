# Synthesis Changelog: P3 Event-Driven Research Contracts

## Session: WFS-synapse-p3-event-driven
## Date: 2026-05-18

---

## Phase 3: Role Analysis Summary

### System Architect
- **Key Decision**: 4-state lifecycle (detected → propagating → settled → expired)
- **Key Decision**: DAG with Tarjan cycle detection + Kahn topological sort
- **Key Decision**: Pluggable detector pattern with DetectorRegistry
- **Key Decision**: 7-day stuck protection timeout

### Data Architect
- **Key Decision**: Hybrid storage (adjacency list in EventContract + edge list as YAML)
- **Key Decision**: EventContract as rebuildable projection (not source of truth)
- **Key Decision**: In-memory graph at query time (no external graph DB)
- **Key Decision**: Lazy Upcast v2.0 → v3.0 (no migration scripts)

### Subject Matter Expert
- **Key Decision**: 6 event categories, 22 sub-categories, 87 event types for A-share
- **Key Decision**: Severity 1-5 scale normalized to 0.0-1.0
- **Key Decision**: Category-specific decay half-lives (earnings 5-8d, policy 1-2d)
- **Key Decision**: P0-P3 priority tiers for propagation latency

### Test Strategist
- **Key Decision**: ~80 new tests (56 unit, 16 integration, 8 performance)
- **Key Decision**: 95% coverage for Schema Registry and Propagation Graph
- **Key Decision**: Property-based testing for propagation determinism
- **Key Decision**: Mock external sources at boundary (MockDataFeed, MockNewsSource)

---

## Phase 4: Synthesis Decisions

### Component Split (6 components)
| # | Component | Tests | Wave |
|---|-----------|-------|------|
| #8 | Event Schema Registry | 12 | 1 |
| #9 | Event Detection Engine | 15 | 2 |
| #10 | Propagation Graph | 18 | 2 |
| #11 | Impact Analyzer | 8 | 3 |
| #12 | Event-Review Integration | 10 | 3 |
| **Total** | | **71** | |

### Execution Strategy
- **Wave 1**: Schema foundation (F-001)
- **Wave 2**: Detection + Graph (F-002, F-003) — parallel
- **Wave 3**: Impact + Integration (F-004, F-005) — parallel
- **Wave 4**: CLI (F-006) — after all

### Cross-Role Conflicts Resolved
1. **Storage strategy**: Data architect's hybrid approach adopted (not pure edge list)
2. **Severity scale**: SME's 1-5 normalized to 0.0-1.0 (data architect's recommendation)
3. **Test count**: Adjusted from 80 to 71 (more realistic per-component estimates)

### Open Questions for P3 Execution
1. Should EventContract be a projection or canonical? → **Projection** (synthesis decision)
2. Maximum propagation depth? → **5 levels** (synthesis decision)
3. Should decay be configurable per-event or per-type? → **Per-type** (SME recommendation)

---

## Phase 4 (Extension): P3 Expansion Feature Specs

> Generated: 2026-05-19 | 3 new features added to P3 scope

### New Features Summary

| # | Feature | Priority | Tests | Depends On |
|---|---------|----------|-------|------------|
| F-007 | Sentiment Viral Propagation | High | 8 | F-001, F-003 |
| F-008 | Capital Flow Divergence Tracking | High | 6 | F-001, F-003 |
| F-009 | Cross-Event Correlation Engine | Medium | 10 | F-001, F-003, F-007, F-008 |

### System Architect Decisions (F-007/008/009)
- **F-007**: Viral coefficient (R₀) computed via BFS from root sentiment event; cascade confirmed if R₀ > 1.0 AND depth ≥ 2
- **F-008**: Divergence score = (institutional_flow - retail_flow) / (|institutional| + |retail| + ε); threshold 0.3
- **F-009**: Correlation uses EVENT_TYPE_AFFINITY matrix + temporal proximity; amplification vs dampening based on impact direction

### Data Architect Decisions (F-007/008/009)
- **F-007**: SentimentPropagation stored as separate schema; edge_type="sentiment" on PropagationGraph
- **F-008**: CapitalFlowDivergence stored as separate schema; integrates via EventContract.settle()
- **F-009**: EventCorrelation stored as separate schema; correlation edges added to PropagationGraph (bidirectional)

### Subject Matter Expert Decisions (F-007/008/009)
- **F-007**: Decay uses CATEGORY_HALF_LIVES["sentiment"] = 2.0d; propagation window default 24h
- **F-008**: 5-day rolling window for flow comparison; institutional flow weighted 1.5x
- **F-009**: Correlation window default 7 days; max cluster size 10 events

### Updated Execution Strategy
- **Wave 5**: Sentiment + Capital Flow (F-007, F-008) — parallel, after Wave 2
- **Wave 6**: Cross-Event Correlation (F-009) — after Wave 5

### Cross-Feature Dependencies
```
F-007 (Sentiment) ──┐
                    ├──→ F-009 (Correlation)
F-008 (Capital Flow)┘
```
