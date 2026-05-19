# Task: IMPL-3 Event-Driven Scoring

## Implementation Summary

### Files Created
- `synapse/core/projection/scoring/event_scorer.py`: Decay-aware event scoring module

### Files Modified
- `synapse/core/projection/scoring/engine.py`: Replaced `_score_event` with `score_event_decay` from event_scorer; imported `score_market_context` from market_scorer (linter auto-fix)
- `synapse/core/projection/scoring/__init__.py`: Added `DecayScore` and `score_event_decay` exports
- `tests/unit/test_projection.py`: Added 14 event scoring tests (TestDecayScore + TestEventScoring)

### Content Added

#### DecayScore (`event_scorer.py`)
- **DecayScore** (`event_scorer.py:30`): Frozen dataclass value object with `score` (float, [0.0, 1.0]) and `reason` (str)
  - `as_tuple()` method returns `(score, reason)` for ScoringFunction interface
  - Validates score range in `__post_init__`
  - Immutable (frozen=True)

#### score_event_decay (`event_scorer.py`)
- **score_event_decay(entry, ctx)** (`event_scorer.py:58`): ScoringFunction-compatible entry point
  - Filters events by `entry.ticker in event.related_tickers`
  - Computes age from `event.created_at` to `ctx.target_date` (in days)
  - Uses `apply_category_decay()` from `event/lifecycle.py` for category-specific exponential decay
  - Initial impact: `(severity + confidence) / 2` (same formula as legacy)
  - Returns highest decayed score across all relevant events
  - Missing events contribute 0.0

- **_compute_event_decay(event, target_date)** (`event_scorer.py:82`): Internal helper
  - Computes age in days, applies category decay, returns DecayScore with detailed reason

### Integration Points

#### Engine Registration
- `ScoringEngine.__init__` registers `score_event_decay` as the "event" dimension (replaces legacy `_score_event`)
- Weight mapping: "event" = 0.30 (unchanged)
- Category half-lives reused from `event/lifecycle.py`: earnings=6.5d, policy=1.5d, sentiment=2.0d, theme=4.0d, capital_flow=2.0d, corporate_action=5.0d, policy_change=2.5d, macro_shift=3.0d, social_sentiment=0.5d

#### Exports
```python
from synapse.core.projection.scoring import DecayScore, score_event_decay
```

### Usage Examples
```python
# Direct use
score, reason = score_event_decay(entry, scoring_context)

# Via engine (auto-registered as "event" dimension)
engine = ScoringEngine()
result = engine.score([entry], context)
event_score = result.entries[0].component_scores["event"]

# DecayScore value object
from synapse.core.projection.scoring.event_scorer import _compute_event_decay
ds = _compute_event_decay(event, target_date)
print(f"Decayed score: {ds.score:.4f}, reason: {ds.reason}")
```

## Verification

### Tests
- `TestDecayScore`: 5 tests (validation, boundaries, immutability, as_tuple)
- `TestEventScoring`: 9 tests (missing events, ticker matching, fresh events, decay ordering, multi-event selection, social_sentiment fast decay, reason formatting, created_at age computation, engine integration)
- **Result**: 87/87 passed, 0 failures, 0 regressions

### Acceptance Criteria
- [x] score_event_decay() function implemented
- [x] Reuses apply_category_decay() from event/lifecycle.py
- [x] DecayScore value object with score and reason
- [x] Newer events rank higher, stale events decay
- [x] Missing events contribute 0.0

## Status: Complete
