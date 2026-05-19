# F-041: Financial NER Engine

**Feature ID**: F-041
**Priority**: High
**Related Roles**: system-architect, data-architect

## Objective

Recognize and classify financial entities (companies, persons, products, institutions) in Chinese text.

## Scope

- Entity type classification (company, person, product, institution, metric)
- Surface form extraction with character offsets
- Entity disambiguation (company name → ticker)
- Cross-document entity linking

## Data Model

**Input**: TextDocument (any Chinese financial text)
**Output**: NERResult (frozen dataclass) containing:
- entities: tuple[NEREntity, ...]
  - surface_form: str
  - entity_type: str (company/person/product/institution/metric)
  - start_offset: int
  - end_offset: int
  - confidence: float [0.0, 1.0]
  - linked_ticker: Optional[str] (for company entities)
  - normalized_name: Optional[str]

## Technical Requirements

- MUST recognize company names (full name, abbreviation, stock name)
- MUST recognize person names (analysts, executives, regulators)
- MUST recognize financial metrics (ROE, PE, PB, EPS)
- MUST link company entities to stock tickers via fuzzy matching
- MUST implement BaseDetector for P3 integration
- SHOULD handle nested entities (e.g., "中信证券分析师张三")
- SHOULD maintain entity dictionary for A-share listed companies

## Entity Types

| Type | Examples | Disambiguation |
|------|----------|----------------|
| company | 贵州茅台, 阿里巴巴, 宁德时代 | ticker linking |
| person | 张三, 李四(分析师) | role context |
| product | 茅台酒, Model Y | brand matching |
| institution | 证监会, 央行, 中信证券 | type classification |
| metric | ROE, 每股收益, 市盈率 | standard name |

## Integration Points

- Entity dictionary from A-share ticker database
- EventBuilder extracts entities as event metadata
- Entity linking enables cross-document correlation

## Acceptance Criteria

1. >90% F1 score on A-share company name recognition
2. >85% F1 score on person name recognition
3. >95% accuracy on ticker linking for recognized companies
4. Processes 1000 sentences/second on CPU
