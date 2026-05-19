# Feature Spec: F-027 - Personalization Configuration

**Priority**: Low (deferred to iteration 2)
**Contributing Roles**: system-architect, data-architect, product-manager
**Status**: Final (conflicts resolved, deferred to iteration 2)

## 1. Requirements Summary

- ScoringConfig MUST be a frozen dataclass loaded from YAML configuration
- Default configuration MUST work without user intervention
- Invalid configurations MUST NOT crash the system — warning + fallback to defaults
- Weight auto-normalization MUST be transparent (logged when applied)
- Configuration file MAY be absent — defaults MUST produce valid scoring behavior
- YAML schema MUST use flat structure (not nested)
- Weight validation: auto-normalize with warning, not ValueError
- Config is a first-class dependency passed as parameter, not loaded globally
- F-027 is deferred to iteration 2 per product-manager recommendation (EP-005)

## 2. Design Decisions [CORE SECTION]

### D-027-1: F-027 Deferred to Iteration 2

**Decision**: F-027 SHOULD be deferred to iteration 2. The default configuration from F-022/F-023/F-024/F-026 MUST be validated with real user data before exposing customization.

**Context**: The product-manager recommends deferring F-027 as Could-priority. Premature personalization risks configuration paralysis, support burden from misconfigurations, and difficulty analyzing system behavior when every user has different weights.

**Options Considered**:
- [product-manager] Could-priority, defer to iteration 2
- [system-architect] Analyzes as active feature
- [data-architect] Defines ScoringConfig as active feature

**Chosen Approach**: Defer F-027 to iteration 2. Ship F-022-F-026 with well-calibrated defaults, collect user feedback for 30 days, then ship F-027 with accumulated knowledge. (EP-005)

**Trade-offs**: Delayed personalization vs. validated defaults. The trade-off is favorable because shipping personalization too early risks degraded system quality.

**Source**: product-manager (recommended by cross-role analysis, EP-005)

### D-027-2: YAML-Only Configuration with Flat Structure

**Decision**: Configuration MUST be provided via YAML file with flat structure (not nested).

**Context**: The system-architect proposes nested YAML structure; the data-architect proposes flat structure. The existing `load_config()` pattern uses flat YAML.

**Options Considered**:
- [system-architect] Nested structure with scoring.weights.signal, scoring.event_decay.enabled, etc.
- [data-architect] Flat structure with signal_weight, event_weight, portfolio_weight, etc.

**Chosen Approach**: Adopt flat structure. Consistent with existing `load_config()` pattern and simpler to parse. (EP-003)

```yaml
# Flat YAML structure
signal_weight: 0.35
event_weight: 0.30
portfolio_weight: 0.20
market_weight: 0.15

default_decay_rate: 0.1
decay_rates:
  earnings: 0.15
  policy: 0.05

thesis_invalidated_boost: 0.5
thesis_weakened_boost: 0.35
thesis_active_boost: 0.15

northbound_threshold_high: 500000000
northbound_threshold_low: 100000000
filter_non_constituent: false

min_priority_score: 0.1
max_entries: 20
```

**Trade-offs**: Simpler parsing vs. less organized grouping. The flat structure is preferred for P1-2 because it aligns with existing patterns.

**Source**: data-architect (recommended by cross-role analysis, EP-003)

### D-027-3: Weight Validation — Warning + Fallback

**Decision**: Invalid weight configurations MUST trigger a warning and fall back to defaults, not raise ValueError.

**Context**: The system-architect proposes warning + fallback; the data-architect proposes raise ValueError. The product-manager requires that invalid configs MUST NOT crash the system.

**Options Considered**:
- [system-architect] Warning + fallback to defaults
- [data-architect] Raise ValueError
- [product-manager] Invalid configs must not crash

**Chosen Approach**: Warning + fallback. On config load, validate weight sum. If invalid, log warning and use defaults. This satisfies the product-manager's non-crash requirement. (EP-002 alignment)

```python
def load_scoring_config(path: Optional[Path] = None) -> ScoringConfig:
    if path is None or not path.exists():
        return ScoringConfig()  # defaults
    try:
        raw = load_config(path)
        return _parse_scoring_config(raw)
    except (ValueError, KeyError) as e:
        logger.warning(f"Invalid scoring config, using defaults: {e}")
        return ScoringConfig()
```

**Trade-offs**: Resilience vs. silent misconfiguration. The warning log mitigates the silent aspect. The alternative (ValueError) would crash the daily generation pipeline.

**Source**: system-architect (recommended by cross-role analysis, EP-002)

### D-027-4: Config as First-Class Dependency

**Decision**: `ScoringConfig` MUST be passed as a parameter to scoring functions, not loaded globally.

**Context**: The system-architect proposes config as first-class dependency. This enables unit testing with different configs, future multi-user support, and A/B testing.

**Options Considered**:
- [system-architect] Config passed as parameter to score_entries()
- [data-architect] Config loaded once at generation time

**Chosen Approach**: Config passed as parameter. The `generate_daily()` function accepts an optional `config: Optional[ScoringConfig]` parameter, defaulting to `ScoringConfig()` if not provided.

**Trade-offs**: Testability and flexibility vs. slightly more complex function signatures. The trade-off is favorable for maintainability.

**Source**: system-architect

### D-027-5: Non-Goals Compliance

**Decision**: The scoring FORMULA is fixed (weighted sum). Only WEIGHTS and PARAMETERS are configurable. No ML models.

