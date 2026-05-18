# TASK-005 Summary: Projection Engine

## Status: COMPLETED

## Changes
- Created: synapse/core/projection/__init__.py
- Created: synapse/core/projection/position_rebuilder.py (148 lines)
- Created: synapse/core/projection/watchlist_generator.py (180 lines)
- Created: synapse/core/projection/timeline.py (183 lines)
- Created: synapse/core/projection/index_manager.py (180 lines)
- Created: tests/unit/test_projection.py (280 lines) — 23 tests

## Summary
实现了 Projection Engine 模块，包含 4 个核心组件，从 canonical artifacts 计算 projection 数据。遵循 ADR-009 的 rebuild rules。

## Key Decisions
1. **Position Rebuilder** — 按时间顺序 replay Decision，buy→创建/更新，sell→关闭
2. **Watchlist Generator** — 每次全量生成（非增量），从 events/signals/positions 构建
3. **Timeline** — append-only 渲染，所有 canonical artifacts 按时间排序
4. **Index Manager** — SQLite 索引，支持按 type/ticker/status/thesis_id 查询

## Convergence Criteria
| Criterion | Status |
|-----------|--------|
| position_rebuilder.py with rebuild_from_decisions() | ✅ |
| watchlist_generator.py with generate_daily() | ✅ |
| timeline.py with render_timeline() | ✅ |
| index_manager.py with SQLite operations | ✅ |
| Position rebuild on Decision changes | ✅ |
| Watchlist daily regeneration | ✅ |
| tests pass | ✅ (23/23) |
