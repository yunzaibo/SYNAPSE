# Task: IMPL-1 WatchlistEntry Schema Extension

## Implementation Summary

### Files Modified
- `synapse/core/schemas/watchlist.py`: Added priority_score and reason fields, __post_init__ validation, updated to_dict/from_dict
- `tests/unit/test_schemas.py`: Added 5 new tests for priority_score defaults, validation, boundary, round-trip, and lazy upcast

### Content Added

**WatchlistEntry** (`synapse/core/schemas/watchlist.py:83-84`):
- `priority_score: float = 0.0` -- Normalized priority score in [0.0, 1.0]
- `reason: str = ''` -- Human-readable scoring explanation (10-200 chars enforced by scoring engine)

**__post_init__** (`synapse/core/schemas/watchlist.py:93-97`):
- Validates `priority_score` is in [0.0, 1.0], raises `ValueError` if out of range

**to_dict()** (`synapse/core/schemas/watchlist.py:111-112`):
- Serializes `priority_score` and `reason` to dict

**from_dict()** (`synapse/core/schemas/watchlist.py:133-134`):
- Deserializes with Lazy Upcast defaults: `priority_score` defaults to `0.0`, `reason` defaults to `''`

### Tests Added (`tests/unit/test_schemas.py`)
- `test_priority_score_defaults` -- Verifies default values (0.0, '')
- `test_priority_score_validation` -- Verifies ValueError for -0.1 and 1.1
- `test_priority_score_boundary` -- Verifies 0.0 and 1.0 are accepted
- `test_round_trip_with_priority` -- Full round-trip with priority_score=0.85
- `test_round_trip_lazy_upcast_missing_fields` -- Missing fields get defaults from from_dict()

## Outputs for Dependent Tasks

### Available Fields
```python
# WatchlistEntry now has:
entry.priority_score  # float, 0.0-1.0, default 0.0
entry.reason          # str, default ''
```

### Integration Points
- **Scoring Engine (IMPL-2)**: Set `priority_score` and `reason` on WatchlistEntry after scoring
- **Ranking (IMPL-6)**: Sort by `priority_score` descending for watchlist ranking
- **from_dict() backward compat**: Existing data without priority_score/reason deserializes correctly with defaults

### Usage Examples
```python
# Create with priority
entry = WatchlistEntry(
    id="wl_001",
    ticker="600519",
    priority_score=0.85,
    reason="技术面突破关键阻力位",
)

# Validation
WatchlistEntry(id="bad", priority_score=1.5)  # raises ValueError

# Round-trip
d = entry.to_dict()
entry2 = WatchlistEntry.from_dict(d)  # preserves priority_score and reason
```

## Status: Complete
