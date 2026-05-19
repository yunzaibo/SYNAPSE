# System Architect Analysis: P4 Chinese Financial NLP Layer

## Architecture Assessment

### System Vision

P4 adds a Chinese financial NLP layer on top of P3's event-driven framework. The system processes unstructured Chinese financial text (earnings reports, research reports, news, policy documents) through a modular pipeline and produces structured Event objects that integrate with the existing PropagationGraph, ImpactAnalyzer, and PropagationLifecycle.

The NLP layer MUST NOT be a standalone system. It operates as a set of pluggable detectors registered into the existing DetectorRegistry, consuming raw text and producing Events that flow through the same propagation/decay/impact pipeline as all other P3 event types.

### Key Architecture Principles

**Principle 1: Pipeline Modularity Over Monolith**
Each NLP task (sentiment, NER, event extraction, summarization) MUST be an independent pipeline stage with well-defined inputs/outputs. Stages MUST be composable -- a single document MAY flow through multiple pipelines. No pipeline stage MUST depend on another stage's internal state.

**Principle 2: Lazy Model Loading as First-Class Concern**
Chinese financial NLP models (BERT-based) consume 500MB-2GB each. The system SHOULD load models on first use and cache them for session lifetime. All detectors MUST be instantiatable without triggering model loads. Model loading MUST happen inside `detect()` or a dedicated `ensure_loaded()` method, never in `__init__()`.

**Principle 3: Graceful Degradation Over Failure**
The NLP pipeline MUST never raise exceptions to the event engine. When a model fails to load, text is unparseable, or processing exceeds time limits, the detector MUST return an empty result with a logged warning. Downstream components MUST receive empty results, not crashes.

**Principle 4: Taxonomy Alignment First**
All NLP-extracted events MUST map to existing P3 EventType values (earnings, policy_change, social_sentiment, corporate_action) or extend the taxonomy via a controlled update process. The system MUST NOT introduce ad-hoc event types outside the taxonomy.

### Data Flow

```
Raw Text Input (from P5 data pipeline)
        |
        v
+------------------+
| Text Preprocessor|  -- Jieba segmentation, abbreviation expansion,
|                  |     number normalization, encoding cleanup
+------------------+
        |
        v
+------------------+
| NLP Task Router  |  -- Routes to appropriate pipeline(s) based on
|                  |     document type / request type
+------------------+
        |
   +----+----+----+----+
   |    |    |    |    |
   v    v    v    v    v
[NER] [Sentiment] [EventExtract] [Summarize] [PolicyParse]
   |    |    |    |    |
   v    v    v    v    v
+------------------+
| Event Builder    |  -- Maps NLP output to Event schema,
|                  |     sets EventType, confidence, severity
+------------------+
        |
        v
+------------------+
| BaseDetector     |  -- detect() returns Event or None
| Implementation   |     confidence_score() returns [0.0, 1.0]
+------------------+
        |
        v
  DetectorRegistry  -->  PropagationGraph  -->  ImpactAnalyzer
```

## System Components & Design

### Core Components

**1. NLP Pipeline (`synapse/nlp/pipeline/`)**

The pipeline is a sequential chain of stage functions. Each stage transforms text or intermediate representations.

```
TextPreprocessor -> FeatureExtractor -> TaskInference -> EventBuilder
```

Stages:
- **TextPreprocessor**: Jieba segmentation with custom financial dictionary, abbreviation expansion (营收 -> 营业收入), number format normalization (亿/万 -> float), encoding cleanup (UTF-8/GBK detection)
- **FeatureExtractor**: Tokenization, POS tagging, dependency parsing. Produces intermediate `NLPCanvas` dataclass.
- **TaskInference**: Model-specific inference. One implementation per task type (SentimentInference, NERInference, EventExtractionInference, etc.)
- **EventBuilder**: Converts inference results to Event objects with proper EventType mapping

**2. Model Manager (`synapse/nlp/models/`)**

Centralized model lifecycle management with lazy loading, caching, and version tracking.

**3. Lexicon Store (`synapse/nlp/lexicon/`)**

Domain-specific financial lexicons. Extends existing `LexiconAnalyzer` in `social.py` with 500+ financial terms, entity dictionaries, and event trigger patterns.

**4. NLP Detectors (`synapse/event/nlp_detectors.py`)**

