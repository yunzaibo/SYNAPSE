# Cross-Cutting Product Decisions: P1-2 Daily Watchlist Generator

## Product Strategy Alignment

### Vision Statement

P1-2 Daily Watchlist Generator transforms raw market data and portfolio state into a prioritized, actionable morning research list. The product vision is: "Every morning, SYNAPSE tells you exactly what to pay attention to, and why."

### Strategic Positioning

Within the SYNAPSE ecosystem, P1-2 occupies the **output layer** -- it is the primary user-facing deliverable that converts backend intelligence (P1 Market Semantics, P5 DataSource, Signal/Event/Position data) into a consumable format. The watchlist is the "last mile" of the data pipeline and the first touchpoint of the user's daily workflow.

**Positioning within dependency chain**:
- P1-1 Market Semantics provides market context (trading calendar, northbound flow, index membership)
- P5 DataSource provides raw market data (prices, fundamentals)
- P3 Signal/Event/Position provides analytical signals
- **P1-2 synthesizes all upstream inputs into a single prioritized output**

This positioning means P1-2 has no value without its dependencies, but also that upstream improvements automatically flow through to improved watchlist quality.

## Priority Matrix (MoSCoW)

| Feature | MoSCoW | Effort | Impact | Rationale |
|---------|--------|--------|--------|-----------|
| F-021 schema-extension | Must | Low | High | Foundation for all scoring; no watchlist scoring without schema |
| F-022 signal-scoring-engine | Must | High | High | Core value proposition; the entire point of the feature |
| F-023 event-driven-filtering | Must | Medium | High | Temporal relevance is what separates "data dump" from "intelligence" |
| F-024 portfolio-aware-scoring | Must | Medium | High | Portfolio context is SYNAPSE's key differentiator vs. generic screeners |
| F-025 market-semantics-validation | Should | Medium | Medium | Prevents noise from non-trading-day or out-of-scope events |
| F-026 ranking-and-filtering | Should | Low | High | Ranking is trivial; filtering rules are the real value |
| F-027 personalization-config | Could | Medium | Low | Deferred to iteration 2; default weights from iteration 1 data |
| F-028 watchlist-tests | Must | Medium | High | Quality gate; scoring bugs directly damage user trust |

## Release Criteria (Go/No-Go)

### MVP Release (F-021 through F-026 + F-028)

The following conditions MUST ALL be met before MVP release:

| Criterion | Condition | Type |
|-----------|-----------|------|
| Schema compatibility | WatchlistEntry backward-compatible with existing consumers | MUST |
| Scoring correctness | priority_score values match expected golden file outputs within 0.01 tolerance | MUST |
| Reason transparency | Every watchlist entry contains a non-empty, human-readable reason string | MUST |
| Daily generation | Watchlist regenerates completely within 5 minutes on reference hardware | MUST |
| Graceful degradation | Missing data source returns partial watchlist with degraded scores, NOT failure | MUST |
| Test coverage | Core scoring logic test coverage >= 80% | MUST |
| Non-trading day handling | No watchlist generated on non-trading days per TradingCalendar | MUST |
| Upstream dependency | P1-1 and P5 modules pass their own release gates | MUST |

### Post-MVP Criteria (F-027)

| Criterion | Condition | Type |
|-----------|-----------|------|
| Default weight validation | Default scoring weights produce watchlists rated "useful" by >= 70% of beta users | SHOULD |
| Configuration UX | YAML config file documented with examples for all weight parameters | SHOULD |
| Backward compatibility | Changing weights does not break existing watchlist consumers | MUST |

## Success Metrics

### Primary KPIs

| Metric | Target | Measurement | Phase |
|--------|--------|-------------|-------|
| Watchlist relevance score | >= 4.0/5.0 user rating on "top 5 items useful" | User feedback survey | Post-launch |
| Scoring latency | < 5 seconds for full daily regeneration | System benchmark | MVP |
| Coverage rate | >= 90% of portfolio positions appear in watchlist when scoring > 0.3 | Automated check | MVP |
| Reason comprehension | >= 80% of reason strings are non-technical and actionable | User testing | MVP |

### Secondary KPIs

| Metric | Target | Measurement | Phase |
|--------|--------|-------------|-------|
| Daily usage rate | >= 60% of weekdays with watchlist access | Access logs | Post-launch |
| Manual override rate | < 10% of watchlist entries manually dismissed | User behavior tracking | Post-launch |
| Configuration adoption | >= 30% of users customize default weights | Config file diff | Post-MVP |
| False positive rate | < 5% of top-10 entries rated "irrelevant" | User feedback | Post-launch |

## User Stories (Cross-Feature)

### Epic: Daily Morning Research Ritual

**US-001**: As an investor, I want to receive a prioritized watchlist every morning so that I know which stocks to research first.
- Acceptance Criteria: Watchlist contains >= 1 and <= 50 entries, sorted by priority_score descending, generated before 9:00 AM trading day.

**US-002**: As an investor, I want to understand WHY each stock appears on my watchlist so that I can make informed decisions.
- Acceptance Criteria: Every entry includes a reason string between 10 and 200 characters, written in plain language, referencing at least one data source (signal, event, position, or market semantics).

**US-003**: As a portfolio manager, I want my existing holdings to be weighted differently than new opportunities so that I can focus on thesis management.
- Acceptance Criteria: Portfolio-aware scoring adjusts priority_score by thesis_status (confirmed > monitoring > speculative) and attention_state (high-attention positions score higher).

**US-004**: As a quantitative researcher, I want the scoring engine to be transparent and reproducible so that I can audit and improve it.
- Acceptance Criteria: Scoring produces deterministic outputs for identical inputs; score components are individually traceable in the reason string.

**US-005**: As a risk-conscious investor, I want non-trading-day events excluded from my watchlist so that I only see actionable items.
- Acceptance Criteria: Events falling outside TradingCalendar trading days receive a decay factor of 0.0 and do not appear in the watchlist.

## Shared Patterns Across Features

### Pattern: Graceful Degradation

F-022, F-023, F-024, and F-025 all depend on upstream data sources. The product requirement is that partial data MUST produce partial results, not failures. This pattern is shared across features and SHOULD be implemented as a common middleware or wrapper.

### Pattern: Reason Generation

F-022, F-023, F-024, and F-025 all contribute to the `reason` field. The reason MUST be composable -- combining contributions from multiple scoring dimensions into a coherent, non-redundant explanation. This pattern SHOULD be centralized in a reason-composition service.

### Pattern: Default vs. Custom Behavior

F-026 (filtering) and F-027 (personalization) share the pattern of "sensible defaults with optional override." The default behavior MUST work for all users without configuration. Overrides MAY be provided but MUST NOT break the default path.

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Scoring opacity erodes user trust | High | High | F-022 reason field is mandatory; golden file tests catch scoring drift |
| Daily regeneration latency exceeds 5 min | Medium | Medium | Profile early; consider caching intermediate scoring results |
| Default weights produce biased watchlists | Medium | High | Validate against historical data; monitor user feedback post-launch |
| Upstream dependency failures cascade | Low | High | Graceful degradation pattern; circuit breaker on data source calls |
