# F-025: Market Semantics Validation -- System Architect Analysis

## Overview

Integrate P1-1 Market Semantics (TradingCalendar, NorthboundFlow, IndexConstituent) into the scoring pipeline to filter and adjust scores based on market-level context. This ensures the watchlist respects market reality (trading days, halted stocks, index membership).

## Current State Analysis

The existing market semantics module at `synapse/core/market/semantics.py` provides:
- `SymbolType` enum and `PRICE_LIMITS` dict
- `validate_t1_settlement()` -- T+1 settlement validation
- `is_suspended()` -- suspension check

The `synapse/core/market/` directory likely also contains:
- `calendar.py` -- `is_trading_day()`, `next_trading_day()` (referenced by semantics.py)
- NorthboundFlow and IndexConstituent data (referenced in guidance-specification)

## Architecture: Market Validation Layer

### Scoring Function: `score_market_context()`

```python
def score_market_context(
    entry: WatchlistEntry,
    context: ScoringContext,
) -> tuple[float, str]:
    """Score market context adjustments."""
    if context.market_data is None:
        return 0.5, "Market data unavailable"

    score = 0.5  # Neutral default
    reasons = []

    # Trading day validation
    if not context.market_data.is_trading_day(context.target_date):
        return 0.0, "Not a trading day"

    # Suspension check
    if context.market_data.is_suspended(entry.ticker, context.target_date):
        return 0.0, "Stock suspended"

    # Northbound flow signal
    if context.market_data.northbound_flow:
        flow_signal = _evaluate_northbound_flow(
            entry.ticker, context.market_data.northbound_flow
        )
        if flow_signal > 0:
            score += 0.15
            reasons.append("northbound inflow")
        elif flow_signal < 0:
            score -= 0.10
            reasons.append("northbound outflow")

    # Index membership boost
    if context.market_data.index_constituents:
        if entry.ticker in context.market_data.index_constituents:
            score += 0.10
            reasons.append("index constituent")

    score = max(0.0, min(1.0, score))
    reason = f"Market: {', '.join(reasons) if reasons else 'neutral'} (score: {score:.2f})"
    return score, reason
```

### MarketSemanticsData Transfer Object

```python
@dataclass(frozen=True)
class MarketSemanticsData:
    """Market-level context for scoring."""
    is_trading_day: bool
    suspended_tickers: set[str]
    northbound_flow: Optional[dict[str, float]]  # ticker -> net flow
    index_constituents: Optional[set[str]]  # set of constituent tickers
```

## Design Decisions

### D-025-1: Trading Day Gate

If `target_date` is NOT a trading day, the entire watchlist generation SHOULD be skipped. This is a hard gate, not a scoring adjustment.

**Rationale**: Generating a watchlist for a non-trading day is misleading. The watchlist is for today's research, and research only matters on trading days.

**Implementation**: Check `is_trading_day()` BEFORE entering the scoring pipeline. If false, return empty `ScoringResult` with a warning.

### D-025-2: Suspension as Hard Filter

Suspended stocks MUST be filtered out entirely (score = 0.0), not just downgraded. A suspended stock cannot be traded, so researching it has limited value.

### D-025-3: Northbound Flow as Soft Signal

Northbound capital flow is a directional signal (inflow = bullish, outflow = bearish). It SHOULD adjust scores by +/- 0.15, not dominate the scoring.

**Rationale**: Northbound flow is one of many signals. Over-weighting it could distort the watchlist.

### D-025-4: Index Membership as Moderate Boost

Index constituents (e.g., CSI 300, CSI 500) receive a moderate boost (+0.10) because:
- Index constituents have higher institutional attention
- Index rebalancing events affect these stocks
- They are more liquid and tradeable

### D-025-5: Neutral Default on Missing Data

When market data is unavailable, the function returns 0.5 (neutral). This ensures missing market data does not penalize or artificially boost entries.

## Integration Points

- **F-022**: `score_market_context()` is one stage in the scoring pipeline
- **Existing `market/semantics.py`**: Uses `is_trading_day()`, `is_suspended()` patterns
- **F-026**: Market validation happens BEFORE ranking (hard filters applied first)
- **P1-1 Market Semantics**: Future integration point for TradingCalendar, NorthboundFlow, IndexConstituent adapters

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Market data source unavailable | MEDIUM | Return neutral score, log warning |
| NorthboundFlow data stale | LOW | Check data freshness timestamp |
| Index constituent list outdated | LOW | Use cached list, refresh daily |
