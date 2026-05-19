# Product Manager Analysis: F-022 Signal Scoring Engine

## Feature Overview

F-022 implements the core scoring engine that calculates priority_score for each potential watchlist entry. The engine fuses signals from multiple dimensions (Signal, Event, Position) into a single 0.0-1.0 score and produces a human-readable reason string explaining the score composition.

This is the highest-value feature in P1-2. The quality of the scoring engine directly determines whether users trust and act on watchlist recommendations.

## User Stories

### US-F022-01: Multi-Signal Fusion
**As an** investor, **I want** the scoring engine to combine signals from multiple data sources **so that** my watchlist reflects the full picture, not just one dimension.

**Acceptance Criteria**:
- Engine accepts Signal, Event, and Position data as inputs
- priority_score is a weighted combination of input dimensions
- Score components are individually traceable in the reason string
- Score is deterministic: identical inputs produce identical outputs

### US-F022-02: Score Transparency
**As an** investor, **I want** the reason string to explain which signals contributed most to a stock's score **so that** I can understand and trust the recommendation.

**Acceptance Criteria**:
- reason string references at least one specific signal (e.g., "Strong northbound inflow +2.1B, thesis confirmed")
- reason string is between 10 and 200 characters
- reason uses plain language, not technical jargon
- Score breakdown is available in structured form (not just free text)

### US-F022-03: Configurable Weights
**As a** quantitative researcher, **I want** scoring weights to be adjustable via configuration **so that** I can tune the system to my investment style.

**Acceptance Criteria**:
- Default weights are provided and documented
- Weights can be overridden via YAML configuration file
- Invalid weight configurations are rejected with clear error messages
- Weight changes produce different scores without code changes

## User Journey Mapping

**Current State**: User manually scans news feeds, market data, and portfolio reports to identify what to research each morning. This takes 30-60 minutes.

**Desired State**: User opens the watchlist, sees 10-20 stocks scored and explained. Total research time drops to 5-10 minutes of scanning reasons and diving into the top 3-5.

**Pain Points Addressed**:
- "I spend too much time figuring out what's important today" -- solved by scoring
- "I miss important signals because I can't monitor everything" -- solved by multi-signal fusion
- "I don't trust automated recommendations without explanation" -- solved by reason transparency

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Score determinism | 100% -- identical inputs produce identical outputs | Golden file regression tests |
| Reason quality | >= 80% of reasons are non-technical and actionable | User testing with 5+ participants |
| Top-10 relevance | >= 70% of top-10 entries rated "useful" by user | Post-launch feedback survey |
| Scoring latency | < 3 seconds for full scoring pass | Performance benchmark |

## Priority Assessment

**MoSCoW**: Must

**Rationale**: This is the core value proposition of P1-2. Without the scoring engine, the watchlist is just a data dump. The effort is high (multi-source fusion, weight management, reason generation), but the impact is the entire feature's reason for existing.

## Dependencies

- **Upstream**: Signal data (P3 signals), Event data (P3 events), Position data (P3 positions), P1-1 Market Semantics (P1-25), P5 DataSource
- **Downstream**: F-026 (ranking uses priority_score), F-027 (personalization overrides weights), F-028 (tests validate scoring)
- **Cross-role**: system-architect defines the fusion algorithm; product-manager defines the weight defaults and reason format

## Constraints & Risks

| Constraint | Type | Mitigation |
|------------|------|------------|
| Deterministic scoring | MUST | Golden file tests; no randomness in scoring algorithm |
| Graceful degradation on missing data | MUST | Missing Signal/Event/Position data produces degraded score, not failure |
| Reason string format | MUST | Structured reason with signal references; validated by tests |
| Weight validation | MUST | Weights MUST sum to 1.0 or be normalized; invalid configs rejected |
| No ML models | MUST NOT | Rule-based scoring only; no trained models or embeddings |

## Product Considerations

The scoring engine is where "data" becomes "intelligence." The product value is not in the score number itself, but in the reason string that explains it. A user should be able to read the reason and think "yes, that makes sense" or "hmm, I disagree with this assessment" -- both reactions are valuable because they build trust through transparency.

Default scoring weights SHOULD be derived from domain expertise and validated against historical data. The weights represent the product's opinion on what matters most. F-027 will later allow users to override these defaults, but the defaults MUST be good enough that most users never need to change them.

The score should follow a roughly normal distribution centered around 0.4-0.6, with tails at 0.0-0.2 (low interest) and 0.8-1.0 (urgent attention). If the engine produces scores clustered at 0.5, it is not discriminating. The distribution shape is a key quality indicator.
