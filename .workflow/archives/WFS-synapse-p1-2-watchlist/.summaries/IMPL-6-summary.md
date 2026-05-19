# Task: IMPL-6 Ranking & Filtering

## Implementation Summary

### Files Modified
- `synapse/core/projection/watchlist_generator.py`: Added rank_entries(), filter_entries(), updated generate_daily()
- `tests/unit/test_projection.py`: Added TestRankingFiltering class with 17 tests

### Content Added
- **rank_entries()** (`watchlist_generator.py:38`): Stable sort by priority_score descending, tie-break by ticker alphabetical order
- **filter_entries()** (`watchlist_generator.py:47`): Filter pipeline: exclude_triggers -> min_priority_score -> dedup by ticker -> top-N cutoff
- **DEFAULT_MAX_ENTRIES** (`watchlist_generator.py:32`): Constant = 20
- **DEFAULT_MIN_PRIORITY_SCORE** (`watchlist_generator.py:33`): Constant = 0.1
- **generate_daily()** (`watchlist_generator.py:123`): Updated signature with max_entries, min_priority_score, exclude_triggers params; integrates rank_entries() and filter_entries() after scoring

### Acceptance Criteria Verification
- [x] rank_entries() sorts by priority_score descending
- [x] Tie-breaking uses ticker alphabetical order
- [x] filter_entries() applies top-N cutoff
- [x] filter_entries() applies min_priority_score threshold
- [x] filter_entries() deduplicates by ticker (highest score wins)
- [x] generate_daily() integrates ranking and filtering

## Outputs for Dependent Tasks

### Available Functions
```python
from synapse.core.projection.watchlist_generator import (
    rank_entries,
    filter_entries,
    generate_daily,
    DEFAULT_MAX_ENTRIES,
    DEFAULT_MIN_PRIORITY_SCORE,
)
```

### Integration Points
- **generate_daily()**: Now accepts `max_entries`, `min_priority_score`, `exclude_triggers` params
- **rank_entries()**: Can be used standalone to sort any scored entry list
- **filter_entries()**: Can be used standalone to filter/dedup any ranked entry list

## Status: Complete
