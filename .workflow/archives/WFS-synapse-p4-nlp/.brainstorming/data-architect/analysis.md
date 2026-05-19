# Data Architect Analysis: P4 Chinese Financial NLP Layer

## Role Perspective Overview

The data architect perspective focuses on data modeling, storage strategy, schema evolution, and integration with existing SYNAPSE schemas for the P4 Chinese Financial NLP layer. The analysis establishes a consistent data foundation that enables NLP outputs to participate in the P3 event engine while preserving raw text for model evolution and A/B comparison.

All data models follow SYNAPSE conventions: frozen dataclasses for immutable results, `to_dict()`/`from_dict()` serialization, and schema_version field for lazy upcast compatibility.

---

## 1. NLP Data Models

### 1.1 TextDocument — Raw Input Entity

TextDocument is the root entity for all NLP processing. Per guidance-specification decision D-043, raw text and NLP results MUST be stored as separate entities linked via `document_id`.

```python
@dataclass(frozen=True, slots=True)
class TextDocument:
    """Raw text document ingested for NLP processing.

    Attributes:
        document_id: Unique identifier (auto-generated UUID if empty).
        content: Raw text content (Chinese financial text).
        source_type: Document origin (announcement, news, research_report, policy).
        source_url: Original URL or file path (optional).
        ticker: Related stock ticker, empty if cross-company document.
        published_at: When the document was originally published.
        ingested_at: When the document entered the system.
        language: Text language code, always "zh-CN" for P4.
        doc_metadata: Extensible metadata dict (announcement_type, sector, etc.).
        schema_version: Data schema version for lazy upcast.
    """

    document_id: str = ""
    content: str = ""
    source_type: str = ""  # "announcement" | "news" | "research_report" | "policy"
    source_url: str = ""
    ticker: str = ""
    published_at: Optional[datetime] = None
    ingested_at: Optional[datetime] = None
    language: str = "zh-CN"
    doc_metadata: dict = field(default_factory=dict)
    schema_version: str = "1.0"
```

**Design rationale**: TextDocument is deliberately NOT a BaseSchema subclass. It represents ingested data, not a research object. It carries its own minimal fields (`document_id`, `schema_version`) for persistence without inheriting the full BaseSchema lifecycle (status, market_context, creator_type). This avoids forcing research object semantics onto raw input data.

### 1.2 NERResult — Named Entity Recognition Output

Per guidance-specification decision D-044, financial entities MUST be represented as typed spans with surface_form, entity_type, confidence, and optional linked_ticker.

```python
@dataclass(frozen=True, slots=True)
class NEREntity:
    """A single named entity extracted from text.

    Attributes:
        surface_form: The exact text span as it appears in the source.
        entity_type: Entity category (company, person, product, institution, event, metric).
        start_offset: Character offset where entity begins in source text.
        end_offset: Character offset where entity ends (exclusive).
        confidence: Model confidence in [0.0, 1.0].
        linked_ticker: Resolved stock ticker for company entities (None if unresolvable).
        normalized_name: Canonical form (e.g., "贵州茅台" -> "贵州茅台酒股份有限公司").
        entity_id: Stable entity ID for cross-document linking.
    """

    surface_form: str = ""
    entity_type: str = ""  # "company" | "person" | "product" | "institution" | "event" | "metric"
    start_offset: int = 0
    end_offset: int = 0
    confidence: float = 0.0
    linked_ticker: Optional[str] = None
    normalized_name: Optional[str] = None
    entity_id: Optional[str] = None


@dataclass(frozen=True, slots=True)
class NERResult:
    """NER analysis output for a single document.

    Attributes:
        document_id: Source document reference.
        model_id: Which NLP model produced this result.
        model_version: Model version string.
        entities: Tuple of extracted entities (immutable).
        processing_time_ms: Inference time in milliseconds.
        created_at: When this result was generated.
        schema_version: Data schema version.
    """

    document_id: str = ""
    model_id: str = ""
    model_version: str = ""
    entities: tuple[NEREntity, ...] = ()
    processing_time_ms: float = 0.0
    created_at: Optional[datetime] = None
    schema_version: str = "1.0"
```

### 1.3 SentimentResult — Sentiment Analysis Output

Per guidance-specification decision D-045, sentiment results MUST include label, confidence score, and optional aspect-level sentiment.

