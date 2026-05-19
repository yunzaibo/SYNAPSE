# Synthesis Changelog

**Session**: WFS-synapse-p1-2-watchlist
**Generated**: 2026-05-19T21:50:00+08:00

## Enhancements Applied

- **EP-001**: Scoring Dimension Unification — 统一为 4 维评分模型（signal, event, portfolio, market）
  - Applied to: F-022 (signal-scoring-engine)
  - Source: system-architect + data-architect consensus
  - Impact: F-022 uses 4-dimension model with market context from F-025

- **EP-002**: Weight Validation Strategy Alignment — 统一为 auto-normalize with warning
  - Applied to: F-022 (signal-scoring-engine), F-027 (personalization-config)
  - Source: system-architect + product-manager consensus
  - Impact: Invalid weights auto-normalize with logged warning, not ValueError

- **EP-003**: ScoringConfig YAML Schema Consolidation — 统一为扁平结构
  - Applied to: F-027 (personalization-config)
  - Source: data-architect recommendation
  - Impact: YAML config uses flat structure consistent with existing load_config() pattern

- **EP-004**: Intermediate Data Structure Naming Convention — 统一为 ScoredEntry（单条）和 ScoringResult（批量）
  - Applied to: F-022 (signal-scoring-engine)
  - Source: system-architect + data-architect consensus
  - Impact: Clear semantic distinction between single ticker result and batch result

- **EP-005**: F-027 MVP Scope Clarification — 将 F-027 推迟到迭代 2
  - Applied to: F-027 (personalization-config)
  - Source: product-manager recommendation
  - Impact: F-027 is deferred; F-022-F-026 use hardcoded defaults

- **EP-006**: Frozen Dataclass Applicability Clarification — P1-2 不添加 frozen=True
  - Applied to: F-021 (watchlist-schema-extension)
  - Source: system-architect recommendation
  - Impact: WatchlistEntry remains mutable; immutability deferred to P2+

- **EP-007**: reason Field Length Contract — 仅作为生成建议，不强制 schema 层面约束
  - Applied to: F-021 (watchlist-schema-extension)
  - Source: product-manager + data-architect consensus
  - Impact: reason is plain string at schema level; 10-200 chars enforced by scoring engine

- **EP-008**: Graceful Degradation Return Type — generate_daily() 返回 list[WatchlistEntry]
  - Applied to: F-022 (signal-scoring-engine)
  - Source: product-manager + system-architect consensus
  - Impact: API returns list[WatchlistEntry]; ScoringResult used internally only

## Clarifications Resolved

(None — auto mode skipped clarification questions)

## Conflicts Resolved

- **F-021 / Frozen Dataclass**: Do NOT add frozen=True to WatchlistEntry in P1-2 [SUGGESTED]
  - Resolution: Defer immutability to separate P2+ refactoring task
  - Rationale: Adding frozen=True would break _build_event_entries(), _build_signal_entries(), _build_portfolio_entries()

- **F-022 / Intermediate structure naming**: ScoredEntry（单条）和 ScoringResult（批量） [RESOLVED]
  - Resolution: Unified naming convention adopted
  - Rationale: Clear semantic distinction between single and batch results

- **F-024 / ThesisAttentionMap structure**: dict[str, tuple[ThesisStatus, AttentionState]] [SUGGESTED]
  - Resolution: Adopt data-architect's tuple structure
  - Rationale: Simple lookup structure, consistent with existing patterns

- **F-028 / Test priority**: 保持 Must-priority [SUGGESTED]
  - Resolution: Test priority confirmed as Must
  - Rationale: Scoring correctness directly impacts user trust

## Resolved Conflicts

- **F-022 / Scoring dimensions count**: [RESOLVED] 采用 4 维模型（含 market）
  - Resolution: Adopt 4-dimension model (signal, event, portfolio, market)
  - Rationale: F-025 market-semantics-validation produces scoring signals; market context provides meaningful input (northbound flow, index membership)
  - Impact: F-025 scoring stage has dimension to contribute to

- **F-022 / Default weights values**: [RESOLVED] 采用 system-architect 的 4 维权重
  - Resolution: {signal: 0.35, event: 0.30, portfolio: 0.20, market: 0.15}
  - Rationale: Consistent with 4-dimension model; signal gets highest weight for real-time triggers; market gets lowest as supplementary
  - Impact: Default weights sum to 1.0, consistent with D-022-2

- **F-022 / Weight validation behavior**: [RESOLVED] 采用 auto-normalize with warning
  - Resolution: Auto-normalize when weights != 1.0, log warning
  - Rationale: Satisfies product-manager non-crash requirement; warning log provides visibility into misconfiguration
  - Impact: Invalid weights no longer crash daily generation

