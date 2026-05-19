# Task: IMPL-008 NLP-P3 Event Integration

## Implementation Summary

### Files Modified
- `synapse/event/nlp_detectors.py`: Created — 6 NLP BaseDetector implementations mapping NLP outputs to P3 Event schema
- `synapse/event/taxonomy.py`: Modified — Added `ner_enrichment` and `event_extraction` event types, NLP source priority, and nlp_enrichment category
- `synapse/event/__init__.py`: Modified — Added lazy imports for all 6 NLP detectors
- `tests/unit/test_nlp_detectors.py`: Created — 58 unit tests for all 6 NLP detectors
- `tests/integration/test_nlp_event_pipeline.py`: Created — 23 integration tests for end-to-end pipeline
- `tests/unit/test_event_detection.py`: Modified — Updated event type count from 9 to 11

### Content Added

**AnnouncementDetector** (`synapse/event/nlp_detectors.py:63`)
- Wraps `AnnouncementParser` (F-037)
- Maps to `EventType.EARNINGS`
- Extracts metrics, period info, entities from financial announcements
- event_type() returns `"earnings"`

**ResearchReportDetector** (`synapse/event/nlp_detectors.py:131`)
- Wraps `ReportSummarizer` (F-038)
- Maps to `EventType.SOCIAL_SENTIMENT`
- Extracts rating, target price, thesis summary from research reports
- event_type() returns `"research_sentiment"`

**NewsSentimentDetector** (`synapse/event/nlp_detectors.py:194`)
- Wraps `NewsSentimentClassifier` (F-039)
- Maps to `EventType.SOCIAL_SENTIMENT`
- Only fires for non-neutral sentiment (bullish/bearish)
- event_type() returns `"social_sentiment"`

**PolicyDetector_NLP** (`synapse/event/nlp_detectors.py:247`)
- Wraps `PolicyUnderstander` (F-040)
- Maps to `EventType.POLICY_CHANGE`
- Extracts issuing body, document type, key changes, affected sectors
- event_type() returns `"policy_change"`

**NERDetector** (`synapse/event/nlp_detectors.py:310`)
- Wraps `NEREngine` (F-041)
- Enriches events with entity metadata (company, person, institution, metric)
- event_type() returns `"ner_enrichment"`

**EventExtractionDetector** (`synapse/event/nlp_detectors.py:365`)
- Wraps `EventExtractor` (F-042)
- Maps extracted event types to P3 EventType strings
- Picks highest-confidence extracted event
- event_type() returns `"event_extraction"`

### Architecture Decisions

1. **Lazy imports**: All NLP modules are imported inside `detect()` methods to avoid circular dependencies between `synapse/nlp/` and `synapse/event/`
2. **Graceful degradation**: Every `detect()` wraps NLP calls in try/except, returning `None` on failure
3. **Unique registry keys**: `ResearchReportDetector` uses `"research_sentiment"` instead of `"social_sentiment"` to avoid collision with `NewsSentimentDetector` in the registry
4. **TextDocument bridge**: `_text_to_doc()` helper converts `data["text"]` strings to `TextDocument` for NLP module compatibility
5. **NLP confidence pass-through**: `detect()` extracts NLP result confidence and passes it to `confidence_score()` for accurate propagation

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.event.nlp_detectors import (
    AnnouncementDetector,
    ResearchReportDetector,
    NewsSentimentDetector,
    PolicyDetector_NLP,
    NERDetector,
    EventExtractionDetector,
)
```

### Integration Points
- **DetectorRegistry**: All 6 detectors register with unique event_type keys
- **PropagationGraph**: NLP events flow through graph as nodes via `event.id`
- **ImpactAnalyzer**: Confidence scores propagate through `Event.confidence` field

### Registration Example
```python
from synapse.event.registry import DetectorRegistry
from synapse.event.nlp_detectors import *

registry = DetectorRegistry()
registry.register(AnnouncementDetector)
registry.register(ResearchReportDetector)
registry.register(NewsSentimentDetector)
registry.register(PolicyDetector_NLP)
registry.register(NERDetector)
registry.register(EventExtractionDetector)

# Run all detectors on NLP text
events = registry.detect_all({"text": "Chinese financial text..."})
```

## Test Results

- **Unit tests**: 58 passed (test_nlp_detectors.py)
- **Integration tests**: 23 passed (test_nlp_event_pipeline.py)
- **Full regression**: 1806 passed, 3 pre-existing failures (unchanged)
- **Zero regressions introduced**

## Status: Complete
