# F-040: Policy Document Understander

**Feature ID**: F-040
**Priority**: Medium
**Related Roles**: subject-matter-expert, data-architect

## Objective

Extract structured metadata from Chinese regulatory documents (PBOC, CSRC, State Council).

## Scope

- Document type classification (monetary policy, regulatory rule, guidance)
- Issuing body identification
- Effective date extraction
- Key regulatory change identification
- Affected sector mapping

## Data Model

**Input**: TextDocument (policy document text)
**Output**: PolicyResult (frozen dataclass) containing:
- issuing_body: str (央行/证监会/国务院/etc.)
- document_type: str (货币政策/监管规则/指导意见/etc.)
- effective_date: Optional[date]
- key_changes: tuple[str, ...] (main regulatory changes)
- affected_sectors: tuple[str, ...] (sector names affected)
- sentiment_impact: bullish/bearish/neutral per sector

## Technical Requirements

- MUST identify issuing body from document header/signature
- MUST extract effective date (生效日期/自X日起施行)
- MUST map policy changes to affected sectors
- MUST implement BaseDetector for P3 integration (POLICY_CHANGE event type)
- SHOULD handle policy documents in both simplified Chinese and mixed Chinese-English

## Domain Requirements

- PBOC documents: interest rate changes, RRR adjustments, open market operations
- CSRC documents: IPO rules, listing requirements, enforcement actions
- State Council documents: macro policy guidance, industry plans

## Integration Points

- EventBuilder → POLICY_CHANGE event type
- Sector impact analysis via ImpactAnalyzer
- Cross-event correlation with market events

## Acceptance Criteria

1. Correctly identifies issuing body for 95%+ of policy documents
2. Extracts at least 1 key regulatory change per document
3. Maps changes to affected sectors with >80% accuracy
