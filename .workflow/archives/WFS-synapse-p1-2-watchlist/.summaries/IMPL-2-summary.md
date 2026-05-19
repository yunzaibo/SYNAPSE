# Task: IMPL-2 Scoring Engine Core

## Implementation Summary

### Files Created
- `synapse/core/projection/scoring/__init__.py`: Package init with public exports
- `synapse/core/projection/scoring/types.py`: Data types for scoring pipeline
- `synapse/core/projection/scoring/aggregator.py`: Weighted sum aggregation logic
- `synapse/core/projection/scoring/engine.py`: Pipeline-based scoring engine

### Files Modified
- `synapse/core/projection/watchlist_generator.py`: Integrated scoring engine into generate_daily()
- `tests/unit/test_projection.py`: Added 28 scoring engine tests

### Content Added

**MarketData** (`scoring/types.py:24`): Market-level data with sentiment, breadth, volatility scores. Defaults to 0.5 (neutral).

**ScoringContext** (`scoring/types.py:48`): Immutable context carrying events, signals, positions, target_date, config, market_data.

**ScoredEntry** (`scoring/types.py:82`): WatchlistEntry wrapper with total_score, component_scores dict, and reason string. Validates score in [0.0, 1.0].

**ScoringResult** (`scoring/types.py:108`): Batch result with scored entries, target_date, generation_timestamp, config_hash for traceability.

**normalize_weights()** (`scoring/aggregator.py:28`): Normalizes weights to sum to 1.0. Emits logging.warning when auto-normalization occurs.

**aggregate_scores()** (`scoring/aggregator.py:56`): Weighted sum formula: total = sum(w_i * s_i). Missing data contributes 0.0, except market which contributes 0.5 (neutral).

**build_reason()** (`scoring/aggregator.py:82`): Builds human-readable reason string from component scores.

**_score_signal()** (`scoring/engine.py:38`): Scores based on signal strength (weak=0.3, medium=0.6, strong=1.0) with count bonus (diminishing returns, max +0.3).

**_score_event()** (`scoring/engine.py:66`): Scores based on event severity and confidence: (severity + confidence) / 2.

**_score_portfolio()** (`scoring/engine.py:88`): Scores based on thesis_status: active=0.3, weakened=0.7, invalidated=1.0.

**_score_market()** (`scoring/engine.py:108`): Scores based on market data: (sentiment + breadth + (1-volatility)) / 3. Returns 0.5 when data missing.

**ScoringEngine** (`scoring/engine.py:126`): Pipeline engine with register/unregister for custom dimensions. score() runs all functions, aggregates, sorts descending. score_single() for convenience.

### Default Weights
- signal: 0.35
- event: 0.30
- portfolio: 0.20
- market: 0.15

### Integration with generate_daily()
- Added optional `market_data: Optional[MarketData]` parameter
- After building entries, runs ScoringEngine.score() and updates priority_score/reason
- Returns entries sorted by priority_score descending
- Backward compatible: existing calls without market_data still work

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.core.projection.scoring import (
    ScoringEngine,
    ScoredEntry,
    ScoringResult,
    ScoringContext,
    MarketData,
    aggregate_scores,
    DEFAULT_WEIGHTS,
    normalize_weights,
)
```

### Integration Points
- **ScoringEngine.register()**: Add custom scoring functions for IMPL-3/4/5
- **ScoringContext**: Pass events, signals, positions, market_data to engine
- **generate_daily()**: Now returns scored entries with priority_score populated

### Usage Examples
```python
# Basic usage
engine = ScoringEngine()
context = ScoringContext(events=events, signals=signals, positions=positions)
result = engine.score(entries, context)
for scored in result.entries:
    print(f"{scored.entry.ticker}: {scored.total_score:.2f} - {scored.reason}")

# With custom weights
engine = ScoringEngine(weights={"signal": 0.5, "event": 0.5, "portfolio": 0.0, "market": 0.0})

# Register custom scorer
def my_scorer(entry, ctx):
    return 0.8, "custom reason"
engine.register("custom_dim", my_scorer)

# Via generate_daily()
entries = generate_daily(events, signals, positions, market_data=MarketData(sentiment_score=0.9))
```

## Test Results
- 28 new scoring tests added
- All 51 tests pass (23 original + 28 new)
- Coverage: aggregator, types, engine, generate_daily integration

## Status: Complete
