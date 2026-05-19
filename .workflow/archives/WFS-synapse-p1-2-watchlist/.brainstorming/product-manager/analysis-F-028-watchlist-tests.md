# Product Manager Analysis: F-028 Watchlist Tests

## Feature Overview

F-028 extends test_projection.py with comprehensive tests for scoring, ranking, and filtering. This is a High-priority feature because scoring correctness directly impacts user trust. A wrong priority_score is worse than no watchlist -- it actively misleads the user.

## User Stories

### US-F028-01: Scoring Correctness
**As a** developer, **I want** golden file regression tests for the scoring engine **so that** scoring drift is detected before reaching users.

**Acceptance Criteria**:
- Golden file tests exist for scoring engine with known inputs and expected outputs
- priority_score values match expected outputs within 0.01 tolerance
- Reason strings match expected patterns (not exact text, but structure)
- Tests run automatically on every commit

### US-F028-02: Ranking Correctness
**As a** developer, **I want** tests that verify ranking order **so that** the sort order is always correct.

**Acceptance Criteria**:
- Tests verify that entries are sorted by priority_score descending
- Tests verify tiebreaker behavior (same score = most recent event first)
- Tests verify top-N truncation
- Tests verify at-least-one guarantee

### US-F028-03: Filtering Correctness
**As a** developer, **I want** tests that verify filtering rules **so that** only valid entries appear in the watchlist.

**Acceptance Criteria**:
- Tests verify threshold filtering (entries below threshold excluded)
- Tests verify category filtering (inclusion and exclusion)
- Tests verify filter composition (AND logic)
- Tests verify graceful degradation with missing data

### US-F028-04: Integration Correctness
**As a** developer, **I want** end-to-end tests that verify the full pipeline **so that** schema, scoring, ranking, and filtering work together.

**Acceptance Criteria**:
- End-to-end test produces a complete watchlist from mock inputs
- Output conforms to WatchlistEntry schema
- All fields are populated correctly (priority_score in range, reason non-empty)
- Test uses mock data for all upstream dependencies

## User Journey Mapping

This feature is developer-facing, not user-facing. The user journey is indirect: reliable tests produce reliable software, which produces trustworthy watchlists.

**Current State**: No watchlist-specific tests exist. Scoring, ranking, and filtering are untested.

**Desired State**: Every scoring path, ranking order, and filter rule has automated test coverage. Regressions are caught before reaching users.

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Core test coverage | >= 80% for scoring, ranking, filtering code | Coverage tool |
| Golden file tests | >= 5 scoring scenarios with expected outputs | Test file count |
| Integration test | >= 1 end-to-end pipeline test | Test file count |
| Regression detection | 100% -- any scoring change breaks golden file test | Manual verification |

## Priority Assessment

**MoSCoW**: Must

**Rationale**: Test coverage is a release gate. Shipping scoring logic without tests is irresponsible -- scoring bugs directly damage user trust. The effort is medium (writing tests, creating golden files), but the risk mitigation is critical.

## Dependencies

- **Upstream**: F-021 (schema), F-022 (scoring engine), F-023 (event filtering), F-024 (portfolio scoring), F-026 (ranking/filtering)
- **Downstream**: All features rely on tests for quality assurance
- **Cross-role**: system-architect defines test infrastructure; product-manager defines golden file expected outputs

## Constraints & Risks

| Constraint | Type | Mitigation |
|------------|------|------------|
| Test coverage >= 80% | MUST | Coverage tool integrated into CI pipeline |
| Golden file tests MUST catch scoring drift | MUST | Any change to scoring algorithm must update golden files |
| Tests MUST be deterministic | MUST | No random data, no time-dependent assertions (use fixed timestamps) |
| Mock data MUST cover edge cases | SHOULD | Empty signals, missing positions, non-trading-day events |

## Product Considerations

F-028 is the quality gate for the entire P1-2 release. The product-manager perspective is: "we do not ship scoring logic that we cannot test." This is non-negotiable.

Golden file tests serve a dual purpose: (1) they catch regressions, and (2) they document expected behavior. When a new developer reads the golden files, they understand what the scoring engine is supposed to do. This is living documentation.

The test suite SHOULD include edge cases that represent real-world scenarios: a day with no events, a portfolio with no positions, a stock with conflicting signals, and a non-trading day. These edge cases are where bugs hide.