- **F-027 / MVP scope inclusion**: [RESOLVED] 将 F-027 推迟到迭代 2
  - Resolution: Defer F-027 to iteration 2
  - Rationale: Product-manager recommends deferral; default weights need 30-day user validation; premature personalization risks config paralysis
  - Impact: Users cannot customize weights until iteration 2; F-022-F-026 use hardcoded defaults

- **F-027 / YAML schema structure**: [RESOLVED] 采用扁平结构
  - Resolution: Flat YAML structure
  - Rationale: Consistent with existing load_config() pattern; simpler parsing
  - Impact: Config parsing aligned with existing patterns

- **F-027 / Weight validation on invalid config**: [RESOLVED] 采用 warning + fallback to defaults
  - Resolution: Warning + fallback to defaults on invalid config
  - Rationale: Satisfies product-manager non-crash requirement; aligned with D-022-3 (auto-normalize with warning)
  - Impact: Invalid configs have graceful degradation

## Feature Spec Summary

| Feature | Spec Path | Words | Sections |
|---------|-----------|-------|----------|
| F-021 | feature-specs/F-021-watchlist-schema-extension.md | ~1800 | 7 |
| F-022 | feature-specs/F-022-signal-scoring-engine.md | ~2400 | 7 |
| F-023 | feature-specs/F-023-event-driven-filtering.md | ~1900 | 7 |
| F-024 | feature-specs/F-024-portfolio-aware-scoring.md | ~2000 | 7 |
| F-025 | feature-specs/F-025-market-semantics-validation.md | ~1900 | 7 |
| F-026 | feature-specs/F-026-ranking-and-filtering.md | ~2000 | 7 |
| F-027 | feature-specs/F-027-personalization-config.md | ~2100 | 7 |
| F-028 | feature-specs/F-028-watchlist-tests.md | ~2200 | 7 |

## Complexity Assessment

| Dimension | Value | Score |
|-----------|-------|-------|
| Feature count | 8 | +2 (High) |
| UNRESOLVED conflicts | 0 | +0 (None) |
| Participating roles | 3 | +1 (Medium) |
| Cross-feature dependencies | 5 | +2 (High) |
| **Total** | | **5** |

**Assessment**: IMPLEMENTATION_READY — All conflicts resolved. Features can proceed to implementation.

## Review Results

**Complexity Score**: 7
**Specs Reviewed**: 8
**Minor Fixes Applied**: 5
**Major Flags Raised**: 2

### Fixes Applied

- **F-026-ranking-and-filtering.md**: Terminology consistency -- changed `config.min_score` to `config.min_priority_score` in requirement text and D-026-3 decision, aligning with F-027 config key name
- **F-026-ranking-and-filtering.md**: Rounding consistency -- changed priority_score rounding from "2 decimal places" to "4 decimal places" in constraint table and acceptance criteria, aligning with F-021 schema contract (`to_dict()` rounds to 4)
- **F-026-ranking-and-filtering.md**: Pipeline clarity -- added note explaining ScoredEntry-to-WatchlistEntry extraction step in pipeline flow, which was implicit but undocumented
- **F-025-market-semantics-validation.md**: Internal contradiction fix -- D-025-2 title said "filtered out entirely" but chosen approach said "score=0.0, not removed." Aligned title, decision text, and constraint table to consistently describe suspension as score=0.0 (retained at bottom, not removed)
- **F-021-watchlist-schema-extension.md**: Added [REVIEW-FLAG] noting that `trigger_type` and `linked_event_id` fields are referenced by F-023/F-024 but not defined in the F-021 schema extension

### Flags Raised

- **F-021-watchlist-schema-extension.md**: [REVIEW-FLAG] Schema gap -- `trigger_type` field is required by F-024 (check `trigger_type != PORTFOLIO_REVIEW`) and F-026 (filter by trigger type), and `linked_event_id` is referenced by F-023 data flow, but neither field is defined in the F-021 schema extension. These fields must be either added to F-021, confirmed as existing WatchlistEntry fields from a prior version, or defined in a separate schema extension. This blocks F-023 and F-024 implementation. [DECISION NEEDED]
- **F-025-market-semantics-validation.md**: [REVIEW-FLAG] Suspension handling semantics -- The original D-025-2 decision title ("filtered out entirely") contradicted the chosen approach ("score=0.0, not removed"). Fixed to consistently describe suspension as scoring penalty (score=0.0) rather than removal. Verified that the chosen approach (retain at bottom) is correct per the trade-off discussion and the at-least-one guarantee in F-026. No further action needed after fix.