Concrete BaseDetector implementations that bridge NLP pipeline outputs to the P3 event engine.

### Component Responsibilities

| Component | Responsibility | Interface |
|-----------|---------------|-----------|
| NLP Pipeline | Orchestrate text processing stages | `Pipeline.process(text, tasks) -> NLPCanvas` |
| Model Manager | Load/cache/version NLP models | `ModelManager.get(name) -> Model` |
| Lexicon Store | Provide domain dictionaries | `LexiconStore.get(name) -> Lexicon` |
| NLP Detectors | Bridge NLP to P3 event engine | `BaseDetector.detect(data) -> Event` |
| Text Preprocessor | Clean and normalize Chinese text | `Preprocessor.process(text) -> str` |

### Integration Layer: P3 Event Engine

**BaseDetector Pattern Compliance**

Every NLP detector MUST implement three methods:
- `detect(data: dict) -> Optional[Event]`: Core detection logic. Data dict MUST contain a `text` key with raw Chinese text. Detector runs NLP pipeline internally and returns Event or None.
- `event_type() -> str`: Returns taxonomy-aligned event type string.
- `confidence_score(data: dict) -> float`: Returns NLP model confidence in [0.0, 1.0].

**Registry Registration**

NLP detectors MUST register via `DetectorRegistry.register()`. The registry MUST be extended with a `detect_text()` convenience method that accepts text-specific data dicts:

```python
# Proposed extension to DetectorRegistry
def detect_text(self, text: str, metadata: dict | None = None) -> list[Event]:
    """Run all registered detectors against text input."""
    data = {"text": text}
    if metadata:
        data.update(metadata)
    return self.detect_all(data)
```

**Propagation Integration**

NLP-produced Events participate in the same lifecycle:
1. Event enters `PropagationGraph` as DETECTED node
2. Graph traversal propagates to related tickers/sectors
3. `ImpactAnalyzer` computes impact = severity * confidence * decay_factor * path_weight
4. `PropagationLifecycle` manages state transitions (DETECTED -> PROPAGATING -> SETTLED -> EXPIRED)
5. Category-specific decay applied via `CATEGORY_HALF_LIVES` (social_sentiment: 0.5 days, policy_change: 2.5 days, earnings: 6.5 days)

**Event Type Mapping**

| NLP Task | Output | Maps to EventType | Maps to Source |
|----------|--------|-------------------|----------------|
| Sentiment Classification | bullish/bearish/neutral | `social_sentiment` | `EventSourceType.NEWS` |
| Financial Announcement | structured financial data | `earnings` | `EventSourceType.DATA_FEED` |
| Research Report | viewpoints + recommendations | `earnings` | `EventSourceType.AI_DETECTED` |
| Policy Document | regulatory changes | `policy_change` | `EventSourceType.NEWS` |
| NER | entity mentions | (metadata enrichment) | N/A |
| Event Extraction | structured event | type-dependent | `EventSourceType.AI_DETECTED` |

## Data Model

### Entity 1: NLPCanvas

Intermediate representation flowing through the pipeline. Produced by TextPreprocessor, consumed by TaskInference.

```
NLPCanvas
---------
document_id: str          # Unique document identifier (UUID)
raw_text: str             # Original text (preserved for re-processing)
normalized_text: str      # Preprocessed text (segmented, cleaned)
segments: list[str]       # Jieba-segmented tokens
entities: list[NPCEntity] # Pre-extracted entities (from NER stage)
metadata: dict            # Source, timestamp, document_type, ticker
created_at: datetime      # Pipeline entry timestamp
```

**Constraints**: document_id MUST be unique. raw_text MUST be preserved unchanged. normalized_text MUST be UTF-8 encoded.

### Entity 2: NPCEntity

Typed entity span extracted by NER pipeline.

```
NPCEntity
---------
surface_form: str         # Text span (e.g., "贵州茅台")
entity_type: str          # COMPANY | PERSON | PRODUCT | INSTITUTION | POSITION
confidence: float         # [0.0, 1.0]
start_offset: int         # Character offset in normalized_text
end_offset: int           # Character offset in normalized_text
linked_ticker: str | None # Resolved ticker (e.g., "600519.SH") if available
```

**Constraints**: entity_type MUST be one of the five defined types. confidence MUST be in [0.0, 1.0]. linked_ticker MAY be None if disambiguation fails.

