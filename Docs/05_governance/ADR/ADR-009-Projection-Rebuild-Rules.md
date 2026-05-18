# ADR-009: Projection Rebuild Rules

## Status

Accepted (2026-05-18)

## Context

SYNAPSE 区分 Canonical Artifacts（Thesis/Decision/Review/Event）和 Projections（Position/Watchlist/Timeline）。Projections 从 Canonical 计算，需要明确 rebuild 语义。

## Decision

| Projection | Rebuild Trigger | Strategy |
|-----------|----------------|----------|
| Position | Decision/Review change | Event-triggered rebuild |
| Watchlist | 每日定时 | Daily regeneration |
| Timeline | 所有 canonical artifact 变化 | Append-only rendering |
| SQLite index | 文件变化 | FileWatcher + lazy rebuild |

## Rules

- Position: Decision.recorded → 创建/更新 Position; Decision.sold → 关闭 Position; Review.completed → 更新 research_state
- Watchlist: 每日早上重新生成（不增量更新）
- Projection 永远从 canonical artifacts 计算，不手工编辑
- Projection 可以被删除和重建（它是 cache，不是 truth）
- 如果 projection 与 canonical 不一致，以 canonical 为准

## Consequences

- 避免 projection drift
- 避免双写问题
- Projection 是 cache，可随时重建

## Related

- ADR-007: Security Identity
- ADR-008: Temporal Semantics
