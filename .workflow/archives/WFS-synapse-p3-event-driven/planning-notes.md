# Planning Notes

**Session**: WFS-synapse-p3-event-driven
**Created**: 2026-05-19T16:30:00+08:00

## User Intent (Phase 1)

- **GOAL**: 实现 P3 扩展 feature specs (F-007 Sentiment Propagation, F-008 Capital Flow Divergence, F-009 Cross-Event Correlation)
- **SCOPE**: 3 个新 feature 的完整实现 — 数据模型、算法、集成点、测试
- **CONTEXT**: P3 核心增强已完成 (5 tasks, 561 tests)。现有 event 模块支持 8 种 EventType, 8 个检测器, PropagationGraph DAG, EventContract settlement lifecycle。F-007/008/009 构建在现有基础设施之上。

### Brainstorm Artifacts Available

| Artifact | Status |
|----------|--------|
| guidance-specification.md | OK - F-007/008/009 组件已添加 |
| feature-specs/F-007~009 | OK - 3 个 feature spec |
| feature-index.json | OK - 9 features, 95 tests, 6 waves |
| synthesis-changelog.md | OK - 跨角色决策已记录 |
| role analyses (4 roles) | OK - system-architect, data-architect, subject-matter-expert, test-strategist |

---

## Context Findings (Phase 2)

- **CRITICAL_FILES**: detectors.py, graph.py, event_contract.py, event.py, lifecycle.py, taxonomy.py
- **ARCHITECTURE**: BaseDetector ABC, DetectorRegistry, PropagationGraph DAG, EventContract settlement
- **CONFLICT_RISK**: low (all changes additive, no breaking changes)
- **CONSTRAINTS**: Lazy Upcast for new fields, duck-typing for circular import avoidance

### Key Integration Points
| Feature | Integration Point | File |
|---------|-------------------|------|
| F-007 | edge_type="sentiment" on PropagationGraph | graph.py |
| F-007 | R₀ via BFS from root sentiment event | new: sentiment.py |
| F-008 | divergence events use EventContract.settle() | event_contract.py |
| F-008 | divergence score computation | new: divergence.py |
| F-009 | correlation edges on PropagationGraph (bidirectional) | graph.py |
| F-009 | EVENT_TYPE_AFFINITY matrix | new: correlation.py |

## Conflict Decisions (Phase 3)
Skipped — conflict_risk is low, all changes additive.

## Consolidated Constraints (Phase 4 Input)
1. 构建在现有 event 模块之上，不修改已有 API
2. 新 schema 使用 Lazy Upcast 保持向后兼容
3. 测试用 py -m pytest -p no:asyncio (Windows)
4. F-009 依赖 F-007 和 F-008
5. [Context] All changes additive — no breaking changes to existing APIs
6. [Context] Duck-typing with hasattr guards for cross-module imports

---

## Task Generation (Phase 4)

**5 tasks generated** across 2 execution waves. 24 total tests.

| Task | Title | Type | Depends | Wave | Tests |
|------|-------|------|---------|------|-------|
| IMPL-001 | F-007 Sentiment Propagation | feature | -- | Wave 5 | -- |
| IMPL-002 | F-008 Capital Flow Divergence | feature | -- | Wave 5 | -- |
| IMPL-003 | F-007/F-008 Tests | test-gen | IMPL-001, IMPL-002 | Wave 5+ | 14 |
| IMPL-004 | F-009 Cross-Event Correlation | feature | IMPL-001, IMPL-002 | Wave 6 | -- |
| IMPL-005 | F-009 Tests | test-gen | IMPL-004 | Wave 6 | 10 |

**New files**: sentiment.py, divergence.py, correlation.py + 3 test files
**Modified files**: None (all additive, no existing APIs changed)

## N+1 Context
### Decisions
| Decision | Rationale | Revisit? |
|----------|-----------|----------|
| 3 separate module files per feature | Feature isolation, testability, no cross-feature coupling | No |
| Single-direction correlation edges | Preserves DAG property (bidirectional creates cycles) | No |
| 1e-9 epsilon in divergence formula | Prevents division by zero when both flows zero | No |
| Max cluster size 10 for correlations | Performance bound for O(n^2) pairwise comparison | Yes for large datasets |
| No new EventType entries needed | F-007/008/009 work with existing types, compute derived metrics | No |
| 8x8 hardcoded affinity matrix | Static domain knowledge, no config file needed | Yes if new event types added |

### Deferred
- [ ] Real-time sentiment streaming (P4 scope per F-007 non-goal)
- [ ] Social media NLP sentiment (F-007 non-goal, only market-data signals)
- [ ] Cross-asset correlation (F-009 non-goal, only within CN_A market)