### Entity 3: SentimentResult

Sentiment classification output with aspect-level granularity.

```
SentimentResult
---------------
document_id: str          # Links to NLPCanvas
label: str                # bullish | bearish | neutral
confidence: float         # [0.0, 1.0]
score: float              # Continuous score [-1.0, 1.0]
aspects: list[AspectSentiment]  # Optional per-aspect sentiment
model_version: str        # Model identifier for versioning
```

**Constraints**: label MUST be one of the three values. score MUST be in [-1.0, 1.0]. aspects MUST be empty list if aspect-level analysis is not performed.

### Entity 4: EventExtractionResult

Structured event extracted from unstructured text.

```
EventExtractionResult
----------------------
document_id: str          # Links to NLPCanvas
event_template: str       # e.g., "earnings_forecast", "ma_deal", "equity_change"
trigger_phrase: str       # Text span that triggered event detection
arguments: dict           # Template-specific structured fields
confidence: float         # [0.0, 1.0]
model_version: str
```

**Constraints**: event_template MUST map to a P3 EventType via the taxonomy. arguments MUST contain at minimum a `date` field when available.

### Entity 5: NLPModelMetadata

Tracks loaded model state for versioning and health checks.

```
NLPModelMetadata
----------------
model_name: str           # e.g., "finbert-zh", "ner-financial"
model_version: str        # Semantic version
loaded_at: datetime       # When model was loaded into memory
memory_usage_mb: float    # Approximate memory footprint
last_used_at: datetime    # Last inference timestamp
inference_count: int      # Total inferences since load
avg_latency_ms: float     # Rolling average inference time
```

**Constraints**: model_version MUST follow semver. memory_usage_mb MUST be > 0 when loaded.

### Entity Relationships

```
NLPCanvas (1) --has-many--> NPCEntity
NLPCanvas (1) --has-one---> SentimentResult
NLPCanvas (1) --has-many--> EventExtractionResult
NLPCanvas (1) --identified-by-> document_id
EventExtractionResult --maps-to--> EventType (taxonomy)
NPCEntity --may-link-to--> ticker (external reference)
NLPModelMetadata --tracks--> Model (loaded instance)
```

## State Machine: NLP Model Lifecycle

```
                    +-----------+
                    | UNLOADED  |
                    +-----+-----+
                          |
                   ensure_loaded()
                          |
                          v
                    +-----------+
                    | LOADING   |  <-- model download / deserialization
                    +-----+-----+
                          |
              +-----------+-----------+
              |                       |
         load success            load failure
              |                       |
              v                       v
        +-----------+          +-----------+
        |  LOADED   |          |  FAILED   |
        +-----+-----+          +-----+-----+
              |                       |
         eviction /             retry on next
         explicit unload        ensure_loaded()
              |                       |
              v                       v
        +-----------+          back to UNLOADED
        | UNLOADED  |
        +-----------+
```

### Transition Table

| From | To | Trigger | Guard | Action |
|------|----|---------|-------|--------|
| UNLOADED | LOADING | `ensure_loaded()` called | model_name valid | Allocate download/inference thread |
| LOADING | LOADED | Model bytes received & deserialized | No exception | Update NLPModelMetadata, log load time |
| LOADING | FAILED | Exception during load | 3 consecutive failures | Log error, emit metric |
| LOADING | UNLOADED | Timeout (>120s) | Load cancelled | Release partial resources |
| LOADED | UNLOADED | Memory pressure / explicit unload | `inference_count == 0` in last 30min | Free model memory, update metadata |
| FAILED | UNLOADED | Retry cooldown (5min) | No active inference | Clear error state |
| FAILED | LOADING | `ensure_loaded()` after cooldown | Cooldown expired | Re-attempt load |

**Self-correction**: The FAILED -> LOADING transition enforces a minimum 5-minute cooldown between retry attempts to prevent retry storms. The FAILED state MUST NOT persist beyond 1 retry cycle -- if the second attempt fails, the model remains UNLOADED and the detector returns empty results permanently until explicit reload.

## Error Handling Strategy

### Error Classification

