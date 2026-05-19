# F-027: Personalization Config — Data Architect Analysis

## Feature Summary

Define the YAML configuration schema for user-customizable scoring weights, filtering rules, and decay parameters.

## Data Model: ScoringConfig

### Definition

```python
@dataclass(frozen=True)
class ScoringConfig:
    """Immutable scoring configuration loaded from YAML."""
    # --- Weight allocation (MUST sum to 1.0) ---
    signal_weight: float = 0.3
    event_weight: float = 0.4
    portfolio_weight: float = 0.3

    # --- Event decay defaults ---
    default_decay_rate: float = 0.1
    decay_rates: dict[str, float] = field(default_factory=dict)  # EventType → rate override

    # --- Portfolio scoring ---
    thesis_active_boost: float = 0.0
    thesis_weakened_boost: float = 0.5
    thesis_invalidated_boost: float = 1.0
    attention_stable_boost: float = 0.0
    attention_rising_boost: float = 0.5
    attention_fading_boost: float = 1.0
    thesis_weight_in_portfolio: float = 0.6   # Within portfolio component

    # --- Market semantics ---
    northbound_threshold_high: float = 5e8   # 5亿 CNY
    northbound_threshold_low: float = 1e8    # 1亿 CNY
    northbound_boost_high: float = 0.3
    northbound_boost_low: float = 0.1
    filter_non_constituent: bool = False
    allowed_indices: list[str] = field(default_factory=lambda: ["000300", "000905"])

    # --- Filtering ---
    min_priority_score: float = 0.0
    max_entries: Optional[int] = None
    exclude_triggers: list[str] = field(default_factory=list)
    allowed_markets: list[str] = field(default_factory=lambda: ["CN_A"])

    def __post_init__(self) -> None:
        total = self.signal_weight + self.event_weight + self.portfolio_weight
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Weights must sum to 1.0, got {total:.6f}"
            )
```

**Why frozen**: Config is loaded once at generation time, shared across all scoring calls. Immutability prevents accidental runtime modification.

## YAML Schema

### File Location

`workspace/config/scoring.yaml`

### Example Content

```yaml
# Scoring weights — MUST sum to 1.0
signal_weight: 0.3
event_weight: 0.4
portfolio_weight: 0.3

# Event decay rates by type
default_decay_rate: 0.1
decay_rates:
  earnings: 0.15
  policy: 0.05
  sector_rotation: 0.10
  macro_data: 0.20

# Portfolio scoring multipliers
thesis_active_boost: 0.0
thesis_weakened_boost: 0.5
thesis_invalidated_boost: 1.0
attention_stable_boost: 0.0
attention_rising_boost: 0.5
attention_fading_boost: 1.0
thesis_weight_in_portfolio: 0.6

# Market semantics
northbound_threshold_high: 500000000
northbound_threshold_low: 100000000
filter_non_constituent: false
allowed_indices:
  - "000300"
  - "000905"

# Filtering
min_priority_score: 0.0
max_entries: null
exclude_triggers: []
allowed_markets:
  - "CN_A"
```

### Loading Function

```python
def load_scoring_config(path: Path) -> ScoringConfig:
```

**Constraints**:
- MUST validate weight sum on load (via `__post_init__`)
- MUST provide sensible defaults for all fields — missing YAML keys use dataclass defaults
- MUST raise clear error if YAML is malformed or weights don't sum to 1.0
- Config file MAY be absent — defaults MUST produce valid scoring behavior

## Storage Strategy

- Single YAML file per workspace — not per day
- Config is NOT versioned with WatchlistEntry schema — independent lifecycle
- Config changes take effect on next daily generation (no mid-day reload)
- Config SHOULD be checked into version control for reproducibility

## Backward Compatibility

- New fields added to ScoringConfig MUST have defaults — old YAML files remain valid
- Deprecated fields SHOULD be logged as warnings, not errors
- Config schema version MAY be added in future iterations (not required for P1-2)

## Risks

- **Medium**: Users may set weights that don't sum to 1.0. Mitigation: `__post_init__` validation with clear error message.
- **Low**: Extremely low max_entries (e.g., 1) could produce unusable watchlists. Mitigation: log warning if max_entries < 5.
