# Planning Notes: P4 Chinese Financial NLP Layer

**Session**: WFS-synapse-p4-nlp
**Date**: 2026-05-19

## User Intent

- **GOAL**: Build Chinese financial NLP layer for A-share equity research
- **KEY_CONSTRAINTS**:
  - 8 features across 4 execution waves
  - All NLP in synapse/nlp/ package
  - All integration via BaseDetector ABC
  - All frozen dataclasses use frozen=True, slots=True
  - All tests use py -m pytest -p no:asyncio

## Context Findings

- **Existing NLP**: social.py has LexiconAnalyzer with ~100 terms — P4 extends to 500+
- **Event Framework**: BaseDetector ABC + DetectorRegistry — NLP detectors follow this pattern
- **Event Types**: SOCIAL_SENTIMENT already defined in EventType enum
- **Test Pattern**: class-based tests, duck-typed mocks, test_<feature>_<scenario> naming

## Consolidated Constraints

1. NLP module lives in synapse/nlp/ (new package)
2. Integration via synapse/event/nlp_detectors.py
3. All frozen dataclasses MUST use frozen=True, slots=True
4. All tests MUST use py -m pytest -p no:asyncio
5. Graceful degradation: return None on NLP failure, never crash
6. TextPreprocessor must be shared across all NLP tasks
7. NER Engine is prerequisite for F-037, F-042, F-038, F-040
8. Sentiment Lexicon is prerequisite for F-039, F-038
9. No ML model training — use pre-trained or rule-based only
10. YAML-based lexicon for user customization

## Conflict Decisions

- **synapse/nlp/ vs synapse/event/nlp/**: Chose top-level synapse/nlp/ for separation of concerns
- **Dictionary-based vs ML NER**: Chose dictionary for MVP, defer transformers to P5
- **YAML lexicon vs Python dict**: Chose YAML for user customization without code changes

## N+1 Context

### Decisions
| Decision | Rationale | Revisit? |
|----------|-----------|----------|
| Dictionary-based NLP | MVP simplicity, no GPU | Yes — add transformers in P5 |
| synapse/nlp/ package | Clean separation | No |
| YAML lexicon format | User customization | No |
| 500+ term threshold | Domain accuracy | Yes — may expand |

### Deferred
- [ ] Transformer model integration (P5)
- [ ] PDF table extraction (P5)
- [ ] Real-time streaming NLP (P5)
- [ ] GPU inference optimization (P5)
