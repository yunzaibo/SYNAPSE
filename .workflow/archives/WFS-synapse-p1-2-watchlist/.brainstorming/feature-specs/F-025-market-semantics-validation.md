# Feature Spec: F-025 - Market Semantics Validation

**Priority**: Medium
**Contributing Roles**: system-architect, data-architect, product-manager
**Status**: Final (conflicts resolved)

## 1. Requirements Summary

- TradingCalendar MUST be used as a hard gate: non-trading days MUST produce empty watchlists
- NorthboundFlow MUST be used as a soft signal: inflow boosts score, outflow reduces score
- IndexConstituent MUST be used as a scope filter: index membership provides moderate score boost
- Market Semantics integration MUST be optional — missing P1-1 data produces degraded scoring, not failure
- TradingCalendar gate is the ONLY hard gate in the market semantics layer
- NorthboundFlow and IndexConstituent are soft enrichments — missing data contributes 0.0
- Market data unavailability returns neutral score 0.5 (from F-022 graceful degradation)
- The scoring function MUST be a pure function

## 2. Design Decisions [CORE SECTION]

### D-025-1: Trading Day Gate (Hard Gate)

**Decision**: If `target_date` is NOT a trading day, the entire watchlist generation SHOULD be skipped. This is a hard gate, not a scoring adjustment.

**Context**: Generating a watchlist for a non-trading day is misleading. The watchlist is for today's research, and research only matters on trading days. All roles agree on this constraint.

**Options Considered**:
- [system-architect] Hard gate: skip generation entirely on non-trading days
- [data-architect] Boolean gate: proceed or return empty list
- [product-manager] Non-trading-day events MUST NOT appear in watchlist

**Chosen Approach**: Check `is_trading_day()` BEFORE entering the scoring pipeline. If false, return empty list with a warning. This is consistent across all role analyses. (All roles consensus)

**Trade-offs**: Absolute correctness (no non-trading-day noise) vs. potential confusion if user expects a watchlist on weekends. The trade-off is favorable because generating a meaningless watchlist is worse than generating none.

**Source**: system-architect, data-architect, product-manager (consensus)

### D-025-2: Suspension as Hard Filter

[REVIEW-FLAG] D-025-2 title says "filtered out entirely" but the chosen approach says "score = 0.0, not removed from entry list." These are contradictory: "filtered out" implies removal, while score=0.0 implies retention at bottom. The chosen approach (score=0.0, retained) is the correct interpretation per the trade-off discussion. The title and requirement text should be updated to say "Suspended stocks MUST receive score = 0.0" rather than "filtered out entirely."

**Decision**: Suspended stocks MUST receive score = 0.0 (lowest possible market score), not removed from the entry list.

**Context**: A suspended stock cannot be traded, so researching it has limited value. The system-architect and data-architect agree on this constraint.

**Options Considered**:
- [system-architect] Hard filter: score = 0.0 for suspended stocks
- [data-architect] Filter gate: remove non-constituent entries if configured

**Chosen Approach**: Suspended stocks receive score = 0.0 in the market scoring function. They are not removed from the entry list but receive the lowest possible market score, ensuring they rank at the bottom.

**Trade-offs**: Clean filtering vs. potentially removing entries that users want to track for research purposes. The score=0.0 approach is less aggressive than removal, allowing users to still see suspended entries at the bottom.

**Source**: system-architect

### D-025-3: Northbound Flow as Soft Signal

**Decision**: Northbound capital flow MUST adjust scores by +/- 0.15 (inflow boost, outflow penalty), not dominate the scoring.

**Context**: Northbound flow is a directional signal (inflow = bullish, outflow = bearish). It is one of many signals. Over-weighting it could distort the watchlist.

**Options Considered**:
- [system-architect] +/- 0.15 adjustment for northbound flow
- [data-architect] Threshold-based: high threshold = 0.3 boost, low threshold = 0.1 boost
- [product-manager] Inflow magnitude normalized to 0.0-1.0 scale

**Chosen Approach**: Threshold-based approach from data-architect, with configurable thresholds via ScoringConfig. This provides more granularity than a fixed +/- 0.15.

```python
if flow_data.net_buy_amount > config.northbound_threshold_high:
    northbound_boost = config.northbound_boost_high  # default 0.3
elif flow_data.net_buy_amount > config.northbound_threshold_low:
    northbound_boost = config.northbound_boost_low   # default 0.1
else:
    northbound_boost = 0.0
```

**Trade-offs**: Threshold-based approach is more nuanced vs. fixed adjustment is simpler. The threshold approach is preferred because northbound flow magnitude varies significantly.

**Source**: data-architect (thresholds), system-architect (adjustment range), product-manager (normalization)

### D-025-4: Index Membership as Moderate Boost

**Decision**: Index constituents (e.g., CSI 300, CSI 500) receive a moderate boost (+0.10) because they have higher institutional attention and are more liquid.

**Context**: The system-architect proposes +0.10 boost. The data-architect proposes a configurable filter. The product-manager supports index membership as a filter criterion.

