# Task: IMPL-005 Event Extraction Engine

## Implementation Summary

### Files Created
- `synapse/nlp/event_patterns.py`: 33 trigger patterns across 5 event types with regex matching
- `synapse/nlp/event_extractor.py`: EventExtractor class with extract() pipeline and frozen dataclasses
- `tests/unit/test_event_extractor.py`: 33 tests covering all 5 event types, edge cases, serialization

### Content Added

**Event Patterns** (`synapse/nlp/event_patterns.py`):
- `TriggerPattern` frozen dataclass: event_type, pattern, base_confidence, description
- `ALL_TRIGGER_PATTERNS`: 33 patterns (7 earnings, 7 M&A, 7 equity, 6 policy, 6 dividend)
- `EVENT_TYPE_TO_P3`: maps internal event types to P3 EventType strings
- `EVENT_TYPE_KEYWORDS`: fallback keyword sets for each event type
- `count_patterns()` / `count_patterns_by_type()` utility functions

**Event Extractor** (`synapse/nlp/event_extractor.py`):
- `ExtractedEvent` frozen dataclass (7 fields): event_type, trigger_phrase, participants, amount, date, confidence, entity_spans
- `EventExtractionResult` frozen dataclass (2 fields): events tuple, processing_time_ms
- `EventExtractor` class with `extract(doc: TextDocument) -> EventExtractionResult` method
- Pipeline: TextPreprocessor -> NEREngine -> pattern matching -> classification -> detail extraction
- `_extract_amount_from_text()`: monetary amount extraction from Chinese text
- `_extract_date_from_text()`: date extraction (YYYY-MM-DD and YYYY年MM月DD日 formats)
- `_extract_participants()`: NER entity linking near trigger matches
- `get_p3_event_type()`: maps internal type to P3 EventType string
- to_dict()/from_dict() round-trip for both dataclasses

### P3 EventType Mapping
| Internal Type | P3 EventType |
|---------------|--------------|
| EARNINGS_FORECAST | earnings |
| MERGER_ACQUISITION | corporate_action |
| EQUITY_CHANGE | corporate_action |
| POLICY_CHANGE | policy_change |
| DIVIDEND | corporate_action |

### Integration Points
- Uses `NEREngine` from IMPL-001 (`synapse.nlp.ner_engine`) for entity recognition
- Uses `TextPreprocessor` from IMPL-001 (`synapse.nlp.text_preprocessor`) for text normalization
- Uses `TextDocument`, `NEREntity`, `NERResult` from `synapse.nlp.schemas`
- Maps to P3 `EventType` enum values via `EVENT_TYPE_TO_P3` dict

### Usage Examples
```python
from synapse.nlp.schemas import TextDocument
from synapse.nlp.event_extractor import EventExtractor

extractor = EventExtractor()
doc = TextDocument(text="公司预计2026年净利润增长50%，同时公布分红方案。", doc_id="news-001")
result = extractor.extract(doc)

for event in result.events:
    print(f"{event.event_type}: {event.trigger_phrase}")
    # EARNINGS_FORECAST: 预计2026年净利润增长50%
    # DIVIDEND: 分红方案

# Map to P3 EventType
p3_type = EventExtractor.get_p3_event_type(event.event_type)
# "earnings" or "corporate_action"
```

## Status: Complete
