# Product Manager Analysis: F-023 Event-Driven Filtering

## Feature Overview

F-023 implements time-decay scoring based on Event lifecycle. Events that occurred recently receive higher scores; events that occurred days or weeks ago decay toward zero. This ensures the watchlist reflects temporal relevance -- a breaking news event from today matters more than a stale announcement from last week.

## User Stories

### US-F023-01: Temporal Relevance
**As an** investor, **I want** recent events to score higher than old events **so that** my watchlist focuses on what's happening now.

**Acceptance Criteria**:
- Events within 24 hours receive decay factor >= 0.8
- Events between 24-72 hours receive decay factor 0.3-0.8
- Events older than 7 days receive decay factor <= 0.1
- Decay factor is multiplied into the priority_score calculation

### US-F023-02: Event Lifecycle Awareness
**As an** investor, **I want** events that are actively developing to maintain higher scores than events that have resolved **so that** I focus on open issues.

**Acceptance Criteria**:
- Event lifecycle status (active, developing, resolved, stale) is a scoring input
- Resolved events receive an additional decay penalty
- Developing events may receive a boost above the time-decay baseline
- The decay model parameters are configurable via YAML

### US-F023-03: Non-Trading Day Handling
**As an** investor, **I want** events on non-trading days to be excluded or heavily discounted **so that** my watchlist only contains actionable items.

**Acceptance Criteria**:
- Events falling on non-trading days per TradingCalendar receive decay factor 0.0
- Weekend and holiday events do not appear in the watchlist
- The TradingCalendar integration is a dependency on F-025

## User Journey Mapping

**Current State**: User sees all events equally, regardless of when they occurred. Old, stale events clutter the list.

**Desired State**: User sees a temporally weighted list. Today's earnings announcement scores higher than last week's analyst upgrade.

**Pain Points Addressed**:
- "My list is full of old news I already acted on" -- solved by time decay
- "I can't tell which events are still developing" -- solved by lifecycle awareness
- "Non-trading-day events are noise" -- solved by TradingCalendar gating

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Decay curve correctness | 24h events >= 0.8, 7d events <= 0.1 | Unit tests with time fixtures |
| Lifecycle integration | Active/developing events score higher than resolved | Unit tests by lifecycle status |
| No stale events in top-20 | 0 events older than 7 days in top-20 | Regression test with historical data |

## Priority Assessment

**MoSCoW**: Must

**Rationale**: Temporal relevance is what separates a useful daily watchlist from a static data dump. Without decay, the list becomes increasingly stale over time. The effort is medium (decay function implementation, lifecycle status integration), but the impact on user experience is high.

## Dependencies

- **Upstream**: Event data (P3 events with lifecycle status), TradingCalendar (F-025 / P1-1)
- **Downstream**: F-022 (decay factor feeds into priority_score), F-026 (filtered results feed into ranking)
- **Cross-role**: system-architect defines the decay function; product-manager defines the decay parameters and lifecycle mappings

## Constraints & Risks

| Constraint | Type | Mitigation |
|------------|------|------------|
| Decay function MUST be deterministic | MUST | Pure function of event timestamp and current time |
| Decay parameters MUST be configurable | SHOULD | YAML configuration for half-life and boundary values |
| Non-trading-day exclusion | MUST | Gated by TradingCalendar from P1-1 |
| Lifecycle status mapping | MUST | Explicit mapping from Event lifecycle enum to decay modifier |

## Product Considerations

The decay model is the product's opinion on "how fast does relevance fade?" This is domain-specific: in volatile markets, a 24-hour half-life may be appropriate; in stable markets, 72 hours may be better. The default half-life SHOULD be 48 hours, reflecting a balance between freshness and persistence.

The lifecycle awareness adds a second dimension beyond pure time decay. An event that is "developing" (e.g., ongoing M&A negotiation) should score higher than a "resolved" event of the same age. This creates a natural hierarchy: recent + developing = highest; old + resolved = lowest.

Non-trading-day handling is a hard constraint: if TradingCalendar says today is not a trading day, no events should appear. This prevents the confusing experience of seeing a watchlist on Saturday that references market events.
