# Task: IMPL-5 Market Semantics Scoring

## Implementation Summary

### Files Created
- `synapse/core/projection/scoring/market_scorer.py`: Market semantics scorer using TradingCalendar, NorthboundFlow, IndexConstituent

### Files Modified
- `synapse/core/projection/scoring/engine.py`: Replaced `_score_market` with `score_market_context` import and registration
- `synapse/core/projection/scoring/__init__.py`: Added `score_market_context` export
- `tests/unit/test_projection.py`: Added 10 market scoring tests (TestMarketScoring class)

### Content Added
- **score_market_context()** (`market_scorer.py:27`): ScoringFunction implementing 5-step market semantics scoring
  - Step 1: TradingCalendar validation via `is_trading_day()` -- returns neutral (0.5) if not trading day
  - Step 2: Legacy MarketData scoring (sentiment, breadth, volatility) for backward compatibility
  - Step 3: NorthboundFlow signal processing via `northbound_to_signals()` -- inflows boost, outflows reduce score
  - Step 4: IndexConstituent membership via `constituent_tickers()` -- tracked index members get +0.1 boost
  - Step 5: Clamp to [0.0, 1.0] and build reason string
  - Returns (0.5, "Market data unavailable") when no data is present

### Key Design Decisions
- Backward compatible: existing `MarketData` (sentiment/breadth/volatility) still works
- New data delivered via `ScoringContext.config` dict:
  - `config["northbound_records"]`: `list[NorthboundFlow]` for capital flow signals
  - `config["tracked_indices"]`: `list[str]` index codes (e.g., "000300.SH")
  - `config["data_dir"]`: str path to market data (defaults to "data/market")
- Score components: baseline 0.5 + northbound inflow boost (up to +0.3) - outflow penalty (up to -0.2) + index member boost (+0.1)
- FileNotFoundError on constituent_tickers gracefully skipped (index data may not exist)

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.core.projection.scoring.market_scorer import score_market_context
from synapse.core.projection.scoring import score_market_context  # also available
```

### Integration Points
- **ScoringEngine**: `score_market_context` registered as "market" dimension scorer
- **ScoringContext.config**: Pass northbound/index data via config dict
- **Usage example**:
  ```python
  ctx = ScoringContext(
      target_date=date(2026, 5, 18),
      market_data=MarketData(sentiment_score=0.7),
      config={
          "northbound_records": [NorthboundFlow(...)],
          "tracked_indices": ["000300.SH", "000905.SH"],
      },
  )
  ```

## Test Results
- 10 new tests added (TestMarketScoring class)
- All 10 market scoring tests pass
- 86/87 total tests pass (1 pre-existing failure in TestEventScoring unrelated to this change)

## Acceptance Criteria Verification
- [x] score_market_context() function implemented
- [x] TradingCalendar validates target_date is trading day
- [x] NorthboundFlow boosts score for large inflows
- [x] IndexConstituent filters universe to tracked indices
- [x] Missing market data returns neutral 0.5

## Status: Complete
