# Feature Spec: F-026 - Ranking and Filtering

**Priority**: Medium
**Contributing Roles**: system-architect, data-architect, product-manager
**Status**: Final (conflicts resolved)

## 1. Requirements Summary

- Watchlist entries MUST be sorted by priority_score descending
- Tie-breaking MUST use ticker alphabetical order for deterministic output
- Deduplication MUST keep the highest-scoring entry per ticker (default strategy)
- Minimum score filter MUST remove entries below config.min_priority_score (default 0.1)
- Top-N selection MUST limit output to config.max_entries (default 20)
- At-least-one guarantee: if any candidates exist, at least 1 entry MUST be returned
- Ranking MUST be deterministic: identical inputs produce identical order
- Filter application order: min_score -> trigger_type -> market -> max_entries
- Filters MUST be AND-combined (no OR logic in MVP)
- RankedWatchlist is an immutable output structure (frozen dataclass)

## 2. Design Decisions [CORE SECTION]

### D-026-1: Stable Sort by priority_score Descending

**Decision**: Entries MUST be sorted by priority_score descending using Python's stable `sorted()`.

**Context**: All roles agree on descending sort by priority_score. The data-architect proposes tie-breaking by ticker alphabetically; the product-manager proposes tie-breaking by event timestamp.

**Options Considered**:
- [system-architect] Stable sort by priority_score descending
- [data-architect] Sort by (-priority_score, ticker) for deterministic tie-breaking
- [product-manager] Tie-break by event timestamp (most recent first)

**Chosen Approach**: Sort by priority_score descending, with ticker alphabetical tie-breaking for determinism. The data-architect's approach is adopted because tickers are unique per day and provide a stable, deterministic tiebreaker. Event timestamp is less reliable because multiple events may exist per ticker.

```python
sorted_entries = sorted(entries, key=lambda e: (-e.priority_score, e.ticker))
```

**Trade-offs**: Deterministic output vs. less intuitive tiebreaker (ticker vs. timestamp). The ticker approach is more reliable because it is always available and deterministic.

**Source**: data-architect (tiebreaker), system-architect (stable sort), product-manager (descending order)

### D-026-2: Deduplication Strategy

**Decision**: Deduplication MUST default to `highest_score` strategy: keep only the entry with the highest `priority_score` for each ticker.

**Context**: A single ticker may appear in multiple entries (event-driven AND signal-driven AND portfolio review). From a user perspective, seeing one entry per ticker with the most compelling reason is better than seeing 3 entries for the same stock.

**Options Considered**:
- [system-architect] highest_score (default) or keep_all (for debugging)
- [data-architect] Dedup by ticker, keep highest score

**Chosen Approach**: Default to `highest_score`. The `keep_all` strategy is available via config for debugging but is not the default. (All roles consensus)

**Trade-offs**: Cleaner output (one entry per ticker) vs. loss of context from multiple triggers. The trade-off is favorable for user experience.

**Source**: system-architect, data-architect (consensus)

### D-026-3: Minimum Score Threshold

**Decision**: Entries below `config.min_priority_score` (default 0.1) MUST be filtered out before ranking.

**Context**: The system-architect proposes default 0.1; the product-manager proposes default 0.2. The data-architect proposes configurable min_priority_score.

**Options Considered**:
- [system-architect] min_score = 0.1
- [product-manager] min_score = 0.2 (default threshold)
- [data-architect] min_priority_score configurable

**Chosen Approach**: Default 0.1 from system-architect. The product-manager's 0.2 may be too aggressive for initial deployment — it could filter out valid entries in a sparse market day. The 0.1 default is more conservative and can be adjusted via F-027.

**Trade-offs**: Conservative threshold (0.1) includes more entries vs. aggressive threshold (0.2) produces a tighter list. The conservative approach is safer for initial deployment.

**Source**: system-architect (default value), data-architect (configurability), product-manager (alternative considered)

### D-026-4: Top-N Selection with At-Least-One Guarantee

**Decision**: The final watchlist MUST contain at most `config.max_entries` entries (default 20). If any candidates exist, at least 1 entry MUST be returned regardless of threshold.

**Context**: The product-manager requires an at-least-one guarantee as a UX requirement. A user who opens an empty watchlist thinks the system is broken.

**Options Considered**:
- [system-architect] max_entries = 20, no at-least-one guarantee
- [product-manager] At-least-one guarantee: return highest-scoring entry if any exist

**Chosen Approach**: Top-N with at-least-one guarantee. If all entries are filtered out by min_score but at least one entry existed, return the highest-scoring entry with a note that it falls below the threshold.

**Trade-offs**: Better UX (no empty watchlist) vs. potentially including a low-quality entry. The trade-off is favorable because showing one entry is better than showing none.

**Source**: product-manager (at-least-one guarantee), system-architect (top-N)

### D-026-5: Filter Application Order

**Decision**: Filters MUST be applied in this order: min_score -> trigger_type -> market -> max_entries.

**Context**: The data-architect defines the filter order. Min score first prevents unnecessary processing of low-quality entries.

**Options Considered**:
- [data-architect] min_score -> trigger_type -> market -> max_entries
- [product-manager] Category filtering (inclusion/exclusion)

**Chosen Approach**: Adopt data-architect's filter order. Min score first is efficient because it reduces the candidate set before applying more expensive filters. Max entries is last because it is a simple truncation.

**Trade-offs**: Efficient processing order vs. potentially counterintuitive filter composition. The order is logical and efficient.

