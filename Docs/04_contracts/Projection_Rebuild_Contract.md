# Projection Rebuild Contract

> P2 扩展后的 Projection 重建契约。
> 冻结 projection 的 rebuild 语义，避免 P3/P4 出现 cache/source-of-truth 混乱。

## Status

Proposed (2026-05-18)

---

## 1. Projection Classification

| Type | Description | Rebuild Strategy | Example |
|------|-------------|------------------|---------|
| **Event-triggered** | Canonical object 变化时立即重建 | Incremental | Position |
| **Daily regeneration** | 每日定时全量重建 | Full rebuild | Watchlist |
| **Append-only** | 只追加，不修改 | Append | Timeline |
| **Lazy rebuild** | 查询时检测 stale，按需重建 | On-demand | Analytics |
| **Periodic** | 定期全量重建 | Full rebuild | SQLite index |

---

## 2. Partial Rebuild

**Question**: Projection 是否允许 partial rebuild?

**Answer**: YES，但有条件。

### Rules

| Condition | Partial Rebuild Allowed | Rationale |
|-----------|------------------------|-----------|
| Single canonical object change | YES | 只重建受影响的 projection |
| Schema version upgrade | NO | 必须全量 rebuild |
| Manual invalidation | YES | 可指定范围 |
| Stale threshold exceeded | YES | 按 ticker/date 范围 |

### Implementation

```python
def rebuild_projection(
    scope: str = "full",          # "full" | "partial" | "incremental"
    filter_ticker: str = None,    # 按 ticker 过滤
    filter_date_range: tuple = None,  # 按日期范围过滤
    force: bool = False           # 强制重建（忽略 stale 检查）
) -> RebuildResult:
    """
    重建 projection。
    
    scope="partial" 时，只重建 filter 指定的范围。
    scope="incremental" 时，只处理 canonical objects 的变化部分。
    """
    pass
```

### Constraints

- Partial rebuild 必须保证 **idempotent**（多次执行结果相同）
- Partial rebuild 必须保证 **consistency**（不会出现部分更新状态）
- Partial rebuild 后必须更新 `computed_at` 时间戳

---

## 3. Snapshot Cache

**Question**: Projection 是否允许 snapshot cache?

**Answer**: YES，但必须明确语义。

### Snapshot vs Cache

| Type | Description | Invalidation | Use Case |
|------|-------------|--------------|----------|
| **Snapshot** | 固定时间点的 projection 快照 | 不自动失效 | 历史对比、审计 |
| **Cache** | 临时存储，stale 时自动失效 | 自动 | 查询加速 |

### Rules

| Rule | Description |
|------|-------------|
| Snapshot 不自动失效 | Snapshot 是 historical record，不随 canonical 变化 |
| Cache 必须有 stale detection | 查询时检查 `computed_at` vs `canonical.updated_at` |
| Snapshot 必须标记 `snapshot_date` | 明确快照时间点 |
| Cache 可以被 delete + rebuild | Cache 是 disposable |

### Implementation

```python
@dataclass
class ProjectionSnapshot:
    """投影快照 - 固定时间点的 projection 状态"""
    snapshot_id: str
    snapshot_date: datetime
    projection_type: str
    data: dict
    canonical_versions: dict  # 快照时的 canonical object versions

@dataclass  
class ProjectionCache:
    """投影缓存 - 临时存储，stale 时自动失效"""
    cache_key: str
    computed_at: datetime
    stale_threshold: timedelta
    data: dict
    
    def is_stale(self, canonical_updated_at: datetime) -> bool:
        return canonical_updated_at > self.computed_at
```

---

## 4. Projection Versioning

**Question**: Projection 是否需要 versioning?

**Answer**: YES，用于 schema evolution。

### Versioning Strategy

| Component | Version Source | Version Format |
|-----------|---------------|----------------|
| Canonical objects | `schema_version` field | "1.0", "2.0" |
| Projections | `projection_version` field | "1.0", "2.0" |
| Analytics | `analytics_version` field | "1.0", "2.0" |

### Version Upgrade Rules

1. **Schema version upgrade** → 全量 rebuild 所有 projections
2. **Projection version upgrade** → 只 rebuild 该 projection type
3. **Backward compatible** → Lazy Upcast 支持旧版本数据
4. **Forward compatible** → 新版本 analytics 可读取旧版本数据

---

## 5. Rebuild Consistency

**Question**: Rebuild 过程中如何保证一致性？

**Answer**: 三阶段 commit 模式。

### Consistency Model

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Prepare     │────▶│  Compute    │────▶│  Commit     │
│  (lock)      │     │  (calculate)│     │  (swap)     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
  验证 canonical     计算新 projection    原子替换旧文件
  objects 版本       到临时目录          删除临时文件
```

### Rules

| Rule | Description |
|------|-------------|
| **Atomic swap** | 新旧文件替换是原子操作 |
| **No partial state** | 不会出现"一半旧一半新"的状态 |
| **Rollback on failure** | 计算失败时保留旧文件 |
| **Read during rebuild** | 读取旧文件（不阻塞） |

---

## 6. Rebuild Trigger Contract

| Canonical Event | Projection Affected | Rebuild Type | Priority |
|-----------------|---------------------|--------------|----------|
| Decision.created | Position | Incremental | High |
| Decision.updated | Position | Incremental | High |
| Review.completed | Error Pattern, Drift | Incremental | Medium |
| Thesis.revision | Evolution | Incremental | Medium |
| Event.created | Correlation | Incremental | Low |
| File change detected | SQLite index | Lazy | Low |
| Daily cron | Watchlist | Full rebuild | Medium |
| Manual command | Any | Full/Partial | User-defined |

---

## 7. Query-time vs Persisted

| Aspect | Query-time | Persisted |
|--------|-----------|-----------|
| **Latency** | Higher (compute on demand) | Lower (read from file) |
| **Storage** | None | File storage |
| **Freshness** | Always fresh | May be stale |
| **Complexity** | Simpler | More complex |
| **Use Case** | Small data, frequent changes | Large data, expensive computation |

**SYNAPSE Default**:

```yaml
projection:
  default_policy: persisted
  
  overrides:
    # Analytics 默认 persisted（计算昂贵）
    analytics:
      policy: persisted
      stale_threshold: 24h
      
    # SQLite index 使用 lazy rebuild
    sqlite_index:
      policy: lazy
      trigger: file_change
      
    # Watchlist 使用 daily regeneration
    watchlist:
      policy: daily_rebuild
      schedule: "0 8 * * *"  # 每天早上 8 点
```

---

## 8. Governance

| Rule | Description |
|------|-------------|
| **Canonical is truth** | 如果 projection 与 canonical 不一致，以 canonical 为准 |
| **Projection is cache** | Projection 可以被删除和重建 |
| **No dual-write** | 禁止同时写入 canonical 和 projection |
| **No write-back** | Projection 永远不写入 canonical objects |
| **Auditable** | Rebuild 过程记录到 activity log |

---

## Related

- ADR-009: Projection Rebuild Rules
- Analytics_Runtime_Philosophy.md
- Analytics_Object_Taxonomy.md
