# F-038: Research Report Summarizer

**Feature ID**: F-038
**Priority**: High
**Related Roles**: system-architect, subject-matter-expert

## Objective

Extract key viewpoints and investment theses from Chinese analyst research reports.

## Scope

- Report structure parsing (title, author, conclusion, key points)
- Investment thesis extraction (bullish/bearish reasoning)
- Target price and rating extraction
- Key risk factor identification

## Data Model

**Input**: TextDocument (research report text)
**Output**: ResearchReportResult (frozen dataclass) containing:
- report_title, analyst_name, institution
- rating: buy/hold/sell/overweight/underweight
- target_price: Optional[float]
- thesis_summary: str (key investment reasoning)
- key_points: tuple[str, ...] (3-5 main points)
- risk_factors: tuple[str, ...]
- sentiment_label: bullish/bearish/neutral

## Technical Requirements

- MUST identify report structure sections (conclusion, key points, risks)
- MUST extract analyst rating and target price when present
- MUST generate concise thesis summary (1-3 sentences)
- MUST implement BaseDetector for P3 integration
- SHOULD handle reports from major brokerages (中信、中金、国泰君安 etc.)

## Integration Points

- NLP Pipeline → EventBuilder → P3 Event Engine
- Sentiment output feeds into sentiment propagation (F-039)

## Acceptance Criteria

1. Extracts rating from 90%+ of structured research reports
2. Generates thesis summary within 50 words
3. Identifies at least 2 key points per report
