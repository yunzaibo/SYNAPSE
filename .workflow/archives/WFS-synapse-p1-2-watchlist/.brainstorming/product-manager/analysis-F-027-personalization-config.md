# Product Manager Analysis: F-027 Personalization Configuration

## Feature Overview

F-027 allows users to customize scoring weights and filtering rules via YAML configuration. This feature is designated as Could-priority (post-MVP) because premature personalization risks configuration paralysis. The default configuration from F-022/F-023/F-024/F-026 MUST be validated with real user data before exposing customization.

## User Stories

### US-F027-01: Weight Customization
**As a** quantitative researcher, **I want** to adjust scoring weights for Signal, Event, and Position dimensions **so that** the watchlist reflects my investment priorities.

**Acceptance Criteria**:
- Weights are configurable via YAML file (signal_weight, event_weight, portfolio_weight)
- Weights MUST sum to 1.0 (or be auto-normalized)
- Invalid configurations produce a clear error message, not a crash
- Changing weights produces different watchlist outputs without code changes

### US-F027-02: Filter Rule Customization
**As an** investor, **I want** to customize filtering rules (threshold, top-N, category inclusion/exclusion) **so that** the watchlist matches my review workflow.

**Acceptance Criteria**:
- Threshold, top-N, and category filters are configurable via YAML
- Defaults match F-026 specifications (threshold=0.2, top-N=20, no category exclusion)
- Configuration changes take effect on next daily generation
- Configuration file is validated on load; invalid values rejected with clear messages

## User Journey Mapping

**Current State**: Default scoring and filtering are fixed. Users get the same watchlist configuration as everyone else.

**Desired State**: Users can tune weights and filters to match their investment style. A momentum investor weights events higher; a value investor weights fundamentals higher.

**Pain Points Addressed**:
- "The scoring doesn't match my priorities" -- solved by weight customization
- "I want more/fewer items on my list" -- solved by top-N customization
- "I want to exclude certain categories" -- solved by filter rule customization

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Configuration validity | 100% -- invalid configs rejected with clear errors | Unit tests for all invalid cases |
| Default configuration sufficiency | >= 70% of users never change defaults | Config file diff tracking |
| Weight normalization | Weights always sum to 1.0 after normalization | Unit test |

## Priority Assessment

**MoSCoW**: Could

**Rationale**: Personalization is valuable but premature for MVP. The default configuration should be validated against real user behavior before exposing customization. Shipping personalization too early risks: (a) users changing weights without understanding the impact, (b) support burden from misconfigurations, (c) difficulty analyzing system behavior when every user has different weights.

**Recommended timing**: Ship in iteration 2, after collecting at least 30 days of user feedback on default watchlist quality.

## Dependencies

- **Upstream**: F-022 (scoring weights), F-026 (filter rules)
- **Downstream**: F-028 (tests validate configuration loading and normalization)
- **Cross-role**: product-manager defines default values and validation rules; data-architect defines YAML schema; system-architect implements config loading

## Constraints & Risks

| Constraint | Type | Mitigation |
|------------|------|------------|
| Default configuration MUST work without user intervention | MUST | Defaults are the same as F-022/F-026 defaults |
| Invalid configuration MUST NOT crash the system | MUST | Config validation on load; fallback to defaults on error |
| Configuration changes MUST be idempotent | MUST | Same config file always produces same output |
| Weight normalization MUST be transparent | SHOULD | Log normalized weights when auto-normalization occurs |

## Product Considerations

The decision to defer F-027 is strategic, not technical. The implementation is straightforward (YAML parsing, weight normalization, validation). The risk is product: premature personalization can degrade system quality if users set extreme weights (e.g., 100% Signal, 0% Event) that produce poor watchlists.

The recommended approach is: ship F-022-F-026 with well-calibrated defaults, collect user feedback for 30 days, then ship F-027 with the accumulated knowledge of what default values work best. This allows the product team to learn from real usage before exposing knobs.

When F-027 does ship, the configuration file SHOULD include inline documentation (YAML comments) explaining each parameter, its valid range, and its impact on scoring. This reduces the support burden and helps users make informed decisions.