**Context**: Per the guidance-specification non-goals: "自定义评分公式" (custom scoring formula) and "机器学习推荐" (ML recommendation) are out of scope.

**Options Considered**:
- [system-architect] Only weights configurable, formula fixed
- [product-manager] Non-goals: no custom formula, no ML

**Chosen Approach**: Configuration is purely rule-based. Users can adjust weights and parameters but cannot change the scoring formula itself.

**Trade-offs**: Simplicity and predictability vs. flexibility. The trade-off is favorable because a fixed formula ensures consistent behavior across users.

**Source**: system-architect, product-manager (consensus)

## 3. Interface Contract

### ScoringConfig Dataclass

```python
@dataclass(frozen=True)
class ScoringConfig:
    """Immutable scoring configuration loaded from YAML."""
    # Dimension weights (auto-normalize if sum != 1.0)
    signal_weight: float = 0.35
    event_weight: float = 0.30
    portfolio_weight: float = 0.20
    market_weight: float = 0.15

    # Signal type weights
    signal_type_weights: dict[str, float] = field(default_factory=lambda: {
        "attention_spike": 0.25,
        "sector_resonance": 0.20,
        "historical_pattern_match": 0.15,
        "factor_anomaly": 0.20,
        "earnings_surprise": 0.10,
        "policy_impact": 0.10,
    })

    # Event decay settings
    event_decay_enabled: bool = True
    use_category_half_life: bool = True
    freshness_boost: float = 1.2
    default_decay_rate: float = 0.1
    decay_rates: dict[str, float] = field(default_factory=dict)

    # Portfolio settings
    thesis_invalidated_weight: float = 0.5
    thesis_weakened_weight: float = 0.35
    thesis_active_weight: float = 0.15
    attention_rising_weight: float = 0.25
    attention_fading_weight: float = 0.10
    attention_stable_weight: float = 0.05
    review_overdue_days: int = 14

    # Market settings
    northbound_flow_weight: float = 0.15
    northbound_threshold_high: float = 5e8
    northbound_threshold_low: float = 1e8
    northbound_boost_high: float = 0.3
    northbound_boost_low: float = 0.1
    index_membership_boost: float = 0.10
    filter_non_constituent: bool = False
    allowed_indices: list[str] = field(default_factory=lambda: ["000300", "000905"])

    # Ranking settings
    max_entries: int = 20
    min_priority_score: float = 0.1
    dedup_strategy: str = "highest_score"
    exclude_triggers: list[str] = field(default_factory=list)
    allowed_markets: list[str] = field(default_factory=lambda: ["CN_A"])
```

### Loading Function

```python
def load_scoring_config(path: Optional[Path] = None) -> ScoringConfig:
    """Load scoring config from YAML, fallback to defaults on error."""
```

### File Location

`workspace/config/scoring.yaml`

## 4. Constraints & Risks

| Constraint | Type | Mitigation |
|------------|------|------------|
| Default config works without user intervention | MUST | Defaults are the same as F-022/F-026 defaults |
| Invalid config MUST NOT crash | MUST | Warning + fallback to defaults |
| Config changes are idempotent | MUST | Same config file always produces same output |
| Weight normalization transparent | SHOULD | Log normalized weights when auto-normalization occurs |
| YAML flat structure | MUST | Consistent with existing load_config() pattern |
| Config is first-class dependency | MUST | Passed as parameter, not loaded globally |

| Risk | Severity | Mitigation |
|------|----------|------------|
| Config file missing | LOW | Use defaults silently |
| Config file malformed | MEDIUM | Log warning, use defaults |
| Extreme weight values | LOW | Auto-normalize, log warning |
| Config changes between runs | LOW | Daily regeneration naturally handles this |
| Premature personalization | MEDIUM | Defer to iteration 2 (EP-005) |

## 5. Acceptance Criteria

- [ ] ScoringConfig is a frozen dataclass with all scoring parameters
- [ ] Default values produce valid scoring behavior
- [ ] load_scoring_config() returns defaults when file is absent
- [ ] load_scoring_config() returns defaults when file is malformed (with warning)
- [ ] Weight auto-normalization occurs when sum != 1.0 (with warning)
- [ ] YAML flat structure consistent with existing load_config() pattern
- [ ] Config passed as parameter to scoring functions (not global)
- [ ] Config changes take effect on next daily generation
- [ ] All new ScoringConfig fields have defaults (backward compatible)

## 6. Detailed Analysis References

- @../system-architect/analysis-F-027-personalization-config.md — YAML structure, validation with fallback, weight auto-normalization
- @../data-architect/analysis-F-027-personalization-config.md — ScoringConfig dataclass, YAML schema, storage strategy
- @../product-manager/analysis-F-027-personalization-config.md — User stories, deferral rationale, default sufficiency
- @../guidance-specification.md#feature-decomposition — F-027 definition and related roles

## 7. Cross-Feature Dependencies

- **Depends on**: F-022 (scoring weights), F-026 (filter rules)
- **Required by**: F-028 (tests validate configuration loading and normalization)
- **Shared patterns**: Frozen dataclass, YAML loading pattern (existing config.py)
- **Integration points**:
  - F-022: ScoringConfig is the primary dependency for all scoring functions
  - F-026: max_entries and min_score control ranking behavior
  - Existing `config.py`: Reuses load_config() for YAML parsing
- **Deferral note**: F-027 is deferred to iteration 2. F-022-F-026 use hardcoded defaults. The ScoringConfig dataclass is defined here for reference but not actively used until iteration 2.
