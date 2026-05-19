# Product Manager Analysis: F-025 Market Semantics Validation

## Feature Overview

F-025 integrates P1-1 Market Semantics components (TradingCalendar, NorthboundFlow, IndexConstituent) into the watchlist scoring pipeline. This integration serves three purposes: gating (only trading-day events), boosting (northbound capital flow signals), and scoping (index membership filtering).

## User Stories

### US-F025-01: Trading Day Gating
**As an** investor, **I want** my watchlist to only include events from actual trading days **so that** I don't see noise from weekends and holidays.

**Acceptance Criteria**:
- Non-trading-day events receive a decay factor of 0.0
- TradingCalendar integration uses P1-1's TradingCalendar module
- Graceful degradation: if TradingCalendar is unavailable, all days are treated as trading days

### US-F025-02: Northbound Flow Signal
**As an** investor, **I want** stocks with significant northbound capital inflows to score higher **so that** I follow institutional money flows.

**Acceptance Criteria**:
- NorthboundFlow data feeds into the scoring engine as a signal dimension
- Inflow magnitude is normalized to 0.0-1.0 scale
- Outflow signals may reduce priority_score
- NorthboundFlow data unavailability produces no adjustment, not failure

### US-F025-03: Index Membership Context
**As an** investor, **I want** the watchlist to be aware of index membership **so that** I can filter or prioritize by index (e.g., CSI 300, CSI 500).

**Acceptance Criteria**:
- IndexConstituent data is available as a filter criterion
- User can filter watchlist by index membership (post-MVP, but data model MUST support it)
- Index membership is included in the reason string when relevant

## User Journey Mapping

**Current State**: User sees events without market context. A Saturday news event appears alongside Friday's trading signals.

**Desired State**: Market Semantics layer filters and enriches the watchlist. Only trading-day events appear; northbound flow provides institutional sentiment context; index membership enables category filtering.

**Pain Points Addressed**:
- "Non-trading-day events are confusing" -- solved by TradingCalendar gating
- "I want to know what foreign investors are doing" -- solved by NorthboundFlow integration
- "I want to filter by index" -- solved by IndexConstituent (data model ready for F-026)

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Trading day accuracy | 100% -- no non-trading-day events in watchlist | Automated check against TradingCalendar |
| NorthboundFlow signal quality | >= 60% of high-inflow stocks appear in top-20 | Historical backtesting |
| Graceful degradation | Watchlist generates correctly when Market Semantics unavailable | Chaos test |

## Priority Assessment

**MoSCoW**: Should

**Rationale**: Market Semantics validation improves watchlist quality but is not strictly required for the core value proposition. The scoring engine (F-022) can function without it. However, TradingCalendar gating is near-essential for correctness. The effort is medium (integration with P1-1 modules).

## Dependencies

- **Upstream**: P1-1 Market Semantics (TradingCalendar, NorthboundFlow, IndexConstituent)
- **Downstream**: F-023 (TradingCalendar feeds into non-trading-day decay), F-022 (NorthboundFlow feeds into scoring), F-026 (IndexConstituent enables filtering)
- **Cross-role**: system-architect defines integration interface; data-architect defines data format; product-manager defines signal weight and filter semantics

## Constraints & Risks

| Constraint | Type | Mitigation |
|------------|------|------------|
| P1-1 dependency | MUST | Graceful degradation: missing P1-1 data = no semantics enrichment, not failure |
| TradingCalendar as hard gate | MUST | Events on non-trading days MUST NOT appear in watchlist |
| NorthboundFlow as soft signal | SHOULD | Missing data = no adjustment; present data = normalized boost |
| IndexConstituent as filter | SHOULD | Data model supports filtering; actual filter UI is post-MVP |

## Product Considerations

TradingCalendar is the most critical Market Semantics component. A watchlist that includes Saturday events is immediately perceived as broken. The product requirement is absolute: no events on non-trading days.

NorthboundFlow is a high-value signal for A-share investors. Foreign institutional capital flow is widely regarded as a leading indicator. Including this as a scoring dimension adds significant value with minimal effort (the data already exists in P1-1).

IndexConstituent is currently a data model placeholder. The actual filtering UI is out of scope for P1-2, but the schema MUST support it so that F-026 can implement index-based filtering in a future iteration.
