# Feature Spec: F-024 - Portfolio-Aware Scoring

**Priority**: High
**Contributing Roles**: system-architect, data-architect, product-manager
**Status**: Final (conflicts resolved)

## 1. Requirements Summary

- Portfolio entries MUST receive scoring adjustments based on Position thesis_status and attention_state
- ThesisAttentionMap MUST be a `dict[str, tuple[ThesisStatus, AttentionState]]` lookup structure
- INVALIDATED thesis_status MUST receive the highest portfolio boost (urgency signal)
- WEAKENED thesis_status MUST receive medium portfolio boost
- ACTIVE thesis_status MUST receive minimal portfolio boost
- RISING attention_state MUST increase portfolio score
- FADING attention_state MUST decrease portfolio score
- Non-portfolio entries (trigger_type != PORTFOLIO_REVIEW) MUST receive portfolio_score = 0.0
- Positions not reviewed in > 14 days SHOULD receive a recency boost
- The portfolio scoring function MUST be a pure function
- Portfolio scoring is SYNAPSE's key differentiator versus generic stock screeners

## 2. Design Decisions [CORE SECTION]

### D-024-1: ThesisAttentionMap Structure

**Decision**: ThesisAttentionMap MUST be `dict[str, tuple[ThesisStatus, AttentionState]]`, keyed by ticker.

**Context**: The data-architect defines ThesisAttentionMap as a lookup structure derived from `list[Position]`. The system-architect references it but does not define the structure.

**Options Considered**:
- [data-architect] dict[str, tuple[ThesisStatus, AttentionState]]
- [system-architect] References ThesisAttentionMap without defining structure

**Chosen Approach**: Adopt data-architect's tuple structure. The map is constructed by `build_thesis_attention_map(positions)` — a pure function that extracts `(research_state.thesis_status, research_state.attention_state)` for each position. (EP-004 resolution, SUGGESTED)

```python
ThesisAttentionMap = dict[str, tuple[ThesisStatus, AttentionState]]

def build_thesis_attention_map(positions: list[Position]) -> ThesisAttentionMap:
    """Pure function: extract thesis/attention state per ticker."""
    return {
        pos.ticker: (pos.research_state.thesis_status, pos.research_state.attention_state)
        for pos in positions
    }
```

**Trade-offs**: Simple lookup structure vs. no additional metadata (e.g., last_review_date). The trade-off is acceptable because last_review_date is accessed directly from Position, not through the map.

**Source**: data-architect (definition, SUGGESTED by cross-role analysis)

### D-024-2: Thesis Status as Primary Signal

**Decision**: ThesisStatus is the primary driver of portfolio scoring. INVALIDATED positions MUST receive the highest portfolio score because they require immediate attention.

**Context**: The system-architect and data-architect define different scoring approaches. The system-architect uses additive scoring (base_score += thesis_contribution + attention_contribution). The data-architect uses multiplicative scoring (thesis_multiplier * 0.6 + attention_multiplier * 0.4).

**Options Considered**:
- [system-architect] Additive: INVALIDATED=0.5, WEAKENED=0.35, ACTIVE=0.15 + attention boost
- [data-architect] Multiplicative: INVALIDATED=1.0, WEAKENED=0.5, ACTIVE=0.0 * 0.6 weight

**Chosen Approach**: Adopt the system-architect's additive approach. It is more intuitive and easier to reason about. The thesis status scores (INVALIDATED=0.5, WEAKENED=0.35, ACTIVE=0.15) directly map to urgency levels. (All roles consensus on thesis_status as primary)

| ThesisStatus | Base Score | Rationale |
|--------------|-----------|-----------|
| INVALIDATED | 0.5 | Urgent: thesis no longer holds |
| WEAKENED | 0.35 | High: thesis under pressure |
| ACTIVE | 0.15 | Low: routine monitoring |

**Trade-offs**: Additive approach is simpler to understand vs. multiplicative approach provides natural scaling. The additive approach is preferred for P1-2 because it is easier to debug and explain in reason strings.

**Source**: system-architect (primary), data-architect (alternative considered)

### D-024-3: Attention State as Secondary Signal

**Decision**: AttentionState modulates the thesis signal. RISING attention on a WEAKENED thesis is more urgent than RISING attention on an ACTIVE thesis.

**Options Considered**:
- [system-architect] Additive: RISING=+0.25, FADING=+0.10, STABLE=+0.05
- [data-architect] Multiplicative: RISING=0.5, FADING=1.0, STABLE=0.0 * 0.4 weight

**Chosen Approach**: Adopt the system-architect's additive approach, consistent with D-024-2.

| AttentionState | Boost | Rationale |
|----------------|-------|-----------|
| RISING | +0.25 | Something is changing, needs review |
| FADING | +0.10 | Losing relevance, lower priority |
| STABLE | +0.05 | No change, routine |

**Trade-offs**: Consistent additive model vs. data-architect's multiplicative model. The additive model is simpler and produces the same qualitative behavior.

**Source**: system-architect (primary), data-architect (alternative considered)

### D-024-4: Review Recency Penalty

**Decision**: Positions not reviewed in > 14 days SHOULD receive a recency boost, scaling linearly with days overdue, capped at 0.2.

**Context**: A position with `last_review_date` more than 2 weeks ago is at risk of thesis drift. The watchlist should flag this.

**Options Considered**:
- [system-architect] Linear boost: min(0.2, days_overdue * 0.01) for > 14 days
- [data-architect] No recency boost defined

**Chosen Approach**: Adopt system-architect's recency boost. It is a natural extension of portfolio awareness — stale positions need review.

