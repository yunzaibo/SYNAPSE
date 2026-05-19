# Implementation Plan: P4 Chinese Financial NLP Layer

**Session**: WFS-synapse-p4-nlp
**Date**: 2026-05-19
**Complexity**: High
**Tasks**: 8 (4 waves)
**Estimated Tests**: 112+

---

## Architecture Overview

P4 adds a Chinese financial NLP layer to SYNAPSE, providing structured text understanding capabilities for A-share equity research. The NLP layer lives in `synapse/nlp/` and integrates with the existing P3 event engine via `BaseDetector` ABC.

```
synapse/nlp/
  __init__.py          # Lazy imports
  schemas.py           # TextDocument, NERResult, SentimentResult, etc.
  text_preprocessor.py # Abbreviation expansion, number normalization
  ner_engine.py        # F-041: 5-type entity recognition
  announcement_parser.py # F-037: Financial metric extraction
  sentiment_classifier.py # F-039: Bullish/bearish/neutral
  event_extractor.py   # F-042: Structured event extraction
  report_summarizer.py # F-038: Analyst report summarization
  policy_understander.py # F-040: Regulatory document parsing
  aspect_detector.py   # Aspect-level sentiment detection
  event_patterns.py    # Event trigger patterns
  financial_patterns.py # Financial metric patterns
  report_patterns.py   # Report structure patterns
  policy_patterns.py   # Policy document patterns
  sector_mapper.py     # Sector keyword mapping
  dict/                # Entity dictionaries
    company_dict.py    # A-share company names
    metric_dict.py     # Financial metric abbreviations
    person_patterns.py # Person name patterns
  lexicon/             # Sentiment lexicon
    __init__.py
    sentiment_dict.yaml # 500+ terms
    loader.py          # YAML loader
    scorer.py          # Enhanced lexicon analyzer
    negation.py        # Negation detection
    degree.py          # Degree modifiers

synapse/event/
  nlp_detectors.py     # F-043: 6 BaseDetector implementations
```

---

## Wave 1: Foundation (2 tasks, parallel)

### IMPL-001: Financial NER Engine (F-041)

**Goal**: Recognize 5 entity types (company, person, product, institution, metric) with ticker linking.

**Deliverables**:
- `synapse/nlp/schemas.py`: TextDocument, NERResult, NEREntity frozen dataclasses
- `synapse/nlp/text_preprocessor.py`: Abbreviation expansion (50+ terms), number normalization
- `synapse/nlp/ner_engine.py`: NEREngine with recognize() method
- `synapse/nlp/dict/`: 3 dictionary modules (company, metric, person)
- `tests/unit/test_ner_engine.py`: 18+ tests

**Dependencies**: None (Wave 1 foundation)

**CLI Execution**: `new` — independent task

---

### IMPL-002: Financial Sentiment Lexicon (F-044)

**Goal**: Build 500+ term sentiment dictionary with negation/degree handling.

**Deliverables**:
- `synapse/nlp/lexicon/sentiment_dict.yaml`: 500+ terms across 7 categories
- `synapse/nlp/lexicon/loader.py`: YAML loader with schema validation
- `synapse/nlp/lexicon/scorer.py`: EnhancedLexiconAnalyzer extending social.py
- `synapse/nlp/lexicon/negation.py`: Context window negation detection
- `synapse/nlp/lexicon/degree.py`: 3-level degree modifiers
- `tests/unit/test_sentiment_lexicon.py`: 16+ tests

**Dependencies**: None (Wave 1 foundation)

**CLI Execution**: `new` — independent task

---

## Wave 2: Core NLP (3 tasks, parallel)

### IMPL-003: Financial Announcement Parser (F-037)

**Goal**: Extract 5+ financial metrics from Chinese earnings announcements.

**Deliverables**:
- `synapse/nlp/patterns/financial_patterns.py`: 20+ regex patterns
- `synapse/nlp/announcement_parser.py`: AnnouncementParser with parse() method
- `tests/unit/test_announcement_parser.py`: 14+ tests

**Dependencies**: IMPL-001 (NER Engine), IMPL-002 (Lexicon)

**CLI Execution**: `merge_fork` — depends on IMPL-001 + IMPL-002

---

### IMPL-004: News Sentiment Classifier (F-039)

**Goal**: Classify financial news as bullish/bearish/neutral with aspect-level granularity.

**Deliverables**:
- `synapse/nlp/aspect_detector.py`: 5-aspect detection
- `synapse/nlp/sentiment_classifier.py`: NewsSentimentClassifier with classify()
- `tests/unit/test_sentiment_classifier.py`: 16+ tests

**Dependencies**: IMPL-002 (Lexicon)

