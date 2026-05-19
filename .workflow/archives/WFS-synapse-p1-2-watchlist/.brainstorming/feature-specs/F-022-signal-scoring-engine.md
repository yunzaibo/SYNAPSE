# Feature Spec: F-022 - Signal Scoring Engine

**Priority**: High
**Contributing Roles**: system-architect, data-architect, product-manager
**Status**: Final (conflicts resolved)

## 1. Requirements Summary

- The scoring engine MUST compute `priority_score` (float, [0.0, 1.0]) for each WatchlistEntry from multiple data dimensions
- The engine MUST use a 4-dimension weighted sum model: signal, event, portfolio, market
- Default weights MUST be: signal=0.35, event=0.30, portfolio=0.20, market=0.15
- Weight normalization MUST auto-normalize when weights do not sum to 1.0, with a logged warning
- The engine MUST be deterministic: identical inputs MUST produce identical outputs
- The engine MUST handle missing data gracefully — missing signals/events/positions contribute 0.0, not failure
- The `reason` field MUST be composed from the highest-contributing scoring dimensions
- The engine MUST be a pure function — no I/O, no mutation of inputs
- ScoredEntry (single) and ScoringResult (batch) are the intermediate data structures
- The `generate_daily()` function MUST return `list[WatchlistEntry]`, not ScoringResult (EP-008)
- The scoring formula MUST NOT use machine learning models (guidance-specification non-goal)

## 2. Design Decisions [CORE SECTION]

### D-022-1: 4-Dimension Scoring Model

**Decision**: The scoring engine MUST use a 4-dimension model: signal, event, portfolio, market.

**Context**: The system-architect proposed 4 dimensions; the data-architect proposed 3 (excluding market). The guidance-specification confirms Market Semantics (TradingCalendar, NorthboundFlow, IndexConstituent) as a scoring input.

**Options Considered**:
- [system-architect] 4 dimensions: signal, event, portfolio, market
- [data-architect] 3 dimensions: signal, event, portfolio

**Chosen Approach**: Adopt the 4-dimension model. Market context (F-025) provides meaningful scoring signals (northbound flow, index membership) that should influence priority. (EP-001)

**Trade-offs**: More comprehensive scoring vs. additional complexity and dependency on P1-1 Market Semantics. The trade-off is acceptable because F-025 gracefully degrades when market data is unavailable (returns neutral 0.5).

**Source**: system-architect (recommended by cross-role analysis, EP-001)

### D-022-2: Default Weights — 4-Dimension Model

**Decision**: Default weights MUST be: signal=0.35, event=0.30, portfolio=0.20, market=0.15.

**Context**: The system-architect proposed these weights; the data-architect proposed different weights for a 3-dimension model. With the 4-dimension model adopted (D-022-1), the system-architect's weights are the correct reference.

**Options Considered**:
- [system-architect] {signal: 0.35, event: 0.30, portfolio: 0.20, market: 0.15}
- [data-architect] {signal: 0.3, event: 0.4, portfolio: 0.3} (3-dimension, no longer applicable)

**Chosen Approach**: Adopt system-architect's 4-dimension weights. Signal gets the highest weight because it captures real-time triggers. Event gets the second highest because recent events drive daily relevance. Portfolio provides context but is not the primary driver. Market provides institutional sentiment as a supplementary signal. (EP-001)

**Trade-offs**: Signal-heavy weighting emphasizes real-time triggers vs. potentially underweighting portfolio context. The weights are configurable via F-027 (deferred to iteration 2) so users can adjust later.

**Source**: system-architect (recommended by cross-role analysis, EP-001)

### D-022-3: Weight Auto-Normalization with Warning

**Decision**: If dimension weights do not sum to 1.0, the scoring engine MUST auto-normalize and log a warning.

**Context**: The system-architect proposed auto-normalize; the data-architect proposed raising ValueError. The product-manager requires that invalid configs MUST NOT crash the system.

**Options Considered**:
- [system-architect] Auto-normalize silently
- [data-architect] Raise ValueError
- [product-manager] Invalid configs must not crash — "not a crash" requirement

**Chosen Approach**: Auto-normalize with a logged warning. This satisfies the product-manager's non-crash requirement while alerting developers to misconfiguration. (EP-002)

```python
total = config.signal_weight + config.event_weight + config.portfolio_weight + config.market_weight
if abs(total - 1.0) > 0.01:
    logger.warning(f"Weights sum to {total:.4f}, auto-normalizing to 1.0")
    config.signal_weight /= total
    config.event_weight /= total
    config.portfolio_weight /= total
    config.market_weight /= total
```

