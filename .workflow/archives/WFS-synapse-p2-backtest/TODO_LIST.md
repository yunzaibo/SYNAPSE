# Tasks: P2 Long-Short Quintile Backtest Engine

## Task Progress

- [x] **IMPL-001**: Quintile Portfolio Sorter and Data Models -> [imply](./.task/IMPL-001.json) | [summary](./.summaries/IMPL-001-summary.md)
- [x] **IMPL-002**: Performance Metrics Calculator (8 Core Metrics Single Pass) -> [imply](./.task/IMPL-002.json)
- [x] **IMPL-003**: Factor IC Analysis (Rolling RankIC/ICIR) -> [imply](./.task/IMPL-003.json)
- [x] **IMPL-004**: Long-Short Spread Calculation -> [imply](./.task/IMPL-004.json)
- [x] **IMPL-005**: Return Attribution Engine (Barra-style Decomposition) -> [imply](./.task/IMPL-005.json)
- [x] **IMPL-006**: Backtest Engine Core (Event-driven Orchestration with DI) -> [imply](./.task/IMPL-006.json)
- [x] **IMPL-007**: Backtest Result Persistence (Parquet Storage) -> [imply](./.task/IMPL-007.json)
- [x] **IMPL-008**: End-to-End Integration Tests (P1/P6 Integration) -> [imply](./.task/IMPL-008.json)

## Feature Coverage

| Feature ID | Feature Name | Task(s) | Status |
|------------|-------------|---------|--------|
| F-029 | Quintile Portfolio Sorting | IMPL-001 | completed |
| F-030 | Backtest Engine Core | IMPL-006 | completed |
| F-031 | Performance Metrics | IMPL-002 | completed |
| F-032 | Factor IC Analysis | IMPL-003 | completed |
| F-033 | Return Attribution | IMPL-005 | completed |
| F-034 | Backtest Result Persistence | IMPL-007 | completed |
| F-035 | Long-Short Spread | IMPL-004 | completed |
| F-036 | Backtest Integration Tests | IMPL-008 | completed |

## Dependency Graph

```
IMPL-001 (Data Models + QuintileSorter)
  |
  +---> IMPL-002 (MetricsCalculator)
  +---> IMPL-003 (ICAnalyzer)
  +---> IMPL-004 (LongShortSpread)
  +---> IMPL-005 (AttributionEngine)
  |
  +---> IMPL-007 (Persistence) [depends on IMPL-001, IMPL-002]
  |
  +---> IMPL-006 (BacktestEngine Core) [depends on ALL above]
         |
         +---> IMPL-008 (Integration Tests)
```

## Execution Order

| Phase | Task(s) | Parallel? | Description |
|-------|---------|-----------|-------------|
| 1 | IMPL-001 | No | Data models and quintile sorter (foundation) |
| 2 | IMPL-002, IMPL-003, IMPL-004, IMPL-005, IMPL-007 | Yes (partial) | Independent computation modules |
| 3 | IMPL-006 | No | Engine orchestration (depends on all) |
| 4 | IMPL-008 | No | Integration tests (validates everything) |

## Status Legend

- `- [ ]` = Pending task
- `- [x]` = Completed task
