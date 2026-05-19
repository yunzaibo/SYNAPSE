# F-027: Personalization Config -- System Architect Analysis

## Overview

Enable user customization of scoring weights and filtering rules through YAML configuration. This allows different users to tune the watchlist generator to their research preferences without code changes.

## Current State Analysis

The existing `config.py` provides basic YAML loading (`load_config()`) and validation (`validate_config()`). There is no existing scoring configuration. The current `watchlist_generator.py` has hardcoded logic.

## Architecture: Configuration Schema

### YAML Structure

```yaml
scoring:
  weights:
    signal: 0.35
    event: 0.30
    portfolio: 0.20
    market: 0.15

  signal_types:
    attention_spike: 0.25
    sector_resonance: 0.20
    historical_pattern_match: 0.15
    factor_anomaly: 0.20
    earnings_surprise: 0.10
    policy_impact: 0.10

  event_decay:
    enabled: true
    use_category_half_life: true
    freshness_boost: 1.2

  portfolio:
    thesis_weights:
      invalidated: 0.5
      weakened: 0.35
      active: 0.15
    attention_weights:
      rising: 0.25
      fading: 0.10
      stable: 0.05
    review_overdue_days: 14

  market:
    northbound_flow_weight: 0.15
    index_membership_boost: 0.10

  ranking:
    max_entries: 20
    min_score: 0.1
    dedup_strategy: "highest_score"
```

### ScoringConfig Dataclass

```python
@dataclass
class ScoringConfig:
    """Immutable scoring configuration."""
    # Dimension weights (must sum to 1.0)
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
    index_membership_boost: float = 0.10

    # Ranking settings
    max_entries: int = 20
    min_score: float = 0.1
    dedup_strategy: str = "highest_score"
```

## Design Decisions

### D-027-1: YAML-Only Configuration

Configuration MUST be provided via YAML file, not environment variables or CLI arguments. This is consistent with the existing `load_config()` pattern and the non-goal of "no complex UI."

### D-027-2: Validation with Fallback

The config MUST be validated on load. Invalid values MUST trigger a warning and fall back to defaults:

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

### D-027-3: Weight Auto-Normalization

If dimension weights do not sum to 1.0, the config loader MUST auto-normalize:

```python
total = config.signal_weight + config.event_weight + config.portfolio_weight + config.market_weight
if abs(total - 1.0) > 0.01:
    logger.warning(f"Weights sum to {total}, auto-normalizing")
    config.signal_weight /= total
    config.event_weight /= total
    config.portfolio_weight /= total
    config.market_weight /= total
```

### D-027-4: Config as First-Class Dependency

`ScoringConfig` MUST be passed as a parameter to `score_entries()`, not loaded globally. This enables:
- Unit testing with different configs
- Future multi-user support (different configs per user)
- A/B testing of scoring strategies

### D-027-5: Non-Goals Compliance

Per the guidance-specification non-goals:
- "自定义评分公式": The scoring FORMULA is fixed (weighted sum). Only WEIGHTS are configurable.
- "机器学习推荐": No ML models. Configuration is purely rule-based.

## Integration Points

- **F-022**: `ScoringConfig` is the primary dependency for all scoring functions
- **F-026**: `max_entries` and `min_score` control ranking behavior
- **Existing `config.py`**: Reuses `load_config()` for YAML parsing

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Config file missing | LOW | Use defaults silently |
| Config file malformed | MEDIUM | Log warning, use defaults |
| Extreme weight values | LOW | Clamp to [0.0, 1.0], normalize |
| Config changes between runs | LOW | Daily regeneration naturally handles this |
