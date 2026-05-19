# F-028: Watchlist Tests — Data Architect Analysis

## Feature Summary

Extend `tests/unit/test_projection.py` with comprehensive tests for scoring, ranking, filtering, and serialization round-trips. Data-architect perspective focuses on serialization correctness and data model invariants.

## Test Categories

### 1. Schema Round-Trip Tests (F-021)

| Test Case | Description | Assertion |
|-----------|-------------|-----------|
| `test_watchlist_entry_v2_round_trip` | v2.0 object with priority_score + reason → dict → object | All fields preserved |
| `test_watchlist_entry_v1_upcast` | v1.0 dict (no priority_score/reason) → v2.0 object | priority_score=0.0, reason="" |
| `test_watchlist_entry_yaml_round_trip` | v2.0 object → YAML → v2.0 object | Full serialization fidelity |
| `test_priority_score_validation` | priority_score=-0.1 or 1.1 | ValueError raised |
| `test_priority_score_boundary` | priority_score=0.0 and 1.0 | No error, value preserved |
| `test_reason_preserved` | reason with special chars (Chinese, punctuation) | String preserved exactly |

### 2. Scoring Engine Tests (F-022)

| Test Case | Description | Assertion |
|-----------|-------------|-----------|
| `test_compute_score_empty_inputs` | All inputs empty | score=0.0, reason non-empty |
| `test_compute_score_signal_only` | Only signals provided | signal component > 0, others = 0 |
| `test_compute_score_event_only` | Only events provided | event component > 0, others = 0 |
| `test_compute_score_portfolio_only` | Only positions provided | portfolio component > 0, others = 0 |
| `test_compute_score_all_components` | All inputs provided | All components > 0, normalized in [0,1] |
| `test_score_weight_sum_validation` | Weights sum != 1.0 | ValueError raised |
| `test_score_result_frozen` | Attempt to mutate ScoreResult | FrozenInstanceError |

### 3. Decay Tests (F-023)

| Test Case | Description | Assertion |
|-----------|-------------|-----------|
| `test_decay_fresh_event` | event_date = target_date | decay_factor = 1.0 |
| `test_decay_aged_event` | event_date 5 days ago, rate=0.1 | decay_factor = 0.5 |
| `test_decay_fully_expired` | event_date 10 days ago, rate=0.1 | decay_factor = 0.0 |
| `test_decay_no_event_date` | event_date = None | decay_factor = 1.0 |
| `test_decay_future_event` | event_date > target_date | decay_factor = 1.0 |
| `test_decay_zero_rate` | decay_rate = 0.0 | decay_factor always 1.0 |

### 4. Portfolio Scoring Tests (F-024)

| Test Case | Description | Assertion |
|-----------|-------------|-----------|
| `test_thesis_active_no_boost` | ThesisStatus.ACTIVE | portfolio_score = 0.0 |
| `test_thesis_weakened_medium_boost` | ThesisStatus.WEAKENED | portfolio_score = 0.5*0.6 = 0.3 |
| `test_thesis_invalidated_max_boost` | ThesisStatus.INVALIDATED | portfolio_score = 1.0*0.6 = 0.6 |
| `test_attention_rising_boost` | AttentionState.RISING | adds 0.5*0.4 = 0.2 |
| `test_non_positioned_ticker` | Ticker not in map | portfolio_score = 0.0 |
| `test_thesis_attention_map_empty` | No positions | Empty dict |

### 5. Ranking and Filtering Tests (F-026)

| Test Case | Description | Assertion |
|-----------|-------------|-----------|
| `test_ranking_descending` | Multiple entries with different scores | Sorted descending |
| `test_tie_breaking_by_ticker` | Same priority_score | Sorted by ticker alphabetically |
| `test_min_priority_score_filter` | min_score = 0.5 | Entries below 0.5 removed |
| `test_max_entries_limit` | max_entries = 3 | Only top 3 returned |
| `test_exclude_triggers` | exclude_triggers = ["portfolio_review"] | Those entries removed |
| `test_allowed_markets` | allowed_markets = ["CN_A"] only | Non-CN_A entries removed |
| `test_filtered_count_accuracy` | Mixed inputs | filtered_count matches actual removals |
| `test_empty_input` | No entries | RankedWatchlist with total_count=0 |

### 6. Config Tests (F-027)

| Test Case | Description | Assertion |
|-----------|-------------|-----------|
| `test_config_defaults` | Load empty YAML | All defaults applied |
| `test_config_weight_validation` | Weights sum = 0.9 | ValueError raised |
| `test_config_custom_weights` | Custom weights summing to 1.0 | Values preserved |
| `test_config_missing_file` | Config file absent | Defaults used |
| `test_config_frozen` | Attempt to mutate | FrozenInstanceError |

## Test Data Fixtures

### Shared Fixtures

```python
@pytest.fixture
def default_config() -> ScoringConfig:
    return ScoringConfig()  # All defaults

@pytest.fixture
def sample_events() -> list[Event]:
    # 3 events: fresh, aged, expired

@pytest.fixture
def sample_signals() -> list[Signal]:
    # 3 signals: weak, medium, strong

@pytest.fixture
def sample_positions() -> list[Position]:
    # 3 positions: active, weakened, invalidated
```

### Test Independence

Each test MUST be independent — no shared mutable state between tests. Fixtures MUST produce fresh objects for each test. This aligns with the frozen dataclass pattern.

## Coverage Target

- Scoring engine: 100% branch coverage on compute_score
- Decay logic: 100% branch coverage on compute_decay
- Ranking: 100% path coverage on rank_and_filter
- Serialization: All to_dict/from_dict pairs tested for round-trip
- Config: Load, validate, default paths covered

## Risks

- **Low**: Test file may grow large. Mitigation: organize into pytest classes by feature.
- **Low**: Test fixtures may become stale as schemas evolve. Mitigation: fixtures use factory functions, not hardcoded dicts.
