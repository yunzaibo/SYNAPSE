# F-028: Watchlist Tests -- System Architect Analysis

## Overview

Extend the existing test suite with comprehensive tests for the scoring engine, ranking/filtering, schema serialization, and integration with market semantics. The existing `test_projection.py` pattern provides the foundation.

## Current State Analysis

The existing test infrastructure uses:
- `py -m pytest -p no:asyncio` (Windows requirement per MEMORY.md)
- `test_projection.py` pattern for projection tests
- Dataclass-based schemas with `to_dict()`/`from_dict()` round-trip

No existing watchlist-specific tests were found. This is a greenfield test effort.

## Test Architecture

### Test Categories

| Category | Scope | Priority | Count Target |
|----------|-------|----------|-------------|
| Schema Round-Trip | F-021 | HIGH | 4 |
| Scoring Engine | F-022 | HIGH | 8 |
| Event Decay | F-023 | HIGH | 5 |
| Portfolio Scoring | F-024 | HIGH | 5 |
| Market Validation | F-025 | MEDIUM | 4 |
| Ranking/Filtering | F-026 | HIGH | 6 |
| Config Loading | F-027 | MEDIUM | 4 |
| Integration | Cross | HIGH | 3 |

### Test File Structure

```
tests/
  test_watchlist_schema.py      # F-021: Schema extension tests
  test_scoring_engine.py        # F-022: Core scoring tests
  test_event_decay_scoring.py   # F-023: Event decay integration
  test_portfolio_scoring.py     # F-024: Portfolio-aware scoring
  test_market_validation.py     # F-025: Market semantics tests
  test_ranking_filtering.py     # F-026: Ranking and filtering
  test_scoring_config.py        # F-027: Configuration tests
  test_watchlist_integration.py # Cross-feature integration
```

## Key Test Cases

### F-021: Schema Round-Trip Tests

```python
def test_watchlist_entry_with_priority_score():
    """priority_score and reason survive to_dict/from_dict round-trip."""
    entry = WatchlistEntry(
        id=generate_id("wl"),
        ticker="600519",
        priority_score=0.85,
        reason="Event: earnings surprise (score: 0.85)",
    )
    d = entry.to_dict()
    restored = WatchlistEntry.from_dict(d)
    assert restored.priority_score == 0.85
    assert restored.reason == "Event: earnings surprise (score: 0.85)"

def test_watchlist_entry_lazy_upcast_v1():
    """v1.0 dict without priority_score/reason creates valid v2.0 entry."""
    v1_dict = {"id": "wl_test1", "ticker": "600519"}  # no priority_score
    entry = WatchlistEntry.from_dict(v1_dict)
    assert entry.priority_score == 0.0
    assert entry.reason == ""

def test_priority_score_range_validation():
    """priority_score must be in [0.0, 1.0]."""
    with pytest.raises(ValueError):
        WatchlistEntry(id="wl_test", priority_score=1.5)
    with pytest.raises(ValueError):
        WatchlistEntry(id="wl_test", priority_score=-0.1)
```

### F-022: Scoring Engine Tests

```python
def test_scoring_deterministic():
    """Same inputs produce same scores."""
    entries = [WatchlistEntry(id="wl_1", ticker="600519")]
    context = ScoringContext(events=[], signals=[], positions=[], ...)
    result1 = score_entries(entries, context)
    result2 = score_entries(entries, context)
    assert result1[0].total_score == result2[0].total_score

def test_scoring_with_no_data():
    """Empty inputs produce zero scores."""
    entries = [WatchlistEntry(id="wl_1", ticker="600519")]
    context = ScoringContext(events=[], signals=[], positions=[], ...)
    scored = score_entries(entries, context)
    assert scored[0].total_score == 0.0

def test_scoring_aggregation_weights():
    """Score respects configured weights."""
    config = ScoringConfig(signal_weight=1.0, event_weight=0.0, ...)
    # ... test that signal dimension dominates
```

### F-026: Ranking Tests

```python
def test_ranking_descending_order():
    """Entries sorted by priority_score descending."""
    entries = [
        ScoredEntry(entry=WatchlistEntry(id="wl_1", ticker="A"), total_score=0.3),
        ScoredEntry(entry=WatchlistEntry(id="wl_2", ticker="B"), total_score=0.8),
        ScoredEntry(entry=WatchlistEntry(id="wl_3", ticker="C"), total_score=0.6),
    ]
    ranked = rank_and_filter(entries, ScoringConfig())
    assert [se.entry.ticker for se in ranked] == ["B", "C", "A"]

def test_ranking_dedup_highest_score():
    """Duplicate tickers keep highest-scoring entry."""
    entries = [
        ScoredEntry(entry=WatchlistEntry(id="wl_1", ticker="A"), total_score=0.3),
        ScoredEntry(entry=WatchlistEntry(id="wl_2", ticker="A"), total_score=0.8),
    ]
    ranked = rank_and_filter(entries, ScoringConfig())
    assert len(ranked) == 1
    assert ranked[0].entry.id == "wl_2"

def test_ranking_min_score_filter():
    """Entries below min_score are filtered out."""
    entries = [
        ScoredEntry(entry=WatchlistEntry(id="wl_1", ticker="A"), total_score=0.05),
    ]
    config = ScoringConfig(min_score=0.1)
    ranked = rank_and_filter(entries, config)
    assert len(ranked) == 0
```

## Design Decisions

### D-028-1: Test Isolation

Each test MUST be independent. No test should depend on the output of another test. This enables parallel test execution and isolated debugging.

### D-028-2: Fixture-Based Test Data

Test data MUST be defined as pytest fixtures, not inline in test functions. This enables reuse and maintenance:

```python
@pytest.fixture
def sample_event():
    return Event(
        id="evt_test1",
        event_type=EventType.EARNINGS,
        title="Q1 Earnings",
        event_date=date(2026, 5, 19),
        severity=0.8,
        confidence=0.9,
    )
```

### D-028-3: Determinism Testing

The scoring engine tests MUST verify determinism: same inputs produce identical outputs. This is critical for ADR-009 daily regeneration.

### D-028-4: Edge Case Coverage

Tests MUST cover:
- Empty inputs (no events, no signals, no positions)
- Single entry with all scoring dimensions
- Multiple entries with same ticker (dedup)
- All entries below min_score (empty result)
- Config with extreme weights (all zero, all one)
- Schema version mismatch (v1.0 dict -> v2.0 entry)

## Integration Points

- **F-021 through F-027**: Each feature's tests validate its specific behavior
- **Existing `test_projection.py`**: Follow same patterns and conventions
- **CI/CD**: Tests MUST pass before `git push` per CLAUDE.md rules

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Test data maintenance burden | LOW | Use fixtures, minimize inline data |
| Flaky tests from date dependency | MEDIUM | Mock `date.today()` in tests |
| Slow test execution | LOW | Tests are pure Python, no I/O |