```python
@dataclass(frozen=True, slots=True)
class AspectSentiment:
    """Sentiment for a specific aspect of the text.

    Attributes:
        aspect: Aspect category (e.g., "revenue", "risk", "management", "guidance").
        label: Sentiment label for this aspect (bullish, bearish, neutral).
        confidence: Confidence in [0.0, 1.0].
    """

    aspect: str = ""
    label: str = ""  # "bullish" | "bearish" | "neutral"
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class SentimentResult:
    """Sentiment analysis output for a single document.

    Attributes:
        document_id: Source document reference.
        model_id: Which NLP model produced this result.
        model_version: Model version string.
        label: Overall sentiment (bullish, bearish, neutral).
        confidence: Overall confidence in [0.0, 1.0].
        score: Continuous sentiment score in [-1.0, 1.0] (bearish to bullish).
        aspect_sentiments: Tuple of per-aspect sentiment breakdowns.
        processing_time_ms: Inference time in milliseconds.
        created_at: When this result was generated.
        schema_version: Data schema version.
    """

    document_id: str = ""
    model_id: str = ""
    model_version: str = ""
    label: str = ""  # "bullish" | "bearish" | "neutral"
    confidence: float = 0.0
    score: float = 0.0
    aspect_sentiments: tuple[AspectSentiment, ...] = ()
    processing_time_ms: float = 0.0
    created_at: Optional[datetime] = None
    schema_version: str = "1.0"
```

### 1.4 EventExtractionResult — Structured Event Extraction

```python
@dataclass(frozen=True, slots=True)
class ExtractedEvent:
    """A structured event extracted from unstructured text.

    Attributes:
        event_type: Maps to P3 EventType taxonomy (earnings, merger_acquisition, equity_change, policy_change, etc.).
        title: Short event title.
        description: Full event description.
        event_date: When the event occurs or occurred.
        related_tickers: Tickers affected by this event.
        confidence: Extraction confidence in [0.0, 1.0].
        severity: Event severity in [0.0, 1.0].
        evidence_spans: Character offsets in source text supporting this extraction.
        structured_fields: Task-specific extracted fields (e.g., {"eps_forecast": 2.5, "period": "Q1"}).
    """

    event_type: str = ""
    title: str = ""
    description: str = ""
    event_date: Optional[date] = None
    related_tickers: tuple[str, ...] = ()
    confidence: float = 0.0
    severity: float = 0.5
    evidence_spans: tuple[tuple[int, int], ...] = ()
    structured_fields: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EventExtractionResult:
    """Event extraction output for a single document.

    Attributes:
        document_id: Source document reference.
        model_id: Which NLP model produced this result.
        model_version: Model version string.
        events: Tuple of extracted events (immutable).
        processing_time_ms: Inference time in milliseconds.
        created_at: When this result was generated.
        schema_version: Data schema version.
    """

    document_id: str = ""
    model_id: str = ""
    model_version: str = ""
    events: tuple[ExtractedEvent, ...] = ()
    processing_time_ms: float = 0.0
    created_at: Optional[datetime] = None
    schema_version: str = "1.0"
```

### 1.5 Model Provenance

```python
@dataclass(frozen=True, slots=True)
class ModelProvenance:
    """Records which model and version produced an NLP result.

    Attributes:
        model_id: Unique model identifier (e.g., "chinese-bert-ner-v1").
        model_type: Model architecture (e.g., "bert", "lexicon", "ensemble").
        model_version: Semantic version string.
        model_path: File path or registry key for model loading.
        loaded_at: When the model was loaded into memory.
        config_hash: Hash of model configuration for reproducibility.
    """

    model_id: str = ""
    model_type: str = ""
    model_version: str = ""
    model_path: str = ""
    loaded_at: Optional[datetime] = None
    config_hash: str = ""
```

---

## 2. Storage Strategy

### 2.1 Parquet-Based Persistence

Following the P2 backtest persistence pattern (decision D-046), NLP results SHOULD use Parquet format. The directory layout mirrors the established convention:

```
nlp_results/
  documents/
    {source_type}/{YYYY-MM-DD}/{document_id}.parquet    # Raw text documents
  ner/
    {model_version}/{YYYY-MM}/{document_id}.parquet     # NER results
  sentiment/
    {model_version}/{YYYY-MM}/{document_id}.parquet     # Sentiment results
  events/
    {model_version}/{YYYY-MM}/{document_id}.parquet     # Event extraction results
```

