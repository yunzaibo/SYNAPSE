# Task: IMPL-007 Policy Document Understander

## Implementation Summary

### Files Modified
- `synapse/nlp/policy_patterns.py`: Issuing body detection, effective date extraction, document type classification, key change extraction
- `synapse/nlp/sector_mapper.py`: SectorMapper with 8+ sector keyword mappings
- `synapse/nlp/policy_understander.py`: PolicyUnderstander pipeline and PolicyResult dataclass
- `tests/unit/test_policy_understander.py`: 30 unit tests

### Content Added

**PolicyResult** (`synapse/nlp/policy_understander.py`):
- Frozen dataclass with slots=True: `issuing_body`, `document_type`, `effective_date`, `key_changes`, `affected_sectors`, `sentiment_impact`, `processing_time_ms`
- `to_dict()` / `from_dict()` round-trip serialization

**PolicyUnderstander** (`synapse/nlp/policy_understander.py`):
- `understand(doc: TextDocument) -> PolicyResult` -- full pipeline:
  1. Issuing body detection (PBOC, CSRC, State_Council)
  2. Document type classification (monetary_policy, regulatory_rule, guidance, enforcement)
  3. Effective date extraction (YYYY-MM-DD or "upon_publish")
  4. Key regulatory change identification
  5. Sector mapping (8+ sectors)
  6. Sentiment impact per sector (bullish/bearish/neutral)

**SectorMapper** (`synapse/nlp/sector_mapper.py`):
- `map_to_sectors(text) -> list[SectorMatch]` -- keyword-based sector identification
- `map_to_sector_names(text) -> tuple[str, ...]` -- convenience method
- 8 sectors: banking, insurance, securities, real_estate, technology, healthcare, energy, consumer

**Policy patterns** (`synapse/nlp/policy_patterns.py`):
- `detect_issuing_body(text) -> IssuingBodyMatch`
- `extract_effective_date(text) -> str | None`
- `classify_document_type(text) -> str`
- `extract_key_changes(text) -> tuple[str, ...]`

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.nlp.policy_understander import PolicyUnderstander, PolicyResult
from synapse.nlp.sector_mapper import SectorMapper, SectorMatch
from synapse.nlp.policy_patterns import (
    detect_issuing_body,
    extract_effective_date,
    classify_document_type,
    extract_key_changes,
    IssuingBodyMatch,
)
```

### Integration Points
- **PolicyUnderstander.understand()**: Accepts `TextDocument`, returns `PolicyResult`
- **SectorMapper.map_to_sectors()**: Accepts text, returns `list[SectorMatch]`
- **EventBuilder**: `PolicyResult` can feed into `POLICY_CHANGE` event type (IMPL-008)

### Usage Examples
```python
from synapse.nlp.schemas import TextDocument
from synapse.nlp.policy_understander import PolicyUnderstander

understander = PolicyUnderstander()
result = understander.understand(TextDocument(
    text="中国人民银行决定自2026年6月1日起下调存款准备金率"
))
assert result.issuing_body == "PBOC"
assert result.effective_date == "2026-06-01"
assert "banking" in result.affected_sectors
```

## Status: Complete
