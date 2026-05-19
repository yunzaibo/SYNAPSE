# F-024: Portfolio-Aware Scoring — Data Architect Analysis

## Feature Summary

Incorporate Position research state (thesis_status and attention_state) into the scoring engine. Existing positions with concerning states receive higher priority scores.

## Data Model: ThesisAttentionMap

### Definition

```python
# Type alias, not a class — it is a lookup structure, not an entity
ThesisAttentionMap = dict[str, tuple[ThesisStatus, AttentionState]]
```

Keyed by ticker. Derived from `list[Position]` by extracting `(research_state.thesis_status, research_state.attention_state)` for each position.

### Construction Function

```python
def build_thesis_attention_map(positions: list[Position]) -> ThesisAttentionMap:
```

**Constraints**:
- MUST be a pure function
- If multiple positions exist for the same ticker (should not happen but defensive), the LAST one wins
- MUST return empty dict for empty input

## Scoring Multipliers

### Thesis Status Impact

| ThesisStatus | Multiplier | Rationale |
|--------------|-----------|-----------|
| ACTIVE | 0.0 | No boost — thesis is healthy, lower priority |
| WEAKENED | 0.5 | Medium boost — thesis needs attention |
| INVALIDATED | 1.0 | Maximum boost — thesis is broken, urgent review |

### Attention State Impact

| AttentionState | Multiplier | Rationale |
|----------------|-----------|-----------|
| STABLE | 0.0 | No boost — attention is normal |
| RISING | 0.5 | Medium boost — something is changing |
| FADING | 1.0 | Maximum boost — losing track, needs review |

### Composite Portfolio Score

```
portfolio_score = thesis_multiplier * 0.6 + attention_multiplier * 0.4
```

Thesis status gets 60% weight within the portfolio component because it is a more direct signal of research state. Attention state gets 40%.

**Constraints**:
- `portfolio_score` MUST be in [0.0, 1.0]
- For non-positioned tickers (not in the map), `portfolio_score` = 0.0 — no boost, no penalty

## Data Flow

```
build_thesis_attention_map(positions) → ThesisAttentionMap
    ↓
For each ticker in watchlist:
    if ticker in map:
        portfolio_score = thesis_mult * 0.6 + attention_mult * 0.4
    else:
        portfolio_score = 0.0
    ↓
ScoreResult.component_scores["portfolio"] = portfolio_score
```

## Position Tickers in Watchlist

The existing `_build_portfolio_entries` creates WatchlistEntry for each Position. P1-2 MUST ensure:
- Position-based entries get portfolio_score = 1.0 (they ARE the position, so max boost)
- Non-position entries whose ticker matches a position get the appropriate multiplier
- The scoring engine MUST handle both cases: entries created from positions AND entries from events/signals that happen to match a position ticker

## Storage Impact

- ThesisAttentionMap is ephemeral — constructed at start of scoring, discarded after
- Position.research_state is already stored — no schema changes needed
- The portfolio_score feeds into ScoreResult.component_scores["portfolio"]

## Risks

- **Low**: Stale Position data (not updated recently) could produce misleading portfolio scores. Mitigation: this is a data freshness concern, not a scoring logic concern. The daily regeneration model means Position data is read fresh each morning.
