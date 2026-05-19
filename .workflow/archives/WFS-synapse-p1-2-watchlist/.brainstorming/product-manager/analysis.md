# Product Manager Analysis: P1-2 Daily Watchlist Generator

## Role Perspective Overview

The product-manager perspective evaluates P1-2 Daily Watchlist Generator through the lens of user value delivery, business impact, and strategic positioning within the SYNAPSE ecosystem. This analysis focuses on translating technical capabilities into user-facing outcomes, defining measurable success criteria, and establishing a prioritized delivery roadmap that maximizes early user value while maintaining architectural integrity.

P1-2 represents a critical user-facing feature: the daily watchlist is the primary touchpoint where users engage with SYNAPSE's intelligence layer. The quality of prioritized, context-aware recommendations directly determines user retention and perceived system value. This analysis frames every feature through the question: "How does this make the user's morning research ritual faster, smarter, or more relevant?"

## Feature Point Index

| Feature | Analysis File | Key Decisions |
|---------|--------------|---------------|
| F-021 watchlist-schema-extension | [analysis-F-021-watchlist-schema-extension.md](./analysis-F-021-watchlist-schema-extension.md) | Schema backward compatibility is a MUST; priority_score range 0.0-1.0 is user-facing contract |
| F-022 signal-scoring-engine | [analysis-F-022-signal-scoring-engine.md](./analysis-F-022-signal-scoring-engine.md) | Scoring transparency via reason field; multi-signal fusion with configurable weights |
| F-023 event-driven-filtering | [analysis-F-023-event-driven-filtering.md](./analysis-F-023-event-driven-filtering.md) | Decay model must balance freshness vs. signal persistence; user-facing time horizon |
| F-024 portfolio-aware-scoring | [analysis-F-024-portfolio-aware-scoring.md](./analysis-F-024-portfolio-aware-scoring.md) | thesis_status drives investment thesis alignment; attention_state enables focus steering |
| F-025 market-semantics-validation | [analysis-F-025-market-semantics-validation.md](./analysis-F-025-market-semantics-validation.md) | TradingCalendar as gating; NorthboundFlow as boost signal; IndexConstituent as scope |
| F-026 ranking-and-filtering | [analysis-F-026-ranking-and-filtering.md](./analysis-F-026-ranking-and-filtering.md) | Ranking MUST surface top-N; filtering MUST support category and threshold rules |
| F-027 personalization-config | [analysis-F-027-personalization-config.md](./analysis-F-027-personalization-config.md) | Personalization is Could-priority; sensible defaults MUST cover 80% use cases |
| F-028 watchlist-tests | [analysis-F-028-watchlist-tests.md](./analysis-F-028-watchlist-tests.md) | Test coverage > 80% is a release gate; golden file testing for scoring consistency |

## Cross-Cutting Concerns

See [analysis-cross-cutting.md](./analysis-cross-cutting.md) for product strategy alignment, prioritization matrix, release criteria, and success metrics that span all features.

## Key Recommendations

1. **Ship scoring transparency from day one**: The `reason` field is not a nice-to-have -- it is the primary trust-building mechanism. Users who understand WHY a stock appears on their watchlist are more likely to act on recommendations and continue using the system. Every scoring feature MUST produce human-readable reasons.

2. **MVP scope is features F-021 through F-026 only**: F-027 (personalization-config) is deferred to a follow-up iteration. The default scoring weights derived from F-022/F-023/F-024 MUST be validated with real user data before exposing configuration. Premature personalization risks configuration paralysis.

3. **Daily regeneration is a product constraint, not just technical**: ADR-009's Daily Full Regeneration aligns with user behavior -- investors review watchlists once per market open. This constraint SHOULD be communicated in product documentation so users understand the system's refresh cadence.

4. **Test coverage gate is non-negotiable**: F-028 is High priority because scoring correctness directly impacts user trust. A wrong priority_score is worse than no watchlist. The testing feature MUST include golden file regression tests that catch scoring drift.

## User Intent Alignment

The original user intent specifies: "基于 P1 Market Semantics 和 P5 DataSource 的每日关注列表生成器" with scope covering "信号评分整合、事件驱动过滤、持仓状态感知、个性化推荐". All eight features directly serve this intent. The product-manager analysis confirms that F-021 through F-026 constitute the MVP scope, while F-027 (personalization) and F-028 (testing) serve as enablers -- the former for future iterations, the latter as a quality gate for the current release.