**Design rationale for `{model_version}` partitioning**: This enables A/B comparison of model outputs on the same documents. When a model is upgraded, new results are written under the new version partition, and old results remain queryable under the old partition.

### 2.2 Schema Versioning in Parquet Metadata

Each Parquet file MUST embed `schema_version` in its metadata, consistent with the backtest persistence pattern:

```python
def save_nlp_result(
    result: NERResult | SentimentResult | EventExtractionResult,
    base_dir: Path,
) -> None:
    """Persist an NLP result to Parquet with schema version metadata."""
    meta = {"schema_version": result.schema_version}
    # ... flatten result to DataFrame row ...
    _write_parquet_with_metadata(df, path, meta)
```

The `_write_parquet_with_metadata` helper from `synapse/backtest/persistence.py` SHOULD be extracted into a shared utility module for reuse by both backtest and NLP persistence layers.

### 2.3 Storage Format Constraints

| Entity | Format | Partitioning | Compression |
|--------|--------|-------------|-------------|
| TextDocument | Parquet | source_type/YYYY-MM-DD | snappy |
| NERResult | Parquet | model_version/YYYY-MM | snappy |
| SentimentResult | Parquet | model_version/YYYY-MM | snappy |
| EventExtractionResult | Parquet | model_version/YYYY-MM | snappy |
| Lexicon entries | CSV/JSONL | — | none |

**Rationale**: Snappy compression is consistent with the existing backtest persistence layer and provides good compression ratio with fast decompression for analytical queries.

### 2.4 Backward Compatibility

The lazy upcast pattern from `synapse/backtest/persistence.py` MUST be applied:

```python
def _lazy_upcast_nlp(row: dict, file_schema_version: str) -> dict:
    """Apply lazy upcast for older NLP schema versions."""
    if file_schema_version < "1.1":
        row.setdefault("model_id", "unknown")
        row.setdefault("model_version", "0.0")
    return row
```

New fields added in future schema versions MUST always have sensible defaults so that older Parquet files can be read without migration scripts.

---

## 3. Text Processing Pipeline Data Flow

### 3.1 Pipeline Stages

The data flow follows a linear pipeline consistent with the modular staged architecture (decision D-039):

```
Raw Text Input
    |
    v
[Stage 1: Ingestion]  -->  TextDocument (persisted)
    |
    v
[Stage 2: Preprocessing]  -->  PreprocessedText (in-memory only)
    |  - Chinese segmentation (jieba with custom dictionary)
    |  - Abbreviation expansion (营收 -> 营业收入)
    |  - Number format normalization (亿/万 -> numeric)
    |  - Encoding normalization (GB2312/GBK -> UTF-8)
    |
    v
[Stage 3: Feature Extraction]  -->  TextFeatures (in-memory only)
    |  - Token embeddings (BERT tokenizer)
    |  - POS tags
    |  - Dependency parse
    |  - Financial term features
    |
    v
[Stage 4: Task-Specific Inference]  -->  NERResult / SentimentResult / EventExtractionResult (persisted)
    |  - NER: span classification
    |  - Sentiment: document/aspect classification
    |  - Event extraction: structured field extraction
    |
    v
[Stage 5: Result Integration]  -->  Event (P3 Event schema)
    |  - Map to EventType taxonomy
    |  - Register via DetectorRegistry
    |  - Link to source document
```

### 3.2 Intermediate Data Models

```python
@dataclass
class PreprocessedText:
    """Intermediate representation after text preprocessing.

    NOT persisted — transient pipeline state only.
    """
    document_id: str = ""
    normalized_text: str = ""
    tokens: list[str] = field(default_factory=list)
    abbreviation_map: dict[str, str] = field(default_factory=dict)
    number_normalizations: list[tuple[int, int, float]] = field(default_factory=list)


@dataclass
class TextFeatures:
    """Intermediate representation after feature extraction.

    NOT persisted — transient pipeline state only.
    """
    document_id: str = ""
    token_ids: list[int] = field(default_factory=list)
    attention_mask: list[int] = field(default_factory=list)
    pos_tags: list[str] = field(default_factory=list)
    financial_terms: list[str] = field(default_factory=list)
```

### 3.3 Batch Processing Data Flow

For batch processing (the primary P4 use case per guidance-specification non-goals), the pipeline processes documents in configurable batches:

