# Milestone: M1-P0-Minimum-Research-Loop — P0 Minimum Research Loop

**Completed**: 2026-05-17
**Artifacts**: 2 (plan: 1, execute: 1)

## Key Outcomes

- Complete factor research pipeline: data → factor → audit → experiment → backtest → report
- 124/124 tests passing across 7 modules + integration
- Governance-first design: explicit transaction costs, experiment preservation, AI boundary enforcement
- All ADR constraints respected (research-first, no real trading, build from scratch)

## Architecture

```
synapse/
  core/       — errors, config, workspace
  data/       — metadata, loader, validator
  factor/     — spec, compute, audit
  experiment/ — record, tracker (state machine)
  backtest/   — config, engine, metrics
  report/     — markdown generator
  agent/      — prompt templates (boundary-respecting)
```

## Learnings

1. setuptools.build_meta required for flat-layout (not _legacy:_Backend)
2. Backtest index alignment: use .iloc with numpy boolean arrays
3. Sharpe floating-point edge case: tolerance > 1e-10, not > 0
4. Windows: `py -m pytest -p no:asyncio`
5. Factor compute on interleaved data: groupby per ticker
6. Reuse existing error codes rather than proliferating new ones

## Audit Findings (Non-blocking)

- 3 LOW: Error classes inconsistent (ValueError vs SYNAPSE errors)
- 4 INFO: Unused error codes, missing Enum for BacktestResult.status, etc.
- 0 CRITICAL: No integration gaps, no circular dependencies

## Deliverables

| Module | Files | Tests |
|--------|-------|-------|
| Core | errors.py, config.py, workspace.py | - |
| Data | metadata.py, loader.py, validator.py | 13 |
| Factor | spec.py, compute.py, audit.py | 10 |
| Experiment | record.py, tracker.py | 21 |
| Backtest | config.py, engine.py, metrics.py | 14 |
| Report | generator.py | 25 |
| Agent | prompts.py | 33 |
| Integration | run_sample_research.py, test_full_pipeline.py | 8 |

## Next Milestone

P1: Enhanced Research Loop (walk-forward validation, purging/embarkment, factor library)
