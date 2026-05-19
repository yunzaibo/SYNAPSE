# F-037: Financial Announcement Parser

**Feature ID**: F-037
**Priority**: High
**Related Roles**: system-architect, data-architect, subject-matter-expert

## Objective

Parse Chinese financial announcements (earnings reports, prospectuses, board resolutions) into structured data using NLP pipeline.

## Scope

- Text preprocessing with financial abbreviation expansion
- Structured field extraction (revenue, profit, EPS, key metrics)
- Table structure detection from plain-text announcements
- Integration with P3 event engine via BaseDetector

## Data Model

**Input**: TextDocument (raw announcement text)
**Output**: AnnouncementResult (frozen dataclass) containing:
- Extracted metrics: revenue, net_profit, eps, roe, gross_margin
- Period info: reporting_period, period_type (Q1/Q2/Q3/annual)
- Key phrases: growth_highlights, risk_factors
- NER entities: company, auditor, key_personnel

## Technical Requirements

- MUST use TextPreprocessor for abbreviation expansion before extraction
- MUST handle number format normalization (亿/万 → float)
- MUST preserve approximation markers (约/超/近) as metadata
- MUST implement BaseDetector ABC for P3 integration
- SHOULD use regex patterns for structured field extraction
- MAY use transformer model for complex unstructured sections

## Integration Points

- TextPreprocessor (synapse/nlp/pipeline/)
- EventBuilder → Event schema (synapse/core/schemas/event.py)
- DetectorRegistry (synapse/event/registry.py)
- PropagationGraph (synapse/event/graph.py)

## Acceptance Criteria

1. Can parse a standard A-share earnings announcement text
2. Extracts at least 5 financial metrics with correct values
3. Outputs Event objects that integrate with P3 propagation graph
4. Handles malformed text gracefully (empty result, no exception)
