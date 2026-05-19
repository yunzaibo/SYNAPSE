# Cross-Cutting Analysis: P1-2 Daily Watchlist Generator

## Data Model Design

### Core Entities

The scoring pipeline introduces 3 new data structures alongside the extended WatchlistEntry:

**1. ScoringConfig** -- Immutable configuration for scoring weights and thresholds.

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| id | str | generate_id('scfg') | auto | Unique config ID |
| schema_version | str | "1.0" | "1.0" | Schema version |
| signal_weights | dict[SignalType, float] | 0.0-1.0, sum=1.0 | balanced | Weight per signal type |
| event_decay_enabled | bool | -- | True | Enable event decay |
| portfolio_boost | float | 0.0-1.0 | 0.3 | Max boost for held positions |
| market_filter_enabled | bool | -- | True | Enable market semantics filter |
| max_entries | int | 1-100 | 20 | Maximum watchlist size |
| min_score | float | 0.0-1.0 | 0.1 | Minimum priority_score threshold |

**2. ScoredEntry** -- Intermediate scoring result (not persisted, used in pipeline).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| entry | WatchlistEntry | -- | The watchlist entry being scored |
| component_scores | dict[str, float] | 0.0-1.0 each | Individual score contributions |
| total_score | float | 0.0-1.0 | Weighted sum of components |
| scoring_metadata | dict | -- | Debug/audit info (data sources used, fallbacks) |

**3. ScoringResult** -- Final output of the scoring pipeline.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| entries | list[ScoredEntry] | sorted desc by total_score | Scored and ranked entries |
| filtered_count | int | >= 0 | Entries removed by filters |
| scoring_date | date | -- | Date of scoring run |
| config_used | ScoringConfig | -- | Config snapshot for audit |
| warnings | list[str] | -- | Non-fatal issues during scoring |

### Entity Relationships

```
ScoringConfig ──1:N──> ScoringResult
ScoringResult ──1:N──> ScoredEntry
ScoredEntry ──1:1───> WatchlistEntry (existing)
ScoredEntry ──1:N───> component_scores (dict)
```

### State Machine: WatchlistEntry Lifecycle

```
                    ┌─────────────┐
                    │  GENERATED  │  (from _build_*_entries)
                    └──────┬──────┘
                           │ score()
                           v
                    ┌─────────────┐
                    │   SCORED    │  (priority_score assigned)
                    └──────┬──────┘
                           │ filter()
                    ┌──────┴──────┐
                    │             │
                    v             v
             ┌──────────┐  ┌──────────┐
             │  PASSED  │  │ FILTERED │
             └────┬─────┘  └──────────┘
                  │ rank()
                  v
             ┌──────────┐
             │  RANKED  │  (final position assigned)
             └────┬─────┘
                  │ save()
                  v
             ┌──────────┐
             │  SAVED   │  (persisted to YAML)
             └──────────┘
```

| From | To | Trigger | Guard |
|------|----|---------|-------|
| GENERATED | SCORED | score() | -- |
| SCORED | FILTERED | filter() | total_score < min_score |
| SCORED | PASSED | filter() | total_score >= min_score |
| PASSED | RANKED | rank() | -- |
| RANKED | SAVED | save() | -- |

## Error Handling Strategy

### Error Classification

| Category | Code Pattern | Severity | Recovery |
|----------|-------------|----------|----------|
| DATA_SOURCE_UNAVAILABLE | WATCHLIST_DS_UNAVAIL | WARNING | Skip data source, score with available data |
| SCORING_INVALID_INPUT | WATCHLIST_SCORING_INPUT | ERROR | Log and skip entry |
| CONFIG_INVALID | WATCHLIST_CFG_INVALID | FATAL | Use default config |
| MARKET_SEMANTICS_UNAVAIL | WATCHLIST_MKT_UNAVAIL | WARNING | Disable market filter, score without |
| SERIALIZATION_FAILED | WATCHLIST_SER_FAIL | ERROR | Log, skip entry, continue |
| SCHEMA_VERSION_MISMATCH | WATCHLIST_SCHEMA_MISMATCH | WARNING | Lazy Upcast with defaults |

### Recovery Mechanisms