**CLI Execution**: `fork` — depends on IMPL-002 (parent has 2 children)

---

### IMPL-005: Event Extraction Engine (F-042)

**Goal**: Extract structured events from unstructured text, map to P3 EventType.

**Deliverables**:
- `synapse/nlp/event_patterns.py`: 30+ trigger patterns for 5 event types
- `synapse/nlp/event_extractor.py`: EventExtractor with extract() method
- `tests/unit/test_event_extractor.py`: 14+ tests

**Dependencies**: IMPL-001 (NER Engine)

**CLI Execution**: `fork` — depends on IMPL-001 (parent has 4 children)

---

## Wave 3: Advanced Analysis (2 tasks, parallel)

### IMPL-006: Research Report Summarizer (F-038)

**Goal**: Extract rating, target price, thesis, and risks from analyst reports.

**Deliverables**:
- `synapse/nlp/report_patterns.py`: 15+ report structure patterns
- `synapse/nlp/report_summarizer.py`: ReportSummarizer with summarize()
- `tests/unit/test_report_summarizer.py`: 12+ tests

**Dependencies**: IMPL-001 (NER Engine), IMPL-004 (Sentiment Classifier)

**CLI Execution**: `merge_fork` — depends on IMPL-001 + IMPL-004

---

### IMPL-007: Policy Document Understander (F-040)

**Goal**: Extract issuing body, effective date, key changes, and sector impact from regulatory documents.

**Deliverables**:
- `synapse/nlp/policy_patterns.py`: Policy document patterns
- `synapse/nlp/sector_mapper.py`: 8+ sector keyword mappings
- `synapse/nlp/policy_understander.py`: PolicyUnderstander with understand()
- `tests/unit/test_policy_understander.py`: 12+ tests

**Dependencies**: IMPL-001 (NER Engine), IMPL-004 (Sentiment Classifier)

**CLI Execution**: `merge_fork` — depends on IMPL-001 + IMPL-004

---

## Wave 4: Integration (1 task)

### IMPL-008: NLP-P3 Event Integration (F-043)

**Goal**: Connect all NLP outputs to P3 event engine via BaseDetector implementations.

**Deliverables**:
- `synapse/event/nlp_detectors.py`: 6 BaseDetector implementations
- `synapse/event/taxonomy.py`: Updated with NLP source types
- `synapse/event/__init__.py`: Updated exports
- `tests/unit/test_nlp_detectors.py`: 20+ unit tests
- `tests/integration/test_nlp_event_pipeline.py`: 5+ integration tests

**Dependencies**: IMPL-003, IMPL-004, IMPL-005, IMPL-006, IMPL-007 (all NLP tasks)

**CLI Execution**: `merge_fork` — depends on 5 parents

---

## Cross-Wave Dependencies

```
Wave 1 (Foundation)
  IMPL-001 (NER) ──────────┬──→ IMPL-003 (Announcement) ──┐
                           ├──→ IMPL-005 (Event Extract) ──┤
                           ├──→ IMPL-006 (Report) ─────────┤
                           └──→ IMPL-007 (Policy) ─────────┤
  IMPL-002 (Lexicon) ─────┬──→ IMPL-003 (Announcement) ──┤
                           └──→ IMPL-004 (Sentiment) ──┬───┤
                                                       ├───┤
Wave 2 (Core NLP)                                     │   │
  IMPL-003 + IMPL-004 + IMPL-005 ────────────────────┤   │
                                                       │   │
Wave 3 (Advanced)                                      │   │
  IMPL-006 + IMPL-007 ───────────────────────────────┘   │
                                                          │
Wave 4 (Integration)                                      │
  IMPL-008 ←──────────────────────────────────────────────┘
```

---

## Quality Standards

- All frozen dataclasses: `frozen=True, slots=True`
- All tests: `py -m pytest -p no:asyncio`
- Graceful degradation: return None on failure, never crash
- Round-trip serialization: `to_dict()` + `from_dict()`
- BaseDetector ABC compliance for all P3 integrations
- Domain-specific: 500+ sentiment terms, 5 entity types, 5 event types

---

## N+1 Context

### Decisions
| Decision | Rationale | Revisit? |
|----------|-----------|----------|
| Dictionary-based NLP (no ML) | MVP simplicity, no GPU dependency | Yes — may add transformers in P5 |
| synapse/nlp/ package (not event/) | Separation of concerns | No |
| YAML lexicon (not Python dict) | User customization without code changes | No |
| 500+ term lexicon | Domain accuracy improvement | Yes — may expand to 1000+ |

### Deferred
- [ ] Transformer model integration (P5)
- [ ] PDF table extraction (P5)
- [ ] Real-time streaming NLP (P5)
- [ ] GPU inference optimization (P5)
