# Task: IMPL-4 Portfolio-Aware Scoring

## Implementation Summary

### Files Created
- `synapse/core/projection/scoring/portfolio_scorer.py`: Portfolio-aware boost scoring module

### Files Modified
- `synapse/core/projection/scoring/engine.py`: Replaced `_score_portfolio()` with wrapper using portfolio_scorer
- `synapse/core/projection/scoring/__init__.py`: Added ThesisAttentionMap, build_thesis_attention_map, score_portfolio_boost exports
- `tests/unit/test_projection.py`: Updated existing portfolio test, added 13 new portfolio scoring tests

### Content Added

**portfolio_scorer.py** (`synapse/core/projection/scoring/portfolio_scorer.py`):
- `ThesisAttentionMap`: TypeAlias for `dict[str, tuple[ThesisStatus, AttentionState]]`
- `build_thesis_attention_map(positions)`: Builds ticker -> (ThesisStatus, AttentionState) map from Position list
- `score_portfolio_boost(ticker, thesis_attention_map)`: Computes combined thesis + attention boost, clamped to [0.0, 1.0]
- `_thesis_boost(status)`: Maps ThesisStatus to boost value (INVALIDATED=0.5, WEAKENED=0.35, ACTIVE=0.15)
- `_attention_boost(state)`: Maps AttentionState to boost value (RISING=0.25, FADING=0.10, STABLE=0.05)

**Constants**:
- `THESIS_INVALIDATED_BOOST = 0.5`
- `THESIS_WEAKENED_BOOST = 0.35`
- `THESIS_ACTIVE_BOOST = 0.15`
- `ATTENTION_RISING_BOOST = 0.25`
- `ATTENTION_FADING_BOOST = 0.10`
- `ATTENTION_STABLE_BOOST = 0.05`
- `MAX_BOOST = 0.75` (sum of max thesis + max attention)

**engine.py** (`synapse/core/projection/scoring/engine.py`):
- `_score_portfolio()` now delegates to `score_portfolio_boost()` via `build_thesis_attention_map()`
- The "portfolio" dimension now considers both thesis_status AND attention_state

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.core.projection.scoring.portfolio_scorer import (
    ThesisAttentionMap,
    build_thesis_attention_map,
    score_portfolio_boost,
    THESIS_INVALIDATED_BOOST,
    THESIS_WEAKENED_BOOST,
    THESIS_ACTIVE_BOOST,
    ATTENTION_RISING_BOOST,
    ATTENTION_FADING_BOOST,
    ATTENTION_STABLE_BOOST,
    MAX_BOOST,
)
```

### Integration Points
- **ScoringEngine**: Portfolio dimension now uses portfolio_scorer (thesis + attention combined boost)
- **ThesisAttentionMap**: Can be pre-built from positions and passed to score_portfolio_boost() directly
- **Boost constants**: Available for use in weighting or display logic

### Usage Examples
```python
# Build map from positions
positions = [pos1, pos2, pos3]
ta_map = build_thesis_attention_map(positions)

# Score a single ticker
score, reason = score_portfolio_boost("600519", ta_map)

# Use with ScoringEngine (automatic via ScoringContext)
engine = ScoringEngine()
result = engine.score(entries, context)  # portfolio dimension uses new scoring
```

## Acceptance Criteria Verification
- [x] score_portfolio_boost() function implemented
- [x] ThesisAttentionMap = dict[str, tuple[ThesisStatus, AttentionState]]
- [x] Thesis status boosts: INVALIDATED (0.5) > WEAKENED (0.35) > ACTIVE (0.15)
- [x] Attention state boosts: RISING (0.25) > FADING (0.10) > STABLE (0.05)
- [x] Missing positions contribute 0.0

## Test Results
- 63 tests passed, 0 failed
- 13 new portfolio scoring tests added (TestPortfolioScoring class)
- All existing tests continue to pass

## Status: Complete
