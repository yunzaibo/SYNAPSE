# Product Manager Analysis: F-026 Ranking and Filtering

## Feature Overview

F-026 implements the final ranking and filtering layer that takes scored watchlist entries and produces the user-facing output. Ranking sorts entries by priority_score descending. Filtering applies rules to include or exclude entries based on category, score threshold, and other criteria.

## User Stories

### US-F026-01: Score-Based Ranking
**As an** investor, **I want** my watchlist sorted by priority_score from highest to lowest **so that** the most important items are at the top.

**Acceptance Criteria**:
- Watchlist entries are sorted by priority_score descending
- Entries with identical priority_score are sorted by event timestamp (most recent first)
- Top-N entries (default 20) are returned; N is configurable
- Ranking is deterministic for identical inputs

### US-F026-02: Category Filtering
**As an** investor, **I want** to filter my watchlist by category (signal type, event type, sector) **so that** I can focus on specific areas.

**Acceptance Criteria**:
- Filtering supports inclusion and exclusion by category
- Multiple filter criteria are AND-combined
- Filters can be applied via YAML configuration
- Default configuration includes no filters (all entries pass)

### US-F026-03: Score Threshold Filtering
**As an** investor, **I want** to set a minimum priority_score threshold **so that** low-relevance entries are automatically excluded.

**Acceptance Criteria**:
- Default threshold is 0.2 (entries below 0.2 are excluded)
- Threshold is configurable via YAML
- Threshold filtering is applied after scoring, before ranking
- At least 1 entry is always returned regardless of threshold

### US-F026-04: Top-N Control
**As an** investor, **I want** to control how many entries appear in my watchlist **so that** I get a manageable number of items to review.

**Acceptance Criteria**:
- Default top-N is 20
- Top-N is configurable via YAML (range: 1-100)
- Top-N is applied after all filtering
- If fewer entries pass filtering than top-N, all passing entries are returned

## User Journey Mapping

**Current State**: User receives a scored list but must manually sort and filter.

**Desired State**: User receives a pre-sorted, pre-filtered list that fits on one screen. The most important items are at the top; noise is filtered out.

**Pain Points Addressed**:
- "I have too many items to review" -- solved by top-N and threshold filtering
- "I want to focus on specific categories" -- solved by category filtering
- "The list order doesn't match my priorities" -- solved by score-based ranking

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Ranking determinism | 100% -- identical inputs produce identical order | Unit tests |
| Filtering correctness | 100% -- filtered results match filter criteria | Unit tests for each filter type |
| Top-N compliance | Watchlist length <= top-N setting | Automated check |
| At-least-one guarantee | Watchlist length >= 1 when any candidates exist | Unit test |

## Priority Assessment

**MoSCoW**: Should

**Rationale**: Ranking is trivially simple (sort by score). Filtering is where the real product value lies -- it transforms a raw scored list into a personalized, actionable output. The effort is low for ranking, medium for filtering.

## Dependencies

- **Upstream**: F-021 (schema with priority_score), F-022 (scoring engine), F-023 (event filtering), F-024 (portfolio adjustments), F-025 (market semantics)
- **Downstream**: F-027 (personalization overrides filter rules), F-028 (tests validate ranking and filtering)
- **Cross-role**: product-manager defines default filter rules; system-architect implements the filtering pipeline

## Constraints & Risks

| Constraint | Type | Mitigation |
|------------|------|------------|
| Ranking MUST be deterministic | MUST | Stable sort with deterministic tiebreaker |
| At-least-one guarantee | MUST | Even with high threshold, return 1 entry if any exist |
| Filter composition | MUST | Filters are AND-combined; no OR logic in MVP |
| Default configuration MUST work | MUST | Default config produces a reasonable watchlist without user customization |

## Product Considerations

Ranking is the simplest feature but has the highest user visibility. The sort order IS the product. If the top 3 entries are wrong, the user loses trust in the entire system. This reinforces the importance of F-022 scoring quality.

Filtering is the mechanism for scope control. Without filtering, the watchlist could contain 200+ entries -- too many to review. The default threshold of 0.2 is calibrated to produce 10-20 entries for a typical portfolio. This calibration SHOULD be validated against real data.

The at-least-one guarantee is a UX requirement, not a technical one. A user who opens an empty watchlist thinks the system is broken. Even if no entries exceed the threshold, the system SHOULD return the highest-scoring entry with a note that it falls below the threshold.
