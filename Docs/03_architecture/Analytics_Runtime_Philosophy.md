# Analytics Runtime Philosophy

> P2 新增 Analytics 层的设计哲学。
> 定义 analytics 的生命周期、rebuild 语义、cache 策略、跨 analytics 依赖。

## Status

Proposed (2026-05-18)

---

## 1. Analytics 是什么

Analytics = **Projection over Canonical Research Objects**。

```
Canonical Objects (Thesis, Decision, Review, Event, Signal, Risk, Position)
        ↓
    Analytics Engine (计算/聚合)
        ↓
    Analytics Projections (ErrorPattern, BehavioralStats, Evolution, Bias, Drift, Correlation)
```

**核心属性**：
- Analytics 是 **derivative**，不是 **source of truth**
- Analytics 可以从 canonical objects **完全重建**
- Analytics 是 **deterministic**：相同输入 → 相同输出
- Analytics 是 **ephemeral**：可以删除、重建、过期

---

## 2. Lifecycle

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Canonical   │────▶│  Analytics  │────▶│  Projection │
│  Objects     │     │  Engine     │     │  Output     │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Invalidated │
                    │  (stale)     │
                    └─────────────┘
```

**生命周期阶段**：

| 阶段 | 说明 | 触发条件 |
|------|------|----------|
| **Fresh** | 刚计算完成，数据最新 | Rebuild 完成 |
| **Stale** | 依赖的 canonical objects 已变化 | Canonical object 更新 |
| **Invalidated** | 显式标记为过期 | 手动或自动触发 |
| **Deleted** | 已删除，可重建 | 手动删除 |

**Stale Detection**：
- 每个 analytics projection 记录 `computed_at` 时间戳
- 查询时比较：`canonical.updated_at > analytics.computed_at` → stale
- 或使用 `canonical.version` 计数器（更精确）

---

## 3. Rebuild Trigger

| Analytics Component | Rebuild Trigger | Strategy |
|---------------------|----------------|----------|
| Error Pattern | Review.completed | 增量追加 |
| Behavioral Stats | Decision.created/updated | 按 ticker 聚合 |
| Research Evolution | Thesis.revision | 版本链遍历 |
| Decision Bias | Decision.created | 批量统计 |
| Thesis Drift | Review.completed + time decay | 定期重算 |
| Correlation Intelligence | Event→Review linkage | 按事件链聚合 |

**Rebuild Rules**：
1. **Lazy Rebuild**：查询时检测 stale，按需重建（非实时）
2. **Batch Rebuild**：支持全量重建（`synapse analytics rebuild --all`）
3. **Incremental**：支持增量更新（仅处理变化部分）
4. **Idempotent**：多次 rebuild 结果相同

---

## 4. Materialization Policy

| Policy | 说明 | 适用场景 |
|--------|------|----------|
| **Query-time** | 每次查询实时计算 | 频繁变化、数据量小 |
| **Persisted** | 计算后存储到文件 | 计算昂贵、变化不频繁 |
| **Hybrid** | 热数据 persisted，冷数据 query-time | 混合场景 |

**SYNAPSE 默认策略**：

```yaml
analytics:
  materialization: persisted  # 默认持久化
  storage_format: yaml        # 与 canonical objects 一致
  cache_dir: analytics/       # 存储在 workspace/analytics/
  stale_threshold: 24h        # 超过 24 小时视为 stale
  rebuild_on_query: true      # 查询时如果 stale 则自动重建
```

---

## 5. Cross-analytics Dependency

```
Error Pattern ──────┐
                    ├──▶ Behavioral Stats
Decision Bias ──────┘
                         │
                         ▼
                    Thesis Drift
                         │
                         ▼
                    Correlation Intelligence
```

**依赖规则**：
- Analytics 之间可以有 **只读依赖**
- 下游 analytics 读取上游 analytics 的输出
- **禁止循环依赖**
- **禁止写回 canonical objects**

**Stale Propagation**：
- 上游 analytics stale → 下游 analytics 也标记为 stale
- Rebuild 时按依赖顺序执行（拓扑排序）

---

## 6. Storage Strategy

```
workspace/
├── thesis/              # Canonical
├── decisions/           # Canonical
├── reviews/             # Canonical
├── events/              # Canonical
├── analytics/           # Analytics Projections (P2 新增)
│   ├── error_patterns/
│   ├── behavioral_stats/
│   ├── evolution/
│   ├── bias/
│   ├── drift/
│   └── correlation/
└── .index/
    └── workspace.db     # SQLite index (acceleration)
```

**Storage Rules**：
- Analytics 存储在 `workspace/analytics/` 目录
- 每个 analytics component 一个子目录
- 文件格式与 canonical objects 一致（YAML）
- SQLite index 可从 analytics files 重建

---

## 7. Invalidation

| Trigger | Action | Scope |
|---------|--------|-------|
| Canonical object 更新 | 标记相关 analytics 为 stale | 单个 analytics |
| Schema 版本升级 | 全量 rebuild | 所有 analytics |
| 手动 invalidate | 标记为 stale | 指定 analytics |
| 时间衰减 | 定期 stale 检查 | 全局 |

**Invalidation Rules**：
1. Invalidation 是 **标记**，不删除文件
2. 下次查询时检测到 stale → 自动 rebuild
3. 支持手动 `synapse analytics invalidate --component drift`

---

## 8. Governance Constraints

| Rule | Description |
|------|-------------|
| **No Write-back** | Analytics 永远不写入 canonical objects |
| **No Autonomous Execution** | Analytics 只提供洞察，不执行交易 |
| **Source Attribution** | AI 生成的 analytics 标记 `source_type: ai_generated` |
| **Deterministic** | 相同输入必须产生相同输出 |
| **Auditable** | Analytics 计算过程可追溯 |

---

## Related

- ADR-009: Projection Rebuild Rules
- ADR-011: AI Mutation Boundaries
- Projection_Rebuild_Contract.md
- Analytics_Object_Taxonomy.md