| Category | Examples | Severity | Recovery |
|----------|----------|----------|----------|
| ModelLoadError | Download failure, OOM, corrupt file | HIGH | Retry with backoff, fall back to lexicon-only |
| TextProcessingError | Encoding error, empty text, too long | LOW | Skip document, log, continue |
| InferenceError | CUDA error, shape mismatch, timeout | MEDIUM | Unload model, return empty |
| TaxonomyError | Unknown event type, mapping failure | MEDIUM | Map to closest type, log warning |
| RegistryError | Duplicate registration, missing detector | HIGH | Reject registration, log error |

### Recovery Mechanisms

**ModelLoadError Recovery**:
1. First failure: retry after 30s exponential backoff (30s, 60s, 120s)
2. After 3 retries: mark model as FAILED, log structured error
3. Detector returns empty result (Event with confidence=0.0) -- no exception propagates
4. Next `ensure_loaded()` attempt enforces 5-minute cooldown

**TextProcessingError Recovery**:
1. Empty text: return empty result immediately (confidence=0.0)
2. Encoding error: attempt GBK -> UTF-8 fallback, then skip if still fails
3. Text too long (>100K chars): truncate to 50K chars with warning log

**InferenceError Recovery**:
1. Model unload on inference exception (to force clean reload)
2. Return empty result for this document
3. Log error with document_id for debugging
4. Continue processing next document in batch

### Graceful Degradation Contract

The NLP layer MUST uphold this contract at all times:

```
For any input (valid or invalid):
  -> detector.detect(data) returns Event | None
  -> detector.confidence_score(data) returns float [0.0, 1.0]
  -> No exceptions escape to the caller
  -> At minimum, a WARNING-level log entry is written
```

When the entire NLP pipeline is unavailable (all models failed):
- Detectors MUST still be registered in DetectorRegistry
- `detect()` MUST return None (not raise)
- `confidence_score()` MUST return 0.0
- A health check endpoint MUST report degraded status

## Observability Requirements

### Metrics (minimum 8)

1. **nlp_pipeline_latency_ms**: Histogram of end-to-end pipeline latency per document (P50, P95, P99)
2. **nlp_model_load_duration_seconds**: Gauge tracking time to load each model (per model_name)
3. **nlp_model_memory_usage_bytes**: Gauge of current memory consumed by loaded models
4. **nlp_inference_count**: Counter of total inferences (labels: model_name, task_type, success/failure)
5. **nlp_event_detection_count**: Counter of Events produced (labels: event_type, detector_name)
6. **nlp_text_length_histogram**: Distribution of input text lengths (to detect outliers)
7. **nlp_model_retry_count**: Counter of model load retries (labels: model_name, attempt_number)
8. **nlp_degradation_events**: Counter of graceful degradation occurrences (labels: category, detector_name)

### Log Events

| Event | Level | When | Key Fields |
|-------|-------|------|------------|
| model_loaded | INFO | Model successfully loaded | model_name, version, latency_ms, memory_mb |
| model_load_failed | ERROR | Model load failed after retries | model_name, error, attempt_count |
| pipeline_complete | INFO | Document processed | document_id, task_types, latency_ms, events_produced |
| pipeline_degraded | WARNING | Fallback to degraded mode | reason, detector_name |
| text_skipped | WARNING | Document skipped (empty/invalid) | document_id, reason |
| taxonomy_mapped | DEBUG | NLP output mapped to EventType | source_task, target_event_type |

### Health Checks

| Check | Condition | Status |
|-------|-----------|--------|
| model_availability | At least 1 model loaded | healthy / degraded |
| pipeline_throughput | > 10 docs/min processed | healthy / warning |
| memory_pressure | Total model memory < 4GB | healthy / critical |
| registry_integrity | All registered detectors instantiatable | healthy / error |

## Configuration Model

### NLP Pipeline Configuration

