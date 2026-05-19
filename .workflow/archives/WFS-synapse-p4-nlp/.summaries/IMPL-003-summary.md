# Task: IMPL-003 Financial Announcement Parser

## Implementation Summary

### Files Created
- `synapse/nlp/patterns/__init__.py`: Package init with lazy exports for financial patterns module
- `synapse/nlp/patterns/financial_patterns.py`: 24 regex patterns for financial metric extraction, period detection, and approximation marker handling
- `synapse/nlp/announcement_parser.py`: AnnouncementParser class with 7-stage pipeline, frozen dataclasses (AnnouncementResult, FinancialMetric, PeriodInfo)
- `tests/unit/test_announcement_parser.py`: 33 unit tests covering metric extraction, period detection, approximation markers, edge cases, frozen dataclass, and full pipeline

### Content Added

**NumberPattern** (`synapse/nlp/patterns/financial_patterns.py:48`): Frozen dataclass for compiled regex patterns with metric_name, pattern, aliases fields.

**METRIC_PATTERNS** (`synapse/nlp/patterns/financial_patterns.py:324`): Dict mapping 19 metric names to 24 NumberPattern instances covering:
- Revenue: 4 patterns (营业收入, 营收, 实现营收, 主营业务收入, 销售收入)
- Net profit: 4 patterns (净利润, 归母净利润, 扣非净利润, 实现净利润)
- EPS: 3 patterns (每股收益, 基本每股收益, 扣非每股收益)
- ROE: 3 patterns (净资产收益率, 加权平均ROE, 扣非ROE)
- Gross margin: 4 patterns (毛利率, 净利率, 毛利率变化, 经营利润率)
- Additional: 6 patterns (总资产, 净资产, 经营性现金流, 资产负债率, growth variants)

**PeriodInfo** (`synapse/nlp/announcement_parser.py:64`): Frozen dataclass with slots=True for reporting period (year, period_type, period_label). Fields: year, period_type, period_label.

**FinancialMetric** (`synapse/nlp/announcement_parser.py:97`): Frozen dataclass with slots=True for extracted financial metrics. Fields: name, value, raw_text, confidence, approximation.

**AnnouncementResult** (`synapse/nlp/announcement_parser.py:133`): Frozen dataclass with slots=True, 8 fields: metrics, period_info, growth_highlights, risk_factors, entities, approximation_markers, confidence, processing_time_ms. Supports to_dict()/from_dict() round-trip.

**AnnouncementParser** (`synapse/nlp/announcement_parser.py:260`): Main parser class with 7-stage pipeline:
1. TextPreprocessor.expand_abbreviations
2. Regex metric extraction (24 patterns)
3. Period detection (Q1/Q2/Q3/Q4/annual/semi-annual)
4. NER entity extraction (company/auditor/personnel)
5. Approximation marker preservation
6. Growth/risk sentence extraction
7. Confidence scoring

**detect_period()** (`synapse/nlp/patterns/financial_patterns.py:377`): Detects reporting period from text using 7 compiled regex patterns with pattern-index-based period type mapping.

**extract_approximation_markers()** (`synapse/nlp/patterns/financial_patterns.py:390`): Extracts approximation markers (约/超/近/逾/不足/etc) from text.

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.nlp.announcement_parser import (
    AnnouncementParser,
    AnnouncementResult,
    FinancialMetric,
    PeriodInfo,
)
from synapse.nlp.patterns.financial_patterns import (
    METRIC_PATTERNS,
    ALL_PATTERNS,
    NumberPattern,
    detect_period,
    extract_approximation_markers,
)
```

### Integration Points
- **AnnouncementParser.parse(doc: TextDocument) -> AnnouncementResult**: Main entry point for parsing financial announcements
- **TextPreprocessor**: Used internally for abbreviation expansion and number normalization
- **NEREngine**: Used internally for entity extraction (company, auditor, personnel)
- **Frozen dataclasses**: All result types use frozen=True, slots=True pattern with to_dict()/from_dict() round-trip

### Usage Examples
```python
from synapse.nlp.schemas import TextDocument
from synapse.nlp.announcement_parser import AnnouncementParser

parser = AnnouncementParser()
doc = TextDocument(text="贵州茅台2024年第三季度报告...", doc_id="doc-001")
result = parser.parse(doc)

# Access extracted metrics
for metric in result.metrics:
    print(f"{metric.name}: {metric.value} (approx: {metric.approximation})")

# Access period info
print(result.period_info.period_type)  # "Q3"

# Access confidence
print(result.confidence)  # 0.75
```

## Status: Complete
