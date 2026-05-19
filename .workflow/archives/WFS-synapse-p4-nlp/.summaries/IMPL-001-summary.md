# Task: IMPL-001 Financial NER Engine

## Implementation Summary

### Files Modified
- `synapse/nlp/__init__.py`: NLP module init with lazy imports for all components
- `synapse/nlp/schemas.py`: TextDocument, NEREntity, NERResult frozen dataclasses (frozen=True, slots=True)
- `synapse/nlp/text_preprocessor.py`: TextPreprocessor with 50+ abbreviation expansions, number normalization (亿/万), approximation markers
- `synapse/nlp/dict/__init__.py`: Dictionary package init
- `synapse/nlp/dict/company_dict.py`: 100+ A-share company names with ticker mapping
- `synapse/nlp/dict/metric_dict.py`: 50+ financial metric aliases
- `synapse/nlp/dict/person_patterns.py`: Person suffix/prefix patterns, institution patterns, product patterns
- `synapse/nlp/ner_engine.py`: NEREngine class with 5 entity type recognizers and fuzzy ticker linking
- `tests/unit/test_ner_engine.py`: 39 tests covering all entity types, edge cases, frozen dataclass behavior

### Content Added

**NEREntity** (`synapse/nlp/schemas.py:40`):
- surface_form: str, entity_type: str, start_offset: int, end_offset: int
- confidence: float [0.0, 1.0], linked_ticker: Optional[str], normalized_name: Optional[str]
- frozen=True, slots=True, to_dict()/from_dict() round-trip

**TextDocument** (`synapse/nlp/schemas.py:13`):
- text: str, doc_id: str, source_type: str, metadata: dict
- frozen=True, slots=True, to_dict()/from_dict() round-trip

**NERResult** (`synapse/nlp/schemas.py:68`):
- doc_id: str, entities: tuple[NEREntity, ...], processing_time_ms: float
- frozen=True, slots=True, to_dict()/from_dict() round-trip

**TextPreprocessor** (`synapse/nlp/text_preprocessor.py:130`):
- abbreviations: dict (50+ financial term expansions)
- expand_abbreviations(text) -> str
- normalize_numbers(text) -> tuple[str, dict] (亿/万/千/百 to float)
- extract_approximation_markers(text) -> list[str]
- preprocess(text) -> PreprocessedText (full pipeline)

**NEREngine** (`synapse/nlp/ner_engine.py:41`):
- recognize(doc: TextDocument) -> NERResult
- _recognize_companies(text) -> list[NEREntity]
- _recognize_metrics(text) -> list[NEREntity]
- _recognize_persons(text) -> list[NEREntity]
- _recognize_institutions(text) -> list[NEREntity]
- _recognize_products(text) -> list[NEREntity]
- _link_tickers(entities) -> list[NEREntity] (difflib.SequenceMatcher fuzzy matching)
- _deduplicate_entities(entities) -> list[NEREntity]

**COMPANY_NAMES** (`synapse/nlp/dict/company_dict.py:11`):
- 100+ A-share company names mapping to tickers (e.g. "贵州茅台" -> "600519.SH")
- Includes full names, abbreviations, and stock names

**METRIC_ALIASES** (`synapse/nlp/dict/metric_dict.py:11`):
- 50+ financial metric aliases (e.g. "ROE" -> "净资产收益率")

**PERSON_SUFFIXES** (`synapse/nlp/dict/person_patterns.py:17`):
- 40+ role-based suffixes (分析师, 董事长, CEO, etc.)
- Forward patterns: name + suffix (e.g. "张三分析师")
- Reverse patterns: suffix + name (e.g. "分析师张三")

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.nlp import NEREngine, TextDocument, NERResult, NEREntity
from synapse.nlp.text_preprocessor import TextPreprocessor, PreprocessedText
from synapse.nlp.dict.company_dict import COMPANY_NAMES, get_ticker
from synapse.nlp.dict.metric_dict import METRIC_ALIASES, get_standard_name
from synapse.nlp.dict.person_patterns import INSTITUTION_PATTERNS, PRODUCT_PATTERNS
```

### Integration Points
- **NEREngine.recognize()**: Core entry point -- pass TextDocument, get NERResult with entities
- **NEREntity.linked_ticker**: Company entities linked to stock tickers for downstream correlation
- **NEREntity.normalized_name**: Metric entities have standard names for aggregation
- **TextPreprocessor.preprocess()**: Preprocess text before NER for abbreviation expansion

### Usage Examples
```python
from synapse.nlp import NEREngine, TextDocument

engine = NEREngine()
doc = TextDocument(text="贵州茅台ROE为15%，张三分析师认为值得买入", doc_id="doc-1")
result = engine.recognize(doc)

for entity in result.entities:
    print(f"{entity.surface_form} ({entity.entity_type}) -> {entity.linked_ticker}")
# 贵州茅台 (company) -> 600519.SH
# ROE (metric) -> 净资产收益率
# 张三 (person) -> None
```

## Status: Complete
