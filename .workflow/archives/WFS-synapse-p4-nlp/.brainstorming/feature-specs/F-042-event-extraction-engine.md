# F-042: Event Extraction Engine

**Feature ID**: F-042
**Priority**: High
**Related Roles**: system-architect, subject-matter-expert

## Objective

Extract structured events from unstructured Chinese financial text (earnings forecasts, M&A, equity changes).

## Scope

- Event type classification (earnings forecast, M&A, equity change, dividend)
- Event detail extraction (amounts, dates, parties involved)
- Event severity/confidence scoring
- Mapping to P3 EventType taxonomy

## Data Model

**Input**: TextDocument (financial news/announcement text)
**Output**: EventExtractionResult (frozen dataclass) containing:
- events: tuple[ExtractedEvent, ...]
  - event_type: str (maps to P3 EventType)
  - trigger_phrase: str (text span that triggered detection)
  - participants: tuple[str, ...] (entities involved)
  - amount: Optional[float] (monetary value if applicable)
  - date: Optional[date] (event date if mentioned)
  - confidence: float [0.0, 1.0]

## Event Types to Extract

| P3 EventType | Trigger Patterns | Key Fields |
|--------------|-----------------|------------|
| EARNINGS_FORECAST | 预计, 业绩预增, 业绩预亏, 扭亏为盈 | amount_range, direction |
| MERGER_ACQUISITION | 收购, 合并, 并购, 重组 | acquirer, target, price |
| EQUITY_CHANGE | 增持, 减持, 回购, 质押, 解除质押 | holder, shares, percentage |
| POLICY_CHANGE | 发布, 实施, 调整, 修改 | issuing_body, effective_date |
| DIVIDEND | 分红, 派息, 高送转 | amount_per_share, record_date |

## Technical Requirements

- MUST map extracted events to P3 EventType taxonomy
- MUST extract trigger phrases with character offsets
- MUST identify participants (entities involved in the event)
- MUST implement BaseDetector for P3 integration
- SHOULD handle multi-event documents (one text → multiple events)
- SHOULD use pattern matching + ML hybrid approach

## Integration Points

- NER Engine (F-041) provides entity recognition
- EventBuilder maps to Event schema
- PropagationGraph receives new events
- ImpactAnalyzer computes event impact

## Acceptance Criteria

1. Extracts events from 90%+ of earnings forecast announcements
2. Correctly classifies event type for 85%+ of extracted events
3. Handles documents with multiple events (average 2-3 per document)
4. Output events integrate seamlessly with P3 propagation graph