```
Batch[TextDocument] --> Batch[PreprocessedText] --> Batch[TextFeatures] --> Batch[NLPResult]
```

Each stage MUST be independently testable and replaceable. The pipeline interface:

```python
class PipelineStage(ABC):
    """Abstract interface for pipeline stages."""

    @abstractmethod
    def process_batch(self, inputs: list) -> list:
        """Process a batch of inputs and return corresponding outputs."""
        ...
```

---

## 4. Entity Resolution & Disambiguation

### 4.1 Company Name Resolution

Chinese company names present unique disambiguation challenges:
- Multiple names for the same entity: "贵州茅台", "茅台", "600519"
- Abbreviated forms: "中石化" vs "中国石油化工股份有限公司"
- Parent/subsidiary ambiguity

**Resolution Strategy**:

```
Surface Form (NER output)
    |
    v
[Exact Match Lookup]  -->  ticker (if found in canonical database)
    |
    v (miss)
[Fuzzy Match (edit distance + embedding similarity)]  -->  ticker (if confidence > threshold)
    |
    v (miss)
[Context-Based Resolution]  -->  ticker (if surrounding text contains ticker)
    |
    v (miss)
[Manual Review Queue]  -->  unresolved entity (flagged for human review)
```

### 4.2 Entity Resolution Data Model

```python
@dataclass(frozen=True, slots=True)
class EntityResolution:
    """Maps an NER surface form to a canonical entity.

    Attributes:
        surface_form: Original text span from NER.
        canonical_name: Resolved canonical company/person name.
        entity_type: Entity type (company, person, etc.).
        linked_ticker: Stock ticker if applicable.
        resolution_method: How this resolution was achieved (exact, fuzzy, context, manual).
        confidence: Resolution confidence in [0.0, 1.0].
        aliases: Known aliases for this entity.
    """

    surface_form: str = ""
    canonical_name: str = ""
    entity_type: str = ""
    linked_ticker: Optional[str] = None
    resolution_method: str = ""  # "exact" | "fuzzy" | "context" | "manual"
    confidence: float = 0.0
    aliases: tuple[str, ...] = ()
```

### 4.3 Ticker Database

The system MUST maintain a canonical ticker database for A-share companies. This database SHOULD be loaded from a reliable source (e.g., akshare, Wind) and refreshed periodically:

```python
@dataclass
class TickerDatabase:
    """Canonical mapping from company names to tickers.

    Attributes:
        name_to_ticker: Mapping company name variants to ticker.
        ticker_to_name: Reverse mapping from ticker to canonical name.
        ticker_to_sector: Mapping from ticker to sector classification.
        last_refreshed: When the database was last updated.
    """
    name_to_ticker: dict[str, str] = field(default_factory=dict)
    ticker_to_name: dict[str, str] = field(default_factory=dict)
    ticker_to_sector: dict[str, str] = field(default_factory=dict)
    last_refreshed: Optional[datetime] = None
```

### 4.4 Person Entity Resolution

Person entities are harder to disambiguate. The system SHOULD:
- Link person names to known roles (CEO, CFO, analyst) when context provides role information
- Track person-to-company associations from announcement metadata
- Flag ambiguous person names for manual resolution

---

## 5. Schema Evolution Strategy

### 5.1 Principles

The schema evolution strategy follows the SYNAPSE "Weak Schema + Lazy Upcast" pattern (ADR-005, as documented in `synapse/core/schemas/base.py`):

1. **No global migration scripts** — each reader is responsible for upcasting
2. **New fields MUST always have defaults** — older data reads without error
3. **Schema version is per-entity, not global** — TextDocument, NERResult, SentimentResult each have independent version tracks
4. **Write always uses latest schema** — new writes produce latest format
5. **Read auto-upcasts** — older formats are silently upgraded at load time

### 5.2 Adding New NLP Task Types

To add a new NLP task type (e.g., "relation extraction") without breaking existing code:

1. **Define a new result dataclass** (e.g., `RelationExtractionResult`) with `schema_version: str = "1.0"`
2. **Register a new detector** implementing `BaseDetector` for the new event type
3. **Add to EventType enum** if the extraction maps to a new event category
4. **Create a new Parquet partition** under `nlp_results/relations/`
5. **No changes to existing result classes** — the new type is additive

This is safe because:
- Existing Parquet files are untouched
- Existing pipeline stages are unaffected (new stage is appended, not inserted)
- The DetectorRegistry accepts new registrations without modifying existing ones