**Chosen Approach**: Dual use: (1) scoring boost (+0.10) for index constituents, (2) optional filter via `filter_non_constituent` config flag. The boost is applied in the market scoring function; the filter is applied in the ranking stage (F-026).

**Trade-offs**: Index membership as both boost and filter vs. simpler single-use approach. The dual use provides more flexibility without significant complexity.

**Source**: system-architect (boost), data-architect (filter), product-manager (data model placeholder)

### D-025-5: Neutral Default on Missing Data

**Decision**: When market data is unavailable, the function returns 0.5 (neutral). This ensures missing market data does not penalize or artificially boost entries.

**Context**: The system-architect and data-architect agree on neutral default. The product-manager requires graceful degradation.

**Options Considered**:
- [system-architect] Return 0.5 (neutral) for missing market data
- [data-architect] Market Semantics integration MUST be optional
- [product-manager] Missing P1-1 data = no semantics enrichment, not failure

**Chosen Approach**: Return 0.5 (neutral) when market data is unavailable. This is consistent with the F-022 graceful degradation strategy. The market component contributes neither boost nor penalty.

**Trade-offs**: Neutral default prevents misleading scores vs. potentially hiding data availability issues. The warning log mitigates the hiding concern.

**Source**: system-architect, data-architect, product-manager (consensus)

## 3. Interface Contract

### MarketSemanticsData Transfer Object

```python
@dataclass(frozen=True)
class MarketSemanticsData:
    """Market-level context for scoring."""
    is_trading_day: bool
    suspended_tickers: set[str]
    northbound_flow: Optional[dict[str, float]]  # ticker -> net flow amount
    index_constituents: Optional[set[str]]         # set of constituent tickers
```

### Scoring Function

```python
def score_market_context(
    entry: WatchlistEntry,
    context: ScoringContext,
) -> tuple[float, str]:
    """Score market context adjustments."""
```

### Data Flow

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

### Integration with P1-1

```python
# Dependency Injection — P1-1 services called at generation time
trading_calendar: TradingCalendar  # from P1-1
northbound_flow: NorthboundFlow    # from P1-1
index_constituent: IndexConstituent # from P1-1
```

## 4. Constraints & Risks

| Constraint | Type | Mitigation |
|------------|------|------------|
| TradingCalendar as hard gate | MUST | Non-trading days produce empty watchlists |
| Suspension handling | MUST | Suspended stocks receive market_score = 0.0 (retained, not removed) |
| Market Semantics integration optional | MUST | Missing P1-1 data = degraded scoring, not failure |
| NorthboundFlow as soft signal | SHOULD | Threshold-based boost, configurable |
| IndexConstituent as scope filter | SHOULD | Data model supports filtering; UI is post-MVP |
| Graceful degradation | MUST | All P1-1 calls wrapped in try/except |

| Risk | Severity | Mitigation |
|------|----------|------------|
| P1-1 services unavailable at generation time | MEDIUM | Wrap all P1-1 calls in try/except, return neutral defaults |
| NorthboundFlow data may lag by 1 day (T+1) | LOW | Use most recent available data |
| Index constituent list outdated | LOW | Use cached list, refresh daily |
| Market data source unavailable | MEDIUM | Return neutral score 0.5, log warning |

## 5. Acceptance Criteria

- [ ] TradingCalendar gate: non-trading days produce empty watchlist
- [ ] Suspended stocks receive market_score = 0.0
- [ ] NorthboundFlow: high inflow adds configurable boost (default 0.3)
- [ ] NorthboundFlow: low inflow adds configurable boost (default 0.1)
- [ ] NorthboundFlow: outflow or no data adds 0.0
- [ ] IndexConstituent: index members receive +0.10 boost
- [ ] IndexConstituent: optional filter via filter_non_constituent config
- [ ] Missing market data returns neutral 0.5
- [ ] All P1-1 calls wrapped in try/except for graceful degradation
- [ ] MarketSemanticsData is a frozen dataclass

## 6. Detailed Analysis References

- @../system-architect/analysis-F-025-market-semantics-validation.md — Trading day gate, suspension filter, northbound flow, index membership
- @../data-architect/analysis-F-025-market-semantics-validation.md — Data dependencies, FlowData structure, integration architecture
- @../product-manager/analysis-F-025-market-semantics-validation.md — User stories, TradingCalendar gating, NorthboundFlow signal
- @../guidance-specification.md#feature-decomposition — F-025 definition and related roles

## 7. Cross-Feature Dependencies

- **Depends on**: P1-1 Market Semantics (TradingCalendar, NorthboundFlow, IndexConstituent)
- **Required by**: F-022 (market component of scoring pipeline), F-026 (IndexConstituent filter)
- **Shared patterns**: Graceful degradation pattern, frozen dataclass for transfer objects
- **Integration points**:
  - F-022: `score_market_context()` is stage 4 in the scoring pipeline
  - F-023: TradingCalendar validation ensures event_date is a valid trading day
  - F-026: IndexConstituent enables index-based filtering
  - F-027: Market parameters configurable via YAML (deferred to iteration 2)