```yaml
nlp:
  pipeline:
    max_text_length: 100000        # chars, documents exceeding this are truncated
    segmentation_engine: jieba      # jieba | pkuseg | none
    custom_dictionary: assets/dicts/financial_jieba.txt
    encoding_fallback: gbk         # fallback when UTF-8 decode fails
    timeout_seconds: 30            # per-document pipeline timeout

  models:
    sentiment:
      name: finbert-zh
      version: "1.0.0"
      path: models/finbert-zh/     # local path or HF hub ID
      lazy_load: true              # load on first inference
      max_batch_size: 32
      device: cpu                   # cpu | cuda | auto

    ner:
      name: ner-financial-zh
      version: "1.0.0"
      path: models/ner-financial-zh/
      lazy_load: true
      max_batch_size: 16

    event_extraction:
      name: event-extraction-zh
      version: "1.0.0"
      path: models/event-extraction-zh/
      lazy_load: true
      max_batch_size: 8

    summarization:
      name: summarization-zh
      version: "1.0.0"
      path: models/summarization-zh/
      lazy_load: true
      max_batch_size: 4

  lexicon:
    positive_terms: assets/lexicon/positive_financial.txt
    negative_terms: assets/lexicon/negative_financial.txt
    entity_dictionary: assets/lexicon/entity_dict.txt
    min_term_count: 500            # minimum terms for domain lexicon

  degradation:
    max_retries: 3
    retry_backoff_seconds: [30, 60, 120]
    model_cooldown_seconds: 300    # 5 min between retry cycles
    empty_result_on_failure: true  # never raise, return empty

  registry:
    auto_register: true            # register all NLP detectors on startup
    detect_text_method: true       # add detect_text() convenience method
```

### Configuration Validation Rules

| Parameter | Type | Range | Default | Validation |
|-----------|------|-------|---------|------------|
| max_text_length | int | 1000-1000000 | 100000 | MUST be > 0 |
| timeout_seconds | int | 5-300 | 30 | MUST be > 0 |
| max_batch_size | int | 1-128 | 32 | MUST be > 0 |
| lazy_load | bool | - | true | MUST be set explicitly |
| device | str | cpu/cuda/auto | cpu | MUST be valid option |
| max_retries | int | 0-10 | 3 | MUST be >= 0 |
| retry_backoff_seconds | list | - | [30,60,120] | MUST be non-decreasing |
| model_cooldown_seconds | int | 60-3600 | 300 | MUST be >= 60 |

## Boundary Scenarios

### 1. Empty Text Input

**Scenario**: Detector receives `data = {"text": ""}` or `data = {"text": None}`.

**Behavior**: Pipeline returns immediately with empty result. No model inference triggered.

```python
def detect(self, data: dict) -> Optional[Event]:
    text = data.get("text", "")
    if not text or not isinstance(text, str):
        return None  # Empty result, no exception
```

**Contract**: `detect()` returns None. `confidence_score()` returns 0.0. One WARNING log emitted.

### 2. Encoding Issues

**Scenario**: Input text contains mixed UTF-8/GBK encoding, or contains null bytes.

**Behavior**: TextPreprocessor attempts UTF-8 decode, falls back to GBK, then latin-1. Null bytes stripped. If all fail, text replaced with empty string and WARNING logged.

**MUST NOT**: Crash on encoding errors. Silently replace garbled characters with replacement character (?) and log.

### 3. Model Load Failure (OOM)

**Scenario**: System has insufficient memory to load a 2GB Chinese BERT model.

**Behavior**:
1. ModelManager catches MemoryError during load
2. Retries with 30s backoff (up to 3 attempts)
3. After 3 failures, model marked as FAILED
4. All detectors using this model return None
5. CRITICAL-level log emitted
6. Health check reports degraded status

### 4. Concurrent Model Loading

**Scenario**: Two threads call `ensure_loaded()` for the same model simultaneously.

**Behavior**: ModelManager MUST use a per-model threading.Lock. First thread loads; second thread waits on lock, then finds model already loaded (no double-load). Lock MUST NOT be held during network I/O -- use a loading state flag instead.

```python
class ModelManager:
    def __init__(self):
        self._locks: dict[str, threading.Lock] = {}
        self._loading: dict[str, bool] = {}

    def ensure_loaded(self, model_name: str) -> Model:
        if model_name in self._loaded_models:
            return self._loaded_models[model_name]

        lock = self._locks.setdefault(model_name, threading.Lock())
        with lock:
            # Double-check after acquiring lock
            if model_name in self._loaded_models:
                return self._loaded_models[model_name]
            if self._loading.get(model_name):
                # Another thread is loading -- wait and retry
                pass
            self._loading[model_name] = True
            try:
                model = self._load_model(model_name)
                self._loaded_models[model_name] = model
                return model
            finally:
                self._loading[model_name] = False
```

### 5. Batch Processing Memory Pressure

**Scenario**: Processing 1000 documents in batch, each producing NER + sentiment results.