**Trade-offs**: Resilience vs. silent misconfiguration. The warning log mitigates the silent aspect. The alternative (ValueError) would crash the daily generation pipeline, which is worse.

**Source**: system-architect (recommended by cross-role analysis, EP-002)

### D-022-4: Pipeline Architecture with Composable Scoring Functions

**Decision**: The scoring engine MUST be implemented as a pipeline of composable scoring functions, each independently testable and replaceable.

**Context**: All roles agree on the pipeline architecture. Each scoring dimension is a separate function that returns `(score_contribution, reason_text)`.

**Options Considered**:
- [system-architect] Pipeline of composable ScoringFunction callables
- [data-architect] Pure function `compute_score()` with component extraction

**Chosen Approach**: Pipeline architecture. Each stage is a `ScoringFunction = Callable[[WatchlistEntry, ScoringContext], tuple[float, str]]`. The pipeline aggregates results into a final score. (All roles consensus)

**Trade-offs**: Composability and testability vs. slightly more complex orchestration. The trade-off is strongly favorable because each dimension can be tested, debugged, and replaced independently.

**Source**: system-architect, data-architect, product-manager (consensus)

### D-022-5: Intermediate Data Structures — ScoredEntry and ScoringResult

**Decision**: The intermediate data structures MUST be ScoredEntry (single ticker) and ScoringResult (batch).

**Context**: The system-architect proposed ScoredEntry; the data-architect proposed ScoreResult. The naming should be unified.

**Options Considered**:
- [system-architect] ScoredEntry for single, no batch type defined
- [data-architect] ScoreResult for single, no batch type defined

**Chosen Approach**: Adopt unified naming: `ScoredEntry` for a single scored ticker (contains entry, total_score, component_scores, reason), `ScoringResult` for a batch result (contains list of ScoredEntry, metadata). (EP-004)

**Trade-offs**: Clear semantic distinction between single and batch vs. two types to maintain. The trade-off is favorable because the batch type carries generation metadata (timestamp, config hash) that single entries do not.

**Source**: system-architect, data-architect (recommended by cross-role analysis, EP-004)

### D-022-6: Graceful Degradation on Missing Data

**Decision**: Each scoring function MUST handle missing data gracefully. Missing signals/events/positions contribute 0.0 to the score. Market data unavailability returns neutral 0.5.

**Context**: The system-architect and product-manager agree on graceful degradation. The pipeline MUST NOT raise exceptions for missing data.

**Options Considered**:
- [system-architect] Return 0.0 for missing signal/event/portfolio; 0.5 for missing market
- [product-manager] Missing data must not crash — graceful degradation

**Chosen Approach**: Each scoring function returns (0.0, "No data") for missing inputs, except market context which returns (0.5, "Market data unavailable") as a neutral default. The pipeline logs warnings for missing data but continues.

**Trade-offs**: Resilience vs. potential for misleading scores. The neutral market default (0.5) is a reasonable compromise — it neither penalizes nor boosts entries when market data is absent.

**Source**: system-architect, product-manager (consensus)

### D-022-7: reason Field Composition

**Decision**: The `reason` field MUST be composed from the highest-contributing scoring dimensions using the format: `"{top_dimension}: {brief_explanation} (score: {total_score:.2f})"`.

**Context**: The product-manager requires that reason strings reference at least one specific signal. The system-architect defines the format pattern.

**Options Considered**:
- [system-architect] Structured format: "{top_dimension}: {brief_explanation} (score: {total_score:.2f})"
- [product-manager] reason must reference at least one specific signal, 10-200 chars

**Chosen Approach**: Structured reason format. The scoring engine composes reason from the top-contributing dimensions. The 10-200 character range is a generation recommendation, not a schema constraint.

**Trade-offs**: Consistent, machine-parseable reason format vs. less natural language. The format is human-readable while being structured enough for debugging.

**Source**: system-architect (format), product-manager (content requirements)

## 3. Interface Contract

### Scoring Function Signatures

```python
ScoringFunction = Callable[[WatchlistEntry, ScoringContext], tuple[float, str]]

@dataclass(frozen=True)
class ScoringContext:
    events: list[Event]
    signals: list[Signal]
    positions: list[Position]
    target_date: date
    config: ScoringConfig
    market_data: Optional[MarketSemanticsData] = None
```

### Intermediate Data Structures

```python
@dataclass(frozen=True)
class ScoredEntry:
    """Single scored ticker result."""
    entry: WatchlistEntry
    total_score: float
    component_scores: dict[str, float]  # {"signal": 0.3, "event": 0.5, ...}
    reason: str

@dataclass(frozen=True)
class ScoringResult:
    """Batch scoring result."""
    entries: list[ScoredEntry]
    target_date: date
    generation_timestamp: datetime
    config_hash: str  # For audit trail
```

