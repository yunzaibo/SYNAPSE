# F-043: NLP-P3 Event Integration

**Feature ID**: F-043
**Priority**: High
**Related Roles**: system-architect, data-architect

## Objective

Connect all NLP outputs to the P3 event engine via BaseDetector implementations.

## Scope

- BaseDetector implementations for each NLP task type
- DetectorRegistry registration
- Event type taxonomy extensions (if needed)
- Confidence scoring and event severity mapping

## Components

### NLP Detectors (synapse/event/nlp_detectors.py)

| Detector | NLP Task | Event Type | Confidence Source |
|----------|----------|------------|-------------------|
| AnnouncementDetector | F-037 | EARNINGS_FORECAST | extraction confidence |
| ResearchReportDetector | F-038 | SOCIAL_SENTIMENT | sentiment confidence |
| NewsSentimentDetector | F-039 | SOCIAL_SENTIMENT | classifier confidence |
| PolicyDetector | F-040 | POLICY_CHANGE | extraction confidence |
| NERDetector | F-041 | (metadata enrichment) | NER confidence |
| EventExtractionDetector | F-042 | (varies) | extraction confidence |

### Registration Pattern

```python
# In synapse/event/registry.py or detector registration module
registry.register("nlp_announcement", AnnouncementDetector)
registry.register("nlp_sentiment", NewsSentimentDetector)
registry.register("nlp_policy", PolicyDetector)
registry.register("nlp_event_extraction", EventExtractionDetector)
```

## Technical Requirements

- MUST implement BaseDetector ABC for all NLP detectors
- MUST register all detectors in DetectorRegistry
- MUST map NLP confidence scores to Event.confidence_score
- MUST handle empty NLP results gracefully (return None from detect())
- MUST NOT block event engine when NLP model is loading
- SHOULD support parallel detection (multiple detectors on same text)

## Integration Points

- BaseDetector (synapse/event/base.py)
- DetectorRegistry (synapse/event/registry.py)
- PropagationGraph (synapse/event/graph.py)
- ImpactAnalyzer (synapse/event/impact.py)
- PropagationLifecycle (synapse/event/lifecycle.py)

## Acceptance Criteria

1. All NLP detectors registered and discoverable via DetectorRegistry
2. NLP events flow through propagation graph correctly
3. Confidence scores propagate to impact analysis
4. No NLP failure causes event engine crash
5. All existing P3 tests continue to pass