### 5.3 Adding Fields to Existing Results

When adding a new field to an existing result (e.g., adding `key_phrases` to `SentimentResult`):

1. Add the field with a default value (`key_phrases: tuple[str, ...] = ()`)
2. Bump `schema_version` from "1.0" to "1.1"
3. Update `from_dict()` to handle missing keys via `.get()` with defaults
4. Update the lazy upcast function to set the default for older versions

```python
# In SentimentResult:
key_phrases: tuple[str, ...] = ()  # Added in schema 1.1

# In from_dict():
key_phrases=tuple(data.get("key_phrases", []))
```

### 5.4 Breaking Changes Protocol

Breaking changes (removing or renaming fields) MUST follow this protocol:

1. **Deprecation period**: Old field remains with a deprecation warning for at least 2 minor versions
2. **Dual-write**: Both old and new field names are written during the deprecation period
3. **Removal**: Old field is removed only after the deprecation period expires

This ensures that any Parquet file written within the deprecation window remains readable.

---

## 6. Data Lineage & Provenance

### 6.1 Provenance Tracking Requirement

Every NLP result MUST record which model/version produced it. This enables:
- Reproducibility: re-running the same model on the same document should produce equivalent results
- Debugging: when results seem wrong, trace back to the specific model version
- A/B comparison: compare outputs from different model versions on the same document

### 6.2 Provenance Fields

Every result class (`NERResult`, `SentimentResult`, `EventExtractionResult`) MUST include:

| Field | Type | Description |
|-------|------|-------------|
| `model_id` | str | Model identifier (e.g., "chinese-bert-ner") |
| `model_version` | str | Semantic version (e.g., "1.2.0") |
| `document_id` | str | Link back to source TextDocument |
| `created_at` | datetime | When this result was generated |
| `processing_time_ms` | float | Inference time for performance tracking |

### 6.3 Lineage Query Pattern

```python
def query_lineage(
    base_dir: Path,
    document_id: str,
    result_type: str = "ner",
) -> list[dict]:
    """Query all NLP results for a document, ordered by model version.

    Returns list of {model_id, model_version, created_at, result_path}
    for A/B comparison of different model outputs.
    """
    ...
```

### 6.4 Lexicon Provenance

For lexicon-based analysis (decision D-048), the system MUST also track:
- Lexicon version (which term list was used)
- Term additions/removals between versions
- Lexicon file hash for reproducibility

---

## 7. Integration with Existing Schemas

### 7.1 Event Schema Extension

NLP results integrate with the P3 event engine via `BaseDetector.detect()` returning an `Event` object. The integration points:

| NLP Result | EventType Mapping | Event Source |
|-----------|-------------------|--------------|
| NERResult | (no direct Event — entities are attributes) | — |
| SentimentResult | SOCIAL_SENTIMENT or SENTIMENT | AI_DETECTED |
| EventExtractionResult | EARNINGS, CORPORATE_ACTION, POLICY_CHANGE, etc. | AI_DETECTED |

**Key integration code path**:
```
NLPResult -> NLPDetector.detect(data) -> Event -> DetectorRegistry -> EventEngine
```

### 7.2 SocialMediaSignal Bridge

The existing `SocialMediaSignal` schema (`synapse/event/social.py`) uses a simple `sentiment_score: float` field. The new `SentimentResult` is richer (label + confidence + aspects). The bridge between them:

```python
def sentiment_result_to_signal(result: SentimentResult, platform: str, ticker: str) -> SocialMediaSignal:
    """Convert a SentimentResult to a SocialMediaSignal for backward compatibility."""
    return SocialMediaSignal(
        platform=platform,
        ticker=ticker,
        content="",  # Content not carried in SocialMediaSignal
        sentiment_score=result.score,  # Maps to [-1.0, 1.0] range
    )
```

This ensures that NLP-enriched sentiment can flow into existing social sentiment aggregation without modifying the SocialMediaSignal schema.

### 7.3 WatchlistEntry Integration

NLP outputs SHOULD feed into WatchlistEntry via the event engine:
- NLP-detected events propagate through the event graph
- Events with high severity/confidence trigger WatchlistEntry creation
- The `linked_event_id` field in WatchlistEntry traces back to the NLP-derived Event

### 7.4 Decision Schema Integration