### Pipeline Stages

| Stage | Function | Input | Output | Weight Source |
|-------|----------|-------|--------|---------------|
| 1 | `score_signal_contribution()` | Entry + Signals | 0.0-1.0 + reason | config.signal_weight |
| 2 | `score_event_decay()` | Entry + Events | 0.0-1.0 + reason | Event.decay_rate + lifecycle |
| 3 | `score_portfolio_boost()` | Entry + Positions | 0.0-1.0 + reason | config.portfolio_weight |
| 4 | `score_market_context()` | Entry + MarketData | 0.0-1.0 + reason | config.market_weight |
| 5 | `aggregate_scores()` | All component scores | final 0.0-1.0 + reason | Weighted sum |

### Aggregation Formula

```
priority_score = clamp(
    w_signal * signal_score +
    w_event * event_score +
    w_portfolio * portfolio_score +
    w_market * market_score,
    0.0, 1.0
)
```

### API Integration

```python
def generate_daily(
    target_date: date,
    config: ScoringConfig,
    events: list[Event],
    signals: list[Signal],
    positions: list[Position],
    market_data: Optional[MarketSemanticsData] = None,
) -> list[WatchlistEntry]:
    """Returns scored, ranked WatchlistEntry list."""
```

## 4. Constraints & Risks

| Constraint | Type | Mitigation |
|------------|------|------------|
| Deterministic scoring | MUST | No randomness; deterministic data sources; golden file tests |
| Graceful degradation on missing data | MUST | Each function returns (0.0, "No data") for missing inputs |
| Weight normalization | MUST | Auto-normalize with warning when weights != 1.0 |
| Reason string format | MUST | Structured format with signal references; 10-200 chars recommended |
| No ML models | MUST NOT | Rule-based scoring only; no trained models or embeddings |
| Pure function requirement | MUST | No I/O, no mutation of inputs in scoring functions |
| generate_daily() return type | MUST | Returns list[WatchlistEntry], not ScoringResult (EP-008) |

| Risk | Severity | Mitigation |
|------|----------|------------|
| Weight tuning complexity | MEDIUM | Start with fixed defaults; F-027 (deferred) allows user override |
| Score explanation verbosity | LOW | Truncate reason to 200 chars max |
| Non-deterministic scoring | HIGH | Use deterministic data sources; no random factors; golden file tests |
| Score distribution clustering | MEDIUM | Validate score distribution is roughly normal centered 0.4-0.6 |

## 5. Acceptance Criteria

- [ ] Scoring engine computes priority_score for each WatchlistEntry from 4 dimensions
- [ ] Default weights: signal=0.35, event=0.30, portfolio=0.20, market=0.15
- [ ] Weights auto-normalize with warning when sum != 1.0
- [ ] Identical inputs produce identical outputs (determinism)
- [ ] Missing signals/events/positions contribute 0.0, not failure
- [ ] Missing market data returns neutral 0.5
- [ ] reason string references at least one scoring dimension
- [ ] priority_score is clamped to [0.0, 1.0]
- [ ] ScoredEntry and ScoringResult intermediate types are frozen dataclasses
- [ ] generate_daily() returns list[WatchlistEntry] (not ScoringResult)
- [ ] Each scoring function is independently testable
- [ ] Score distribution is roughly normal centered 0.4-0.6 (validated by golden file tests)

## 6. Detailed Analysis References

- @../system-architect/analysis-F-022-signal-scoring-engine.md — Pipeline architecture, composability, default weights, graceful degradation
- @../data-architect/analysis-F-022-signal-scoring-engine.md — ScoreResult data model, component scores, normalization
- @../product-manager/analysis-F-022-signal-scoring-engine.md — User stories, scoring transparency, reason quality
- @../guidance-specification.md#feature-decomposition — F-022 definition and related roles

## 7. Cross-Feature Dependencies

- **Depends on**: F-021 (WatchlistEntry schema with priority_score and reason fields)
- **Required by**: F-026 (ranking uses priority_score), F-028 (tests validate scoring)
- **Shared patterns**: Pure function pattern, Graceful Degradation strategy (guidance-specification)
- **Integration points**:
  - F-023: `score_event_decay()` uses `apply_category_decay()` from event/lifecycle.py
  - F-024: `score_portfolio_boost()` reads Position.thesis_status and attention_state
  - F-025: `score_market_context()` uses TradingCalendar, NorthboundFlow, IndexConstituent
  - F-027: ScoringConfig for weight customization (deferred to iteration 2)