**Source**: data-architect

### D-026-6: RankedWatchlist Output Structure

**Decision**: The ranking function MUST return a RankedWatchlist frozen dataclass containing sorted entries, metadata, and counts.

**Context**: The data-architect defines RankedWatchlist as an immutable output. The system-architect uses a simpler list-based approach.

**Options Considered**:
- [data-architect] RankedWatchlist frozen dataclass with entries, total_count, filtered_count
- [system-architect] list[WatchlistEntry] return type

**Chosen Approach**: Adopt data-architect's RankedWatchlist for the internal ranking function. The `generate_daily()` API returns `list[WatchlistEntry]` (EP-008), but the ranking function returns RankedWatchlist for auditability.

```python
@dataclass(frozen=True)
class RankedWatchlist:
    target_date: date
    entries: tuple[WatchlistEntry, ...]
    total_count: int
    filtered_count: int
    generation_timestamp: datetime
```

**Trade-offs**: Rich metadata for debugging vs. simpler return type. The metadata is valuable for audit trails and debugging.

**Source**: data-architect (RankedWatchlist), system-architect (API compatibility)

## 3. Interface Contract

### Ranking Function

```python
def rank_and_filter(
    scored_entries: list[ScoredEntry],
    config: ScoringConfig,
    target_date: date,
) -> RankedWatchlist:
    """Rank and filter scored entries into final watchlist."""
```

### RankedWatchlist

```python
@dataclass(frozen=True)
class RankedWatchlist:
    target_date: date
    entries: tuple[WatchlistEntry, ...]  # Sorted by priority_score descending
    total_count: int
    filtered_count: int
    generation_timestamp: datetime
```

### Pipeline Flow

```
ScoredEntry[] -> dedup -> filter(min_score) -> filter(trigger_type) -> filter(market) -> sort(desc) -> top(N) -> extract WatchlistEntry -> RankedWatchlist
```

Note: The final step extracts `WatchlistEntry` from each `ScoredEntry.entry` to populate `RankedWatchlist.entries`. The `ScoredEntry` wrapper is discarded after ranking; only the enriched `WatchlistEntry` (with `priority_score` and `reason` set) is persisted.

### Filter Types

| Filter | Config Key | Default | Behavior |
|--------|-----------|---------|----------|
| Min score | `min_priority_score` | 0.1 | Remove entries below threshold |
| Max entries | `max_entries` | 20 | Limit output count |
| Trigger type | `exclude_triggers` | [] | Remove entries matching excluded trigger types |
| Market | `allowed_markets` | ["CN_A"] | Keep only entries from allowed markets |

## 4. Constraints & Risks

| Constraint | Type | Mitigation |
|------------|------|------------|
| Deterministic ranking | MUST | Stable sort with deterministic tiebreaker (ticker) |
| At-least-one guarantee | MUST | Return highest-scoring entry if any candidates exist |
| Filter composition AND-combined | MUST | No OR logic in MVP |
| Default config works without user intervention | MUST | Defaults produce reasonable watchlist |
| Score preservation | MUST | priority_score rounded to 4 decimal places in output (consistent with F-021 schema contract) |

| Risk | Severity | Mitigation |
|------|----------|------------|
| All entries filtered out (empty watchlist) | MEDIUM | At-least-one guarantee prevents this |
| Dedup loses important context | LOW | keep_all strategy available via config |
| Sort instability with equal scores | LOW | Python sorted() is stable; ticker tiebreaker |
| max_entries = 0 produces empty watchlist | LOW | Validate > 0 or treat as None |

## 5. Acceptance Criteria

- [ ] Entries sorted by priority_score descending
- [ ] Tie-breaking by ticker alphabetical order
- [ ] Deduplication keeps highest-scoring entry per ticker
- [ ] Min score filter removes entries below threshold (default 0.1)
- [ ] Top-N selection limits output to max_entries (default 20)
- [ ] At-least-one guarantee: at least 1 entry returned if any candidates exist
- [ ] Ranking is deterministic for identical inputs
- [ ] Filter application order: min_score -> trigger_type -> market -> max_entries
- [ ] RankedWatchlist is a frozen dataclass with entries, total_count, filtered_count
- [ ] filtered_count accurately reflects entries removed at all filter stages
- [ ] Score preservation: priority_score rounded to 4 decimal places in output (consistent with F-021)

## 6. Detailed Analysis References

- @../system-architect/analysis-F-026-ranking-and-filtering.md — Pipeline flow, deduplication, stable sort, score preservation
- @../data-architect/analysis-F-026-ranking-and-filtering.md — RankedWatchlist, filter types, filter application order
- @../product-manager/analysis-F-026-ranking-and-filtering.md — User stories, at-least-one guarantee, top-N control
- @../guidance-specification.md#feature-decomposition — F-026 definition and related roles

## 7. Cross-Feature Dependencies

- **Depends on**: F-021 (WatchlistEntry schema with priority_score), F-022 (scoring engine produces ScoredEntry)
- **Required by**: F-028 (tests validate ranking and filtering)
- **Shared patterns**: Stable sort, frozen dataclass for output
- **Integration points**:
  - F-022: Receives ScoredEntry[] from the scoring pipeline
  - F-025: IndexConstituent filter applied during market filtering stage
  - F-027: config.min_score, config.max_entries, config.exclude_triggers (deferred to iteration 2)
  - Existing `save_watchlist()`: Receives ranked entries for YAML persistence
