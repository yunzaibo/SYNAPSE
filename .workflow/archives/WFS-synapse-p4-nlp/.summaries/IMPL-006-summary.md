# Task: IMPL-006 Research Report Summarizer

## Implementation Summary

### Files Created
- `synapse/nlp/report_patterns.py`: 18 structure patterns for Chinese analyst research reports
- `synapse/nlp/report_summarizer.py`: ReportSummarizer class with ResearchReportResult dataclass
- `tests/unit/test_report_summarizer.py`: 33 unit tests covering all functionality

### Files Modified
- `synapse/nlp/__init__.py`: Added lazy exports for ResearchReportResult, ReportSummarizer, ReportRating

### Content Added

**ReportRating** (`synapse/nlp/report_patterns.py:32`): Enum with 5 rating types: buy, hold, sell, overweight, underweight

**RATING_KEYWORDS** (`synapse/nlp/report_patterns.py:42`): 16 Chinese-to-English rating keyword mappings covering major brokerages

**StructurePattern** (`synapse/nlp/report_patterns.py:62`): Frozen dataclass for regex pattern definitions with priority

**TITLE_PATTERNS** (`synapse/nlp/report_patterns.py:82`): 3 patterns for report header detection (standard, brokerage, simple)

**AUTHOR_PATTERNS** (`synapse/nlp/report_patterns.py:110`): 2 patterns for analyst name extraction (role prefix, certificate number)

**INSTITUTION_PATTERNS** (`synapse/nlp/report_patterns.py:130`): 2 patterns for brokerage/institution name extraction

**RATING_PATTERNS** (`synapse/nlp/report_patterns.py:186`): 3 patterns for rating extraction (explicit, inline, contextual)

**TARGET_PRICE_PATTERNS** (`synapse/nlp/report_patterns.py:222`): 2 patterns for target price extraction (single value, range)

**SECTION_MARKERS** (`synapse/nlp/report_patterns.py:248`): 7 section markers (conclusion, key_points, risks, investment_highlights, valuation, company_overview, financial_summary)

**BULLET_PATTERNS** (`synapse/nlp/report_patterns.py:308`): 4 patterns for bullet/list item extraction

**RISK_SENTENCE_PATTERN** (`synapse/nlp/report_patterns.py:319`): Fallback pattern for risk sentence detection

**ResearchReportResult** (`synapse/nlp/report_summarizer.py:53`): Frozen dataclass with 8 fields: report_title, analyst_name, institution, rating, target_price, thesis_summary, key_points, risk_factors. Supports to_dict()/from_dict() round-trip.

**ReportSummarizer** (`synapse/nlp/report_summarizer.py:125`): Main class with summarize(text: TextDocument) -> ResearchReportResult pipeline:
1. Title extraction via title patterns
2. Analyst/institution extraction via NER fallback
3. Rating extraction via rating patterns + keyword lookup
4. Target price extraction via price patterns
5. Thesis summary generation from conclusion section (extractive, within 50 words)
6. Key points extraction from bullet/numbered lists
7. Risk factor identification from risk section

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.nlp.report_patterns import ReportRating, RATING_KEYWORDS, SECTION_MARKERS
from synapse.nlp.report_summarizer import ResearchReportResult, ReportSummarizer
```

### Integration Points
- **ReportSummarizer.summarize()**: Accepts TextDocument, returns ResearchReportResult
- **ResearchReportResult.to_dict()**: Serialize for JSON storage
- **ResearchReportResult.from_dict()**: Deserialize from storage
- **NEREngine**: Used internally for analyst/institution entity recognition

### Usage Examples
```python
from synapse.nlp.schemas import TextDocument
from synapse.nlp.report_summarizer import ReportSummarizer

summarizer = ReportSummarizer()
doc = TextDocument(text="中信证券深度研究报告\n投资评级：买入\n目标价：50元\n...")
result = summarizer.summarize(doc)
print(result.rating)           # ReportRating.BUY
print(result.target_price)     # 50.0
print(result.key_points)       # ('point 1', 'point 2', ...)
print(result.risk_factors)     # ('risk 1', 'risk 2', ...)
```

## Test Results
- 33 tests pass: `py -m pytest tests/unit/test_report_summarizer.py -p no:asyncio -q`
- Pattern count: 18 structure patterns + 7 section markers = 25 total
- All 5 rating types covered: buy, hold, sell, overweight, underweight

## Status: Complete
