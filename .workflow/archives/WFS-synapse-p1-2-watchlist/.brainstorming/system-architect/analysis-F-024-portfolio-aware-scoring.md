# F-024: Portfolio-Aware Scoring -- System Architect Analysis

## Overview

Implement scoring adjustments based on Position thesis_status and attention_state, so that held positions receive appropriate priority in the daily watchlist. This ensures portfolio review triggers are weighted by the urgency of the thesis status.

## Current State Analysis

The existing `_build_portfolio_entries()` creates entries for ALL positions with `TriggerType.PORTFOLIO_REVIEW`. The position data available:

**Position.research_state** (from `position.py`):
- `thesis_status`: ACTIVE | WEAKENED | INVALIDATED
- `attention_state`: STABLE | RISING | FADING
- `last_review_date`: Optional[date]

Currently, all portfolio entries receive equal treatment regardless of thesis status.

## Architecture: Portfolio Scoring Function

### Scoring Function: `score_portfolio_boost()`

```python
def score_portfolio_boost(
    entry: WatchlistEntry,
    context: ScoringContext,
) -> tuple[float, str]:
    """Score portfolio entries based on thesis and attention state."""
    if entry.trigger_type != TriggerType.PORTFOLIO_REVIEW:
        return 0.0, "Not a portfolio entry"

    position = _find_position(context.positions, entry.ticker)
    if position is None:
        return 0.0, "Position not found"

    rs = position.research_state
    base_score = 0.0
    reasons = []

    # Thesis status contribution
    if rs.thesis_status == ThesisStatus.INVALIDATED:
        base_score += 0.5
        reasons.append("thesis invalidated")
    elif rs.thesis_status == ThesisStatus.WEAKENED:
        base_score += 0.35
        reasons.append("thesis weakened")
    elif rs.thesis_status == ThesisStatus.ACTIVE:
        base_score += 0.15
        reasons.append("thesis active")

    # Attention state contribution
    if rs.attention_state == AttentionState.RISING:
        base_score += 0.25
        reasons.append("attention rising")
    elif rs.attention_state == AttentionState.FADING:
        base_score += 0.10
        reasons.append("attention fading")
    elif rs.attention_state == AttentionState.STABLE:
        base_score += 0.05
        reasons.append("attention stable")

    # Recency boost: positions not reviewed recently get higher priority
    if rs.last_review_date:
        days_since_review = (context.target_date - rs.last_review_date).days
        if days_since_review > 14:
            recency_boost = min(0.2, days_since_review * 0.01)
            base_score += recency_boost
            reasons.append(f"review overdue {days_since_review}d")

    score = min(1.0, base_score)
    reason = f"Portfolio: {', '.join(reasons)} (score: {score:.2f})"
    return score, reason
```

## Design Decisions

### D-024-1: Thesis Status as Primary Signal

`ThesisStatus` is the primary driver of portfolio scoring. INVALIDATED positions MUST receive the highest portfolio score because they require immediate attention (either exit or thesis reconstruction).

| ThesisStatus | Base Score | Rationale |
|--------------|-----------|-----------|
| INVALIDATED | 0.5 | Urgent: thesis no longer holds |
| WEAKENED | 0.35 | High: thesis under pressure |
| ACTIVE | 0.15 | Low: routine monitoring |

### D-024-2: Attention State as Secondary Signal

`AttentionState` modulates the thesis signal. RISING attention on a WEAKENED thesis is more urgent than RISING attention on an ACTIVE thesis.

| AttentionState | Boost | Rationale |
|----------------|-------|-----------|
| RISING | +0.25 | Something is changing, needs review |
| FADING | +0.10 | Losing relevance, lower priority |
| STABLE | +0.05 | No change, routine |

### D-024-3: Review Recency Penalty

Positions not reviewed in > 14 days receive a recency boost. This ensures stale positions are surfaced for review. The boost scales linearly with days overdue, capped at 0.2.

**Rationale**: A position with `last_review_date` more than 2 weeks ago is at risk of thesis drift. The watchlist should flag this.

### D-024-4: Non-Portfolio Entries Score 0.0

Entries with `trigger_type != PORTFOLIO_REVIEW` MUST receive `portfolio_score = 0.0`. This ensures the portfolio dimension only affects portfolio entries, not event-driven or signal-driven entries.

## Integration Points

- **F-022**: `score_portfolio_boost()` is one stage in the scoring pipeline
- **Existing `position.py`**: Reads `Position.research_state.thesis_status`, `attention_state`, `last_review_date`
- **F-026**: Portfolio entries with high scores appear in top-N ranking

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Position not found for ticker | LOW | Return 0.0, log warning |
| Missing last_review_date | LOW | Skip recency boost |
| Thesis INVALIDATED but user wants to hold | LOW | Personalization (F-027) can override |