Decision records reference events via `event_trigger_id` and `event_influence_score`. NLP-derived events participate identically to data-feed events — there is no schema difference. The `source` field on Event distinguishes AI_DETECTED from DATA_FEED for auditing purposes.

### 7.5 Shared Persistence Utilities

The `_write_parquet_with_metadata` and `_read_parquet_metadata` helpers from `synapse/backtest/persistence.py` SHOULD be extracted into a shared `synapse/core/persistence.py` module. Both backtest and NLP persistence layers depend on the same Parquet I/O pattern.

---

## Cross-Cutting Concerns

### Error Handling

Per guidance-specification (decision D-042), NLP pipeline MUST gracefully degrade:
- Model loading failure: return empty result, log warning, continue pipeline
- Unparseable text: return empty result for that document, continue batch
- Entity resolution failure: leave `linked_ticker` as None, flag for review
- Parquet write failure: log error, continue (result is in-memory and queryable until process exit)

### Concurrency

NLP results are written per-document with no cross-document dependencies. Multiple pipeline workers MAY write concurrently to different document partitions without locking. The Parquet partition layout (by model_version/YYYY-MM) prevents write conflicts.

### Scalability Considerations

- **Document volume**: A-share market produces ~500 announcements/day, ~2000 news articles/day. At this scale, Parquet with snappy compression stores ~50MB/day of NLP results.
- **Model loading**: Lazy loading (decision D-041) keeps memory at ~500MB per active model. Multiple models MAY be loaded simultaneously for pipeline stages that need both NER and sentiment.
- **Query performance**: Parquet columnar format supports efficient aggregation queries (e.g., "average sentiment for ticker X over last 30 days") in <100ms for 30-day windows.

---

## Key Recommendations

1. **Extract shared Parquet I/O utilities** from `synapse/backtest/persistence.py` into `synapse/core/persistence.py` before implementing NLP persistence. This avoids code duplication and ensures consistent metadata handling.

2. **Design TextDocument as a standalone entity** (not BaseSchema subclass). Raw input data has different lifecycle semantics than research objects. Forcing BaseSchema inheritance would require meaningless fields (status, market_context) on every ingested document.

3. **Implement entity resolution as a separate service** rather than embedding it in the NER pipeline. This allows the ticker database to be refreshed independently and enables reuse by other subsystems (e.g., manual watchlist entry validation).

4. **Use `{model_version}` partitioning** in Parquet storage paths. This is critical for A/B model comparison and enables clean model rollback by simply pointing queries at the old partition.

5. **Track processing_time_ms on every result**. This provides baseline performance metrics for model selection and enables alerting when inference time degrades unexpectedly.

---

## Feature Point Index

| Feature | Analysis Focus | Key Data Decisions |
|---------|---------------|-------------------|
| F-037 financial-announcement-parser | TextDocument + EventExtractionResult + NERResult | Structured fields extraction from filings |
| F-038 research-report-summarizer | TextDocument + SentimentResult + aspect_sentiments | Key viewpoint extraction, aspect-level analysis |
| F-039 news-sentiment-classifier | TextDocument + SentimentResult | Label + confidence + score, integrates with SocialMediaSignal |
| F-040 policy-document-understander | TextDocument + EventExtractionResult + structured_fields | Policy metadata extraction (issuing_body, effective_date) |
| F-041 financial-ner-engine | NERResult + EntityResolution + TickerDatabase | Typed spans with disambiguation |
| F-042 event-extraction-engine | EventExtractionResult + EventType mapping | Maps to P3 taxonomy |
| F-043 nlp-p3-event-integration | BaseDetector implementations + Event bridge | NLP outputs become Events |
| F-044 financial-sentiment-lexicon | LexiconAnalyzer enhancement + ModelProvenance | 500+ terms, versioned lexicon |

---

## Integration Points Summary

| Integration | Source | Target | Pattern |
|------------|--------|--------|---------|
| NLP -> Event Engine | NLPResult | Event (via BaseDetector) | detect() returns Event |
| Sentiment -> Social | SentimentResult | SocialMediaSignal | Bridge conversion function |
| Event -> Watchlist | Event | WatchlistEntry | linked_event_id |
| Event -> Decision | Event | Decision | event_trigger_id |
| Persistence | NLP Parquet | synapse/backtest/persistence.py | Shared Parquet I/O utilities |
| Entity Resolution | NERResult | TickerDatabase | Resolution service |
