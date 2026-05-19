# F-025: Market Semantics Validation — Data Architect Analysis

## Feature Summary

Integrate P1-1 Market Semantics (TradingCalendar, NorthboundFlow, IndexConstituent) into the watchlist generation pipeline. This is a validation and enrichment layer, not a scoring layer.

## Data Dependencies

### TradingCalendar

**Purpose**: Validate that `target_date` is a trading day. Non-trading days SHOULD produce empty watchlists (no market data to score).

**Data consumed**:
- `target_date` parameter
- TradingCalendar.is_trading_day(date) → bool

**Data produced**: Boolean gate — proceed or return empty list.

**Storage**: No new storage. TradingCalendar is a P1-1 service, called via Dependency Injection.

### NorthboundFlow

**Purpose**: Enrich watchlist entries with northbound capital flow data. Tickers with significant northbound buying MAY receive a score boost.

**Data consumed**:
- `target_date`
- NorthboundFlow.get_flow(date, ticker) → FlowData

**FlowData structure** (from P1-1):
```python
@dataclass(frozen=True)
class FlowData:
    net_buy_amount: float    # Net buy in CNY (negative = sell)
    buy_amount: float
    sell_amount: float
```

**Data produced**: Enrichment for scoring — `northbound_boost` component.

**Scoring integration**:
```
if flow_data.net_buy_amount > threshold_high:
    northbound_boost = 0.3
elif flow_data.net_buy_amount > threshold_low:
    northbound_boost = 0.1
else:
    northbound_boost = 0.0
```

Thresholds SHOULD be configurable in ScoringConfig.

### IndexConstituent

**Purpose**: Validate that tickers are valid A-share constituents. Filter out non-constituent tickers if configured.

**Data consumed**:
- IndexConstituent.get_constituents(index_code) → list[str]

**Data produced**: Filter gate — optionally remove non-constituent entries.

**Filtering mode**:
- If `filter_non_constituent = true` in ScoringConfig: entries with tickers NOT in any configured index are removed
- If `filter_non_constituent = false` (default): all entries pass, constituent status is informational only

## Integration Architecture

```
generate_daily() enhanced flow:
  1. TradingCalendar gate: is_trading_day(target_date)?
     - No → return empty list
     - Yes → continue
  2. Build raw entries from events + signals + positions (existing)
  3. Enrichment pass (new):
     - For each entry: lookup NorthboundFlow data
     - For each entry: check IndexConstituent status
  4. Scoring pass (new):
     - Include northbound_boost in component_scores
  5. Filtering pass (new):
     - Apply IndexConstituent filter if configured
  6. Ranking pass (new):
     - Sort by priority_score
```

## Storage Impact

- Market Semantics services are P1-1 — P1-2 DOES NOT store their data
- P1-2 calls P1-1 services via Dependency Injection at generation time
- NorthboundFlow enrichment data is ephemeral — used during scoring, not persisted in WatchlistEntry

## Constraints

- Market Semantics integration MUST be optional — if P1-1 services are unavailable, the pipeline MUST continue with degraded scoring (graceful degradation)
- TradingCalendar gate is the ONLY hard gate — non-trading days MUST produce empty lists
- NorthboundFlow and IndexConstituent are soft enrichments — missing data contributes 0.0 to scoring

## Risks

- **Medium**: P1-1 services may not be available at generation time. Mitigation: wrap all P1-1 calls in try/except, return neutral defaults on failure.
- **Low**: NorthboundFlow data may lag by 1 day (T+1 settlement). Scoring SHOULD use the most recent available data, not assume real-time.
