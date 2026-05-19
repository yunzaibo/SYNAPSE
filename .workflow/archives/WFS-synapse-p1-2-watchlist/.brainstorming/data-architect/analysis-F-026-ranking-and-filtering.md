# F-026: Ranking and Filtering — Data Architect Analysis

## Feature Summary

Sort WatchlistEntry list by `priority_score` descending, apply optional filters, and produce the final daily watchlist output.

## Data Model: RankedWatchlist

### Definition

```python
@dataclass(frozen=True)
class RankedWatchlist:
    """Immutable ranked watchlist output."""
    target_date: date
    entries: tuple[WatchlistEntry, ...]   # Sorted by priority_score descending
    total_count: int
    filtered_count: int                   # Entries removed by filters
    generation_timestamp: datetime
```

**Why tuple, not list**: Immutable — the ranked output MUST NOT be mutated after generation.

**Why frozen**: Same rationale as ScoreResult — computed output, not stored entity.

### Construction Function

```python
def rank_and_filter(
    entries: list[WatchlistEntry],
    config: ScoringConfig,
    target_date: date,
) -> RankedWatchlist:
```

## Ranking Algorithm

### Sort Key

```python
sorted_entries = sorted(entries, key=lambda e: (-e.priority_score, e.ticker), reverse=False)
```

**Tie-breaking**: When two entries have the same `priority_score`, sort by `ticker` alphabetically. This produces deterministic output regardless of input order.

**Constraints**:
- MUST be stable sort — entries with same score maintain relative order from input
- MUST produce deterministic output for same input (tickers are unique per day)

### Top-N Selection

If `config.max_entries` is set (default: None = no limit):
- Keep only the top N entries after sorting
- Entries beyond N are dropped silently

## Filtering Rules

### Filter Types

| Filter | Config Key | Default | Behavior |
|--------|-----------|---------|----------|
| Min score | `min_priority_score` | 0.0 | Remove entries below threshold |
| Max entries | `max_entries` | None | Limit output count |
| Trigger type | `exclude_triggers` | [] | Remove entries matching excluded trigger types |
| Market | `allowed_markets` | ["CN_A"] | Keep only entries from allowed markets |

### Filter Application Order

1. Min score filter (remove low-scoring entries)
2. Trigger type filter (remove excluded trigger types)
3. Market filter (remove non-allowed markets)
4. Max entries limit (truncate to top N)

**Constraints**:
- Filters MUST be applied in this order — min score first prevents unnecessary processing
- Filters MUST NOT mutate input entries — return new filtered list
- `filtered_count` MUST accurately reflect entries removed at ALL filter stages

## Storage Impact

- RankedWatchlist is ephemeral — constructed during generation, entries written to YAML
- The `entries` tuple is the same WatchlistEntry objects, just sorted
- `save_watchlist` already handles per-entry YAML writing — no changes needed
- A summary file (`watchlist_summary.yaml`) SHOULD be written alongside entries:

```yaml
target_date: "2026-05-19"
total_count: 12
filtered_count: 3
generation_timestamp: "2026-05-19T08:00:00+08:00"
entries:
  - id: "wl_abc123"
    ticker: "600519"
    priority_score: 0.85
    reason: "事件驱动: 业绩超预期"
  - id: "wl_def456"
    ticker: "000858"
    priority_score: 0.72
    reason: "持仓回顾: thesis weakening"
```

This summary file provides a quick overview without parsing individual YAML files.

## Risks

- **Low**: All entries with priority_score = 0.0 (unscored) will rank lowest. This is correct — unscored entries are "nice to have" not "must research".
- **Low**: max_entries = 0 would produce empty watchlist. SHOULD validate > 0 or treat as None.