**Trade-offs**: Additional scoring signal vs. complexity. The linear scaling is simple and predictable.

**Source**: system-architect

### D-024-5: Non-Portfolio Entries Score 0.0

**Decision**: Entries with `trigger_type != PORTFOLIO_REVIEW` MUST receive `portfolio_score = 0.0`. The portfolio dimension only affects portfolio entries.

**Context**: The system-architect and data-architect agree on this constraint. Non-portfolio entries (event-driven, signal-driven) should not be boosted by portfolio context.

**Options Considered**:
- [system-architect] portfolio_score = 0.0 for non-portfolio entries
- [data-architect] portfolio_score = 0.0 for non-positioned tickers

**Chosen Approach**: Both are consistent. Non-portfolio entries get portfolio_score = 0.0. This ensures the portfolio dimension is scoped correctly.

**Trade-offs**: Clean separation of portfolio vs. non-portfolio scoring vs. potential missed opportunity to boost non-portfolio entries that match a position ticker. The separation is cleaner for P1-2.

**Source**: system-architect, data-architect (consensus)

## 3. Interface Contract

### Scoring Function

```python
def score_portfolio_boost(
    entry: WatchlistEntry,
    context: ScoringContext,
) -> tuple[float, str]:
    """Score portfolio entries based on thesis and attention state."""
```

### ThesisAttentionMap

```python
ThesisAttentionMap = dict[str, tuple[ThesisStatus, AttentionState]]

def build_thesis_attention_map(positions: list[Position]) -> ThesisAttentionMap:
    """Pure function: extract thesis/attention state per ticker."""
```

### Scoring Logic

```
score_portfolio_boost(entry, context):
  1. Check trigger_type != PORTFOLIO_REVIEW -> return (0.0, "Not a portfolio entry")
  2. Find position by ticker in context.positions
  3. If not found -> return (0.0, "Position not found")
  4. Compute thesis contribution:
     - INVALIDATED: +0.5
     - WEAKENED: +0.35
     - ACTIVE: +0.15
  5. Compute attention contribution:
     - RISING: +0.25
     - FADING: +0.10
     - STABLE: +0.05
  6. Compute recency boost (if last_review_date > 14 days overdue):
     - min(0.2, days_overdue * 0.01)
  7. Clamp total to [0.0, 1.0]
  8. Return (score, reason)
```

### Data Flow

```
build_thesis_attention_map(positions) → ThesisAttentionMap
    ↓
For each ticker in watchlist:
    if ticker in map:
        portfolio_score = thesis_contribution + attention_contribution + recency_boost
    else:
        portfolio_score = 0.0
    ↓
ScoreResult.component_scores["portfolio"] = portfolio_score
```

## 4. Constraints & Risks

| Constraint | Type | Mitigation |
|------------|------|------------|
| Score range [0.0, 1.0] | MUST | Clamp after all additions |
| Non-portfolio entries score 0.0 | MUST | Check trigger_type before scoring |
| ThesisAttentionMap is pure function | MUST | No I/O, no mutation of inputs |
| Missing position data = no failure | MUST | Return 0.0, log warning |
| Thesis INVALIDATED = highest boost | MUST | INVALIDATED base score = 0.5 |

| Risk | Severity | Mitigation |
|------|----------|------------|
| Position not found for ticker | LOW | Return 0.0, log warning |
| Missing last_review_date | LOW | Skip recency boost |
| Thesis INVALIDATED but user wants to hold | LOW | F-027 (deferred) can override |
| Stale Position data | LOW | Daily regeneration reads fresh data |

## 5. Acceptance Criteria

- [ ] score_portfolio_boost() returns (0.0, "Not a portfolio entry") for non-PORTFOLIO_REVIEW entries
- [ ] INVALIDATED thesis_status contributes +0.5 to portfolio score
- [ ] WEAKENED thesis_status contributes +0.35 to portfolio score
- [ ] ACTIVE thesis_status contributes +0.15 to portfolio score
- [ ] RISING attention_state contributes +0.25 to portfolio score
- [ ] FADING attention_state contributes +0.10 to portfolio score
- [ ] STABLE attention_state contributes +0.05 to portfolio score
- [ ] Positions not reviewed in > 14 days receive recency boost (capped at 0.2)
- [ ] Non-positioned tickers receive portfolio_score = 0.0
- [ ] build_thesis_attention_map() is a pure function
- [ ] Total portfolio score is clamped to [0.0, 1.0]

## 6. Detailed Analysis References

- @../system-architect/analysis-F-024-portfolio-aware-scoring.md — Additive scoring, thesis/attention mapping, recency boost
- @../data-architect/analysis-F-024-portfolio-aware-scoring.md — ThesisAttentionMap structure, multiplicative scoring alternative
- @../product-manager/analysis-F-024-portfolio-aware-scoring.md — User stories, thesis-aware scoring rationale, non-portfolio guarantee
- @../guidance-specification.md#feature-decomposition — F-024 definition and related roles

## 7. Cross-Feature Dependencies

- **Depends on**: Position schema (thesis_status, attention_state, last_review_date)
- **Required by**: F-022 (portfolio component of scoring pipeline), F-028 (tests validate portfolio adjustments)
- **Shared patterns**: Pure function pattern, ThesisAttentionMap as lookup dict
- **Integration points**:
  - F-022: `score_portfolio_boost()` is stage 3 in the scoring pipeline
  - F-027: Portfolio weights configurable via YAML (deferred to iteration 2)
  - Existing `position.py`: Reads Position.research_state.thesis_status, attention_state, last_review_date
