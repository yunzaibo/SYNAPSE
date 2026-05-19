# Product Manager Analysis: F-024 Portfolio-Aware Scoring

## Feature Overview

F-024 adjusts watchlist scoring based on the user's existing portfolio positions. Stocks the user already holds are scored differently from stocks they are considering. The adjustment is driven by two Position attributes: `thesis_status` (confirmed, monitoring, speculative) and `attention_state` (high, normal, low).

This feature is SYNAPSE's key differentiator versus generic stock screeners. Most screeners treat all stocks equally; portfolio-aware scoring acknowledges that managing an existing position is fundamentally different from discovering a new opportunity.

## User Stories

### US-F024-01: Thesis-Aligned Scoring
**As a** portfolio manager, **I want** my existing holdings scored based on their thesis status **so that** I focus attention on positions that need active management.

**Acceptance Criteria**:
- confirmed thesis positions receive a moderate boost (0.1-0.2) to priority_score
- monitoring thesis positions receive a strong boost (0.2-0.3) to priority_score
- speculative thesis positions receive the strongest boost (0.3-0.4) to priority_score
- Non-portfolio stocks are scored without portfolio adjustment

### US-F024-02: Attention Steering
**As an** investor, **I want** positions marked as high-attention to score higher **so that** I don't lose track of stocks requiring close monitoring.

**Acceptance Criteria**:
- high attention_state adds 0.2 to priority_score
- normal attention_state adds 0.0 (no adjustment)
- low attention_state subtracts 0.1 from priority_score
- Attention state adjustments are capped at 0.0-1.0 total range

### US-F024-03: New Opportunity Detection
**As an** investor, **I want** non-portfolio stocks with strong signals to appear alongside my holdings **so that** I discover new opportunities that align with my investment style.

**Acceptance Criteria**:
- Non-portfolio stocks are scored using pure Signal + Event scoring
- Strong-signal non-portfolio stocks can rank above weak-signal portfolio stocks
- The watchlist always includes at least 3 non-portfolio entries when available

## User Journey Mapping

**Current State**: User receives a flat list mixing holdings and opportunities. They must mentally separate "things I own" from "things I might buy."

**Desired State**: Scoring naturally prioritizes based on portfolio context. Active positions that need attention surface alongside strong new opportunities.

**Pain Points Addressed**:
- "I forget to monitor a position I'm worried about" -- solved by attention_state boost
- "My watchlist is dominated by stocks I already own" -- solved by balanced scoring weights
- "I miss new opportunities because my list is full of holdings" -- solved by non-portfolio entry guarantee

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Portfolio coverage | >= 90% of portfolio positions with attention_state=high appear in top-20 | Automated check |
| Opportunity discovery | >= 3 non-portfolio entries in watchlist when > 10 candidates exist | Automated check |
| Score adjustment accuracy | Portfolio adjustments produce score changes within expected ranges | Unit tests |

## Priority Assessment

**MoSCoW**: Must

**Rationale**: Portfolio-awareness is SYNAPSE's competitive advantage. Without it, the watchlist is a generic screener. The effort is medium (position data integration, adjustment calculation), and the impact on differentiation is high.

## Dependencies

- **Upstream**: Position data (P3 positions with thesis_status, attention_state), F-022 (base signal scores)
- **Downstream**: F-026 (ranking uses adjusted scores), F-028 (tests validate portfolio adjustments)
- **Cross-role**: system-architect defines the adjustment algorithm; product-manager defines the adjustment ranges and thesis-to-score mapping

## Constraints & Risks

| Constraint | Type | Mitigation |
|------------|------|------------|
| Score range MUST stay within 0.0-1.0 | MUST | Adjustments are clamped after application |
| Portfolio data unavailability | MUST | Missing position data = no portfolio adjustment, not failure |
| Thesis status mapping | MUST | Explicit mapping: confirmed < monitoring < speculative for boost magnitude |
| Attention state mapping | MUST | Explicit mapping: high > normal > low for adjustment |

## Product Considerations

The thesis_status mapping is counterintuitive but deliberate: speculative positions get the HIGHEST boost because they require the most active monitoring. A position you are unsure about deserves more attention than one you are confident in. This is the "squeaky wheel" principle applied to portfolio management.

The non-portfolio entry guarantee (at least 3 entries when available) prevents the watchlist from becoming a portfolio review tool. The user should always see fresh opportunities alongside their holdings. This balance is critical for the "discovery" use case.

Attention_state is a user-provided signal. The system SHOULD NOT infer attention_state from data alone -- it reflects the user's subjective assessment of which positions need focus. The UI for setting attention_state is out of scope for P1-2, but the data model MUST support it.