1. **Data Source Unavailability**: The scoring pipeline MUST NOT fail if one data source is unavailable. Each scoring function MUST return a default score (0.0) and log a warning when its data source is missing. The `scoring_metadata` dict MUST record which sources were used.

2. **Invalid Input Handling**: Entries with malformed data (missing ticker, invalid SignalType) MUST be skipped with a logged error. The pipeline MUST continue processing remaining entries.

3. **Configuration Fallback**: If the user-provided `ScoringConfig` fails validation, the system MUST fall back to the default balanced configuration and log a WARNING.

4. **Graceful Degradation**: The `generate_daily()` function currently returns an empty list on failure. The scored version MUST return a `ScoringResult` with partial entries and warnings, rather than an empty result.

## Observability Requirements

### Metrics (MUST implement)

| Metric | Type | Description |
|--------|------|-------------|
| `watchlist_scoring_duration_ms` | histogram | Time to score all entries |
| `watchlist_entry_count` | gauge | Total entries before filtering |
| `watchlist_filtered_count` | gauge | Entries removed by filters |
| `watchlist_score_distribution` | histogram | Distribution of priority_score values |
| `watchlist_data_source_latency_ms` | histogram | Latency per data source query |
| `watchlist_generation_date` | gauge | Current generation date |
| `watchlist_scoring_warnings_total` | counter | Total warnings during scoring |

### Log Events

| Event | Level | When | Data |
|-------|-------|------|------|
| scoring_started | INFO | Pipeline start | target_date, entry_count |
| scoring_completed | INFO | Pipeline end | duration_ms, scored_count, filtered_count |
| data_source_skipped | WARNING | Source unavailable | source_name, reason |
| entry_skipped | WARNING | Entry invalid | entry_id, reason |
| config_fallback | WARNING | Config invalid | error_message |
| scoring_error | ERROR | Unrecoverable error | error_type, entry_id |

### Health Checks

| Check | Condition | Action |
|-------|-----------|--------|
| scoring_pipeline_healthy | Last run completed without FATAL errors | -- |
| data_sources_available | All configured sources responded | Alert on degradation |
| score_distribution_valid | No bimodal or all-zero distributions | Log anomaly |

## Configuration Model

### YAML Configuration Structure

```yaml
scoring:
  signal_weights:
    attention_spike: 0.25
    sector_resonance: 0.20
    historical_pattern_match: 0.15
    factor_anomaly: 0.20
    earnings_surprise: 0.10
    policy_impact: 0.10
  event_decay:
    enabled: true
    use_category_half_life: true
  portfolio:
    boost_factor: 0.3
    thesis_active_boost: 0.2
    attention_rising_boost: 0.15
  market_filter:
    enabled: true
    skip_halted: true
    skip_suspended: true
  ranking:
    max_entries: 20
    min_score: 0.1
    dedup_strategy: "highest_score"
```

### Validation Rules

- `signal_weights` values MUST be in [0.0, 1.0]
- `signal_weights` values SHOULD sum to 1.0 (warning if not, auto-normalize)
- `max_entries` MUST be in [1, 100]
- `min_score` MUST be in [0.0, 1.0]
- `boost_factor` MUST be in [0.0, 1.0]

## Boundary Scenarios

### Concurrency
- `generate_daily()` is called once per morning batch. No concurrent execution is expected within a single instance. However, if multiple instances run (e.g., CI testing), the function MUST be idempotent -- same inputs produce same outputs.

### Rate Limiting
- Data source queries (EastMoney, Akshare) MUST respect existing rate limiting in the adapter layer. The scoring pipeline SHOULD NOT introduce additional rate limiting since it operates on already-loaded data.

### Shutdown / Cleanup
- The scoring pipeline is synchronous and stateless. No cleanup is required on shutdown. Intermediate `ScoredEntry` objects are garbage collected.

### Scalability
- Current scale: ~50-200 entries per day. The pipeline design MUST handle up to 1000 entries without architectural changes.
- The scoring function composition pattern enables future parallelization if needed.

### Disaster Recovery
- The daily full regeneration model (ADR-009) provides natural DR: re-running `generate_daily()` with the same inputs produces the same output. No special recovery logic is needed.