**Behavior**:
- Pipeline processes documents in configurable batch sizes (default 32)
- Results are written to Parquet after each batch, not accumulated in memory
- Peak memory = model_size + batch_size * avg_document_size
- If memory exceeds 4GB threshold, batch_size auto-reduces by 50%

### 6. Model Version Mismatch

**Scenario**: Config references model version "1.2.0" but only "1.1.0" is cached locally.

**Behavior**: ModelManager MUST check version before returning cached model. If mismatch, triggers fresh download/load. Old version evicted after new version loads successfully. WARNING log emitted about version mismatch.

### 7. Taxonomy Extension Required

**Scenario**: NLP extracts an event type not in current taxonomy (e.g., "share_pledge").

**Behavior**:
1. EventBuilder maps to closest existing EventType (e.g., `corporate_action`)
2. Original NLP event template preserved in Event.description
3. WARNING log: "Event template 'share_pledge' mapped to 'corporate_action' -- consider taxonomy extension"
4. No crash, no data loss

### 8. Rapid Detector Registration/Deregistration

**Scenario**: Hot-reload scenario where NLP detectors are updated at runtime.

**Behavior**: DetectorRegistry MUST use a threading.RLock for register/unregister operations. `detect_all()` MUST take a snapshot of detectors at call start, so mid-call registration changes do not affect the current detection pass. This prevents partial-result inconsistency.

## Technical Feasibility Analysis

### Complexity Assessment

| Component | Complexity | Risk | Mitigation |
|-----------|-----------|------|------------|
| Text Preprocessor | LOW | Jieba dictionary coverage | Ship with 500+ financial terms |
| Model Manager | MEDIUM | Concurrent loading, memory mgmt | Thread-safe lazy loading pattern |
| Sentiment Pipeline | LOW | Lexicon already exists in social.py | Extend existing LexiconAnalyzer |
| NER Pipeline | MEDIUM | Entity disambiguation | Fuzzy ticker matching |
| Event Extraction | HIGH | Template coverage | Start with 3 templates, iterate |
| P3 Integration | LOW | BaseDetector pattern well-established | Follow existing detector pattern |
| Summarization | MEDIUM | Chinese summarization quality | Use pre-trained model, validate |

### Resource Implications

**Memory**: 500MB-2GB per loaded model. With lazy loading, peak = 1 active model (~500MB) + pipeline overhead (~100MB). Total system memory requirement: 2GB minimum, 4GB recommended.

**CPU**: CPU inference is acceptable per guidance spec. Estimated throughput: 10-50 documents/minute depending on model and text length. Batch processing with `max_batch_size` tuning.

**Storage**: Model files (~2GB total for 4 models) + lexicon files (~5MB) + processed results in Parquet (~2x raw text size).

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Model download blocked in China | MEDIUM | HIGH | Mirror models to domestic CDN, support local paths |
| Jieba segmentation errors on financial terms | MEDIUM | MEDIUM | Custom dictionary, continuous term harvesting |
| NER disambiguation false positives | HIGH | MEDIUM | Confidence thresholding, ticker database matching |
| Event extraction template gaps | HIGH | MEDIUM | Fallback to sentiment-only, iterate templates |
| Memory pressure on small instances | LOW | HIGH | Lazy loading + auto-reduction |

## Quality and Performance Framework

### Non-Functional Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Pipeline latency (P95) | < 5 seconds per document | Histogram metric |
| Model load time | < 30 seconds | Load duration metric |
| Throughput | > 10 docs/min | Counter metric |
| Memory per model | < 2GB | Memory gauge |
| Availability | 99.5% (degraded OK) | Health check |
| Graceful degradation | 100% of failures | Error handling contract |

### Testing Strategy

**Unit Tests**: Each pipeline stage tested independently with fixture texts (empty, short, long, encoded, financial jargon).

**Integration Tests**: End-to-end pipeline with mock models. Verify Event output schema compliance.

**Performance Tests**: Batch processing throughput, memory usage under load, model load time benchmarks.

## Configuration Model: Cross-Cutting

### NLP-Specific Configuration Parameters

All NLP configuration MUST be defined in a single `nlp` section of the project config. The configuration MUST support:

1. **Per-model paths**: Local filesystem or HuggingFace hub ID
2. **Device selection**: Per-model CPU/GPU assignment
3. **Batch size tuning**: Per-task configurable batch sizes
4. **Timeout controls**: Per-document and per-batch timeouts
5. **Degradation policy**: Retry counts, backoff schedules, cooldown periods

### Configuration Validation

On startup, the system MUST validate all NLP configuration:
- Model paths exist or are valid HF hub IDs
- Batch sizes are within [1, 128]
- Timeout values are within [5, 300] seconds
- Device strings are valid ("cpu", "cuda", "auto")
- Retry backoff arrays are non-decreasing

Invalid configuration MUST cause a startup error (not runtime failure).

## Recommendations

### Recommended Architecture

**Phase 1 (MVP)**: Implement sentiment pipeline + NER pipeline + P3 integration. These three components provide immediate value: sentiment signals flow into social_sentiment events, NER enriches existing events with entity data.

**Phase 2**: Add event extraction with 3 core templates (earnings_forecast, ma_deal, equity_change). Extend taxonomy as needed.

**Phase 3**: Add financial announcement parser and policy document understander. These require more complex template coverage.

### Technology Stack Recommendations

| Component | Recommendation | Rationale |
|-----------|---------------|-----------|
| Segmentation | jieba + custom dict | Proven for Chinese, fast, extensible |
| Sentiment Model | FinBERT-zh or ERNIE-Fin | Domain-specific pre-training |
| NER Model | RoBERTa-zh-ner-finance | Financial entity recognition |
| Event Extraction | UIE (Unified Information Extraction) | Template-flexible extraction |
| Storage | Parquet (via pandas/pyarrow) | Consistent with P2, columnar efficiency |
| Model Hub | HuggingFace with local cache | Version control + offline support |

### Key Architectural Decisions

1. **Pipeline as composition, not inheritance**: Use function composition for pipeline stages, not class inheritance. This keeps stages testable and replaceable.

2. **Model Manager as singleton**: One ModelManager per process, shared across all detectors. Prevents duplicate model loading.

3. **Lexicon as configuration, not code**: Financial lexicons MUST be stored in external files (CSV/TXT), not hardcoded. This enables domain experts to update terms without code changes.

4. **Event type mapping table**: A single `NLP_EVENT_MAP` dictionary mapping NLP task outputs to P3 EventTypes. Centralizes the mapping logic and makes taxonomy extension a configuration change.

## Cross-Feature Dependencies

| Feature | Depends On | Provides To |
|---------|-----------|-------------|
| F-037 (announcement parser) | F-041 (NER), F-042 (event extraction) | Structured financial data to Event engine |
| F-038 (report summarizer) | F-041 (NER) | Key viewpoints as Event descriptions |
| F-039 (news sentiment) | F-044 (lexicon), F-041 (NER) | Sentiment signals to social_sentiment events |
| F-040 (policy understander) | F-041 (NER), F-042 (event extraction) | Policy events to policy_change events |
| F-041 (NER engine) | (standalone) | Entity enrichment for all other features |
| F-042 (event extraction) | F-041 (NER) | Structured events to Event engine |
| F-043 (P3 integration) | All NLP features | BaseDetector bridge to PropagationGraph |
| F-044 (sentiment lexicon) | (standalone) | Domain terms for F-039 and LexiconAnalyzer |

**Critical path**: F-041 (NER) -> F-042 (event extraction) -> F-043 (P3 integration). These three MUST be implemented first to establish the NLP-to-Event pipeline.

## Appendix: Decision Tracking

| Decision ID | Question | Selected | Rationale |
|-------------|----------|----------|-----------|
| SA-P4-001 | Pipeline architecture | Function composition | Testability, replaceability |
| SA-P4-002 | Model loading strategy | Lazy + singleton manager | Memory optimization |
| SA-P4-003 | Error handling contract | Return empty, never raise | Research workflow stability |
| SA-P4-004 | P3 integration pattern | BaseDetector + Registry | Framework consistency |
| SA-P4-005 | Lexicon storage | External files | Domain expert editable |
| SA-P4-006 | Event type mapping | Centralized NLP_EVENT_MAP | Taxonomy extension as config |
| SA-P4-007 | Concurrency model | Per-model lock + snapshot | Thread-safe without contention |
| SA-P4-008 | Storage format | Parquet for results | P2 consistency, query efficiency |
