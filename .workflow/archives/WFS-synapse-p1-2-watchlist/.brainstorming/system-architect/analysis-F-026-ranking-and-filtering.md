# F-026: Ranking and Filtering -- System Architect Analysis

## Overview

Implement the post-scoring ranking and filtering mechanism that produces the final watchlist from scored entries. This includes deduplication, minimum score filtering, top-N selection, and stable sorting.

## Current State Analysis

The existing `generate_daily()` returns ALL entries without ranking or filtering. The `save_watchlist()` function writes all entries to individual YAML files. There is no concept of "top N" or minimum score threshold.

## Architecture: Ranking Pipeline

### Pipeline Flow

```
ScoredEntry[] -> dedup -> filter(min_score) -> sort(desc) -> top(N) -> WatchlistEntry[]
```

### Implementation

```python
def rank_and_filter(
    scored_entries: list[ScoredEntry],
    config: ScoringConfig,
) -> list[WatchlistEntry]:
    """Rank and filter scored entries into final watchlist."""

    # 1. Deduplication: keep highest-scoring entry per ticker
    deduped = _deduplicate_by_ticker(scored_entries, config.dedup_strategy)

    # 2. Minimum score filter
    filtered = [se for se in deduped if se.total_score >= config.min_score]

    # 3. Stable sort by score (descending)
    ranked = sorted(filtered, key=lambda se: se.total_score, reverse=True)

    # 4. Top-N selection
    top_entries = ranked[:config.max_entries]

    # 5. Convert to WatchlistEntry with priority_score and reason
    return [_to_watchlist_entry(se) for se in top_entries]


def _deduplicate_by_ticker(
    entries: list[ScoredEntry],
    strategy: str,
) -> list[ScoredEntry]:
    """Deduplicate entries by ticker, keeping the highest-scoring one."""
    by_ticker: dict[str, list[ScoredEntry]] = {}
    for se in entries:
        ticker = se.entry.ticker
        by_ticker.setdefault(ticker, []).append(se)

    result = []
    for ticker, group in by_ticker.items():
        if strategy == "highest_score":
            result.append(max(group, key=lambda se: se.total_score))
        elif strategy == "keep_all":
            result.extend(group)
        else:
            result.append(max(group, key=lambda se: se.total_score))

    return result
```

## Design Decisions

### D-026-1: Deduplication Strategy

A single ticker may appear in multiple entries (e.g., event-driven AND signal-driven AND portfolio review). The deduplication strategy MUST default to `highest_score`:

- `highest_score`: Keep only the entry with the highest `priority_score` for each ticker
- `keep_all`: Keep all entries (for debugging or when different triggers matter)

**Rationale**: From a user perspective, seeing one entry per ticker with the most compelling reason is better than seeing 3 entries for the same stock with different reasons.

### D-026-2: Stable Sort

The ranking MUST use a stable sort (Python's `sorted()` is stable). This preserves the original ordering for entries with equal scores, which provides deterministic output.

### D-026-3: Minimum Score Threshold

Entries below `config.min_score` (default 0.1) MUST be filtered out. This prevents noise from low-relevance entries cluttering the watchlist.

### D-026-4: Top-N Selection

The final watchlist MUST contain at most `config.max_entries` entries (default 20). This prevents overwhelming the user with too many research items.

**Rationale**: Research quality degrades with quantity. 20 entries per day is a reasonable cognitive load for a focused research session.

### D-026-5: Score Preservation

The `priority_score` written to the final `WatchlistEntry` MUST be the `total_score` from `ScoredEntry`, rounded to 2 decimal places for readability:

```python
entry.priority_score = round(se.total_score, 2)
```

## Integration Points

- **F-022**: Receives `ScoredEntry[]` from the scoring pipeline
- **F-027**: `config.min_score` and `config.max_entries` come from ScoringConfig
- **F-021**: Writes final `priority_score` and `reason` to WatchlistEntry
- **Existing `save_watchlist()`**: Receives ranked entries for YAML persistence

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| All entries filtered out (empty watchlist) | MEDIUM | Log warning, return empty list |
| Dedup loses important context | LOW | `keep_all` strategy available via config |
| Sort instability with equal scores | LOW | Python sorted() is stable |
