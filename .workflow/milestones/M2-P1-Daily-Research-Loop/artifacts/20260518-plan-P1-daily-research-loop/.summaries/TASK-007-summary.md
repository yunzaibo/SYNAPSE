# TASK-007 Summary: Research Workflow (Watchlist + Decision + Review)

## Status: COMPLETED

## Changes
- Created: synapse/core/workflow/__init__.py
- Created: synapse/core/workflow/daily_research.py (103 lines)
- Created: synapse/core/workflow/decision_flow.py (105 lines)
- Created: synapse/core/workflow/review_flow.py (76 lines)
- Created: tests/unit/test_workflow.py (260 lines) — 13 tests

## Summary
实现了 P1 Daily Research Loop 的三个 workflow：每日研究生成、决策记录、决策回顾。所有 workflow 遵循 ADR-009 和 ADR-010 规范。

## Key Decisions
1. **Activity logging 通过参数注入** — 不强制依赖，方便测试
2. **Workspace 目录可选** — None 时跳过文件操作
3. **Decision rebuild 包含新 decision** — 自动加入列表再 rebuild

## Convergence Criteria
| Criterion | Status |
|-----------|--------|
| daily_research.py with run_daily_research() | ✅ |
| run_daily_research() calls generate_daily() | ✅ |
| decision_flow.py with record_decision() | ✅ |
| record_decision() triggers position rebuild | ✅ |
| review_flow.py with submit_review() | ✅ |
| All workflows write to activity.jsonl | ✅ |
| tests pass | ✅ (13/13) |
