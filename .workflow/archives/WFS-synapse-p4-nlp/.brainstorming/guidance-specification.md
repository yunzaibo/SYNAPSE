# P4 Chinese Financial NLP Layer - Confirmed Guidance Specification

**Metadata**: 2026-05-20T02:00:00+08:00 | brainstorm | Chinese Financial NLP | system-architect, data-architect, subject-matter-expert

## 1. Project Positioning & Goals

**CONFIRMED Objectives**: Build a Chinese financial NLP layer that provides structured text understanding capabilities for A-share equity research, integrated with the P3 event-driven framework.

**CONFIRMED Success Criteria**:
- Parse financial announcements (earnings reports, prospectuses) into structured data
- Extract key viewpoints from research reports
- Classify news sentiment (bullish/bearish/neutral) for Chinese financial text
- Understand policy documents from regulatory bodies (PBOC, CSRC, State Council)
- Recognize financial entities (companies, persons, products, institutions)
- Extract structured events from unstructured text (earnings forecasts, M&A, equity changes)
- All NLP outputs integrate with P3 event engine via BaseDetector ABC

## 2. Concepts & Terminology

**Core Terms**: The following terms are used consistently throughout this specification.

| Term | Definition | Aliases | Category |
|------|------------|---------|----------|
| Financial NLP | Natural language processing specialized for Chinese financial text | 金融NLP | core |
| Sentiment Analysis | Classification of text polarity as bullish/bearish/neutral | 情感分析, 情绪分析 | core |
| Named Entity Recognition (NER) | Identification and classification of financial entities in text | 实体识别, 命名实体识别 | core |
| Event Extraction | Structured extraction of events from unstructured text | 事件抽取 | core |
| Financial Announcement | Official company filings: earnings reports, prospectuses, board resolutions | 财报, 公告 | domain |
| Research Report | Analyst reports with investment theses and recommendations | 研报, 研究报告 | domain |
| Policy Document | Regulatory documents from PBOC, CSRC, State Council | 政策文件, 监管文件 | domain |
| Lexicon-based Analysis | Rule-based text analysis using domain-specific dictionaries | 词典分析, 规则分析 | technical |
| Transformer Model | Pre-trained neural network for contextual text understanding | 预训练模型 | technical |
| BaseDetector | P3 abstract base class for event detectors | 检测器基类 | technical |
| DetectorRegistry | P3 registry for registering event detectors | 检测器注册表 | technical |

**Usage Rules**:
- All documents MUST use the canonical term
- Aliases are for reference only
- New terms introduced in role analysis MUST be added to this glossary

## 3. Non-Goals (Out of Scope)

The following are explicitly OUT of scope for this project:

- **Real-time trading signals**: NLP outputs are research inputs, not trading signals
- **Portfolio construction**: NLP layer does not make buy/sell recommendations
- **Multi-language support**: MVP focuses exclusively on Chinese (Simplified)
- **Deep learning model training**: Use pre-trained models, do not train from scratch
- **Social media scraping**: NLP processes text provided by data layer, does not crawl
- **News aggregation**: Text ingestion is handled by P5 data pipeline
- **Real-time streaming NLP**: Batch processing is sufficient for research use cases
- **GPU inference optimization**: CPU inference is acceptable for research volumes

**Rationale**: These exclusions help maintain focus on core NLP capabilities and prevent scope creep into data collection, trading, or infrastructure optimization.

## 4. System Architect Decisions

### SELECTED Choices

**NLP Pipeline Architecture**: The system MUST implement a modular pipeline with separate stages for text preprocessing, feature extraction, and task-specific inference.
- **Rationale**: Modularity enables independent improvement of each stage
- **Impact**: Each stage can be tested and replaced independently
- **Requirement Level**: MUST

**Integration Pattern with P3**: New NLP detectors MUST implement BaseDetector ABC and register via DetectorRegistry.
- **Rationale**: Consistency with existing event framework
- **Impact**: NLP outputs automatically participate in propagation graph and impact analysis
- **Requirement Level**: MUST

**Model Loading Strategy**: The system SHOULD use lazy loading for NLP models to minimize memory footprint when multiple analysis types are not needed simultaneously.
- **Rationale**: Research workflows typically focus on one analysis type at a time
- **Impact**: Reduces memory usage from ~2GB (all models) to ~500MB (active model only)
- **Requirement Level**: SHOULD

**Error Handling**: NLP pipeline MUST gracefully degrade when model loading fails or text is unparseable, returning empty results rather than raising exceptions.
- **Rationale**: Research workflows should not crash due to individual text failures
- **Impact**: Downstream components receive empty results with logging
- **Requirement Level**: MUST

## 5. Data Architect Decisions

### SELECTED Choices

**Text Storage Model**: Raw text and NLP results MUST be stored as separate entities with linking via document_id, enabling re-processing without data duplication.
- **Rationale**: NLP models evolve; raw text should be preserved for re-analysis
- **Impact**: Storage overhead ~2x, but enables model versioning and A/B comparison
- **Requirement Level**: MUST

**NER Output Schema**: Financial entities MUST be represented as typed spans with surface_form, entity_type, confidence, and optional linked_ticker for disambiguation.
- **Rationale**: Typed spans enable downstream filtering and aggregation
- **Impact**: Consistent entity representation across all NLP tasks
- **Requirement Level**: MUST

**Sentiment Output Schema**: Sentiment results MUST include label (bullish/bearish/neutral), confidence score, and optional aspect-level sentiment for multi-aspect texts.
- **Rationale**: Aspect-level sentiment enables nuanced analysis of earnings reports
- **Impact**: More granular sentiment data for event engine consumption
- **Requirement Level**: MUST

**Storage Format**: NLP results SHOULD use Parquet format for batch query efficiency, consistent with P2 backtest persistence pattern.
- **Rationale**: Columnar storage enables efficient aggregation queries
- **Impact**: ~3x faster analytical queries vs JSON
- **Requirement Level**: SHOULD

## 6. Subject Matter Expert Decisions

### SELECTED Choices

**Chinese Financial Text Challenges**: The system MUST handle domain-specific challenges: financial abbreviation expansion (e.g., 营收→营业收入), number format normalization (亿/万→numeric), and table structure extraction from PDF announcements.
- **Rationale**: Generic NLP fails on financial text without domain adaptation
- **Impact**: Significantly improves accuracy on Chinese financial documents
- **Requirement Level**: MUST

**Sentiment Lexicon**: The system SHOULD maintain a domain-specific sentiment lexicon with 500+ financial terms, augmenting generic sentiment models.
- **Rationale**: Financial sentiment differs from general sentiment (e.g., 高增长 is positive, 高风险 is negative)
- **Impact**: +15-20% accuracy improvement on financial text classification
- **Requirement Level**: SHOULD

**Policy Document Understanding**: Policy documents MUST be processed with structured extraction: issuing body, effective date, key regulatory changes, and affected sectors.
- **Rationale**: Policy impact analysis requires structured metadata
- **Impact**: Enables sector-level policy impact scoring in event engine
- **Requirement Level**: MUST

**Event Type Mapping**: NLP-extracted events MUST map to existing P3 EventType taxonomy (EARNINGS_FORECAST, MERGER_ACQUISITION, EQUITY_CHANGE, POLICY_CHANGE) or extend with new types via taxonomy update.
- **Rationale**: Consistency with P3 event framework
- **Impact**: NLP events automatically participate in cross-event correlation
- **Requirement Level**: MUST

## Cross-Role Integration

**CONFIRMED Integration Points**:
- NLP detectors → BaseDetector ABC → DetectorRegistry (system-architect + data-architect)
- NLP output schema → Event schema extension (data-architect + subject-matter-expert)
- Sentiment lexicon → LexiconAnalyzer enhancement (subject-matter-expert + system-architect)
- Model lazy loading → Pipeline architecture (system-architect)

## Risks & Constraints

**Identified Risks**:
- Model download size (~2GB for Chinese BERT) → Mitigation: Lazy loading + optional model cache
- PDF table extraction complexity → Mitigation: Start with text-only, add table extraction in v2
- Jieba segmentation accuracy on financial terms → Mitigation: Custom dictionary with 500+ financial terms
- NER disambiguation for company names → Mitigation: Fuzzy matching with ticker database

## Feature Decomposition

**Constraints**: Max 8 features | Each independently implementable | ID format: F-{3-digit}

| Feature ID | Name | Description | Related Roles | Priority |
|------------|------|-------------|---------------|----------|
| F-037 | financial-announcement-parser | Structured extraction from earnings reports and company filings | system-architect, data-architect, subject-matter-expert | High |
| F-038 | research-report-summarizer | Key viewpoint and thesis extraction from analyst reports | system-architect, subject-matter-expert | High |
| F-039 | news-sentiment-classifier | Bullish/bearish/neutral classification for Chinese financial news | system-architect, data-architect, subject-matter-expert | High |
| F-040 | policy-document-understander | Structured extraction from regulatory documents (PBOC, CSRC, State Council) | subject-matter-expert, data-architect | Medium |
| F-041 | financial-ner-engine | Named entity recognition for companies, persons, products, institutions | system-architect, data-architect | High |
| F-042 | event-extraction-engine | Structured event extraction from unstructured text (earnings forecasts, M&A, equity changes) | system-architect, subject-matter-expert | High |
| F-043 | nlp-p3-event-integration | BaseDetector implementations connecting NLP outputs to P3 event engine | system-architect, data-architect | High |
| F-044 | financial-sentiment-lexicon | Domain-specific sentiment dictionary with 500+ financial terms | subject-matter-expert, data-architect | Medium |

## Appendix: Decision Tracking

| Decision ID | Category | Question | Selected | Phase | Rationale |
|-------------|----------|----------|----------|-------|-----------|
| D-037 | Intent | P4 scope | NLP layer for A-share research | 1 | Core research capability |
| D-038 | Roles | Analysis roles | system-architect, data-architect, subject-matter-expert | 2 | Architecture + data + domain |
| D-039 | System | Pipeline architecture | Modular staged pipeline | 3 | Independent stage improvement |
| D-040 | System | P3 integration | BaseDetector + DetectorRegistry | 3 | Framework consistency |
| D-041 | System | Model loading | Lazy loading | 3 | Memory optimization |
| D-042 | System | Error handling | Graceful degradation | 3 | Research workflow stability |
| D-043 | Data | Text storage | Separate raw/results with document_id link | 3 | Re-processing capability |
| D-044 | Data | NER schema | Typed spans with confidence | 3 | Downstream compatibility |
| D-045 | Data | Sentiment schema | Label + confidence + aspect | 3 | Nuanced analysis |
| D-046 | Data | Storage format | Parquet for batch queries | 3 | P2 consistency |
| D-047 | Domain | Chinese challenges | Abbreviation, number format, table extraction | 3 | Domain accuracy |
| D-048 | Domain | Sentiment lexicon | 500+ financial terms | 3 | +15-20% accuracy |
| D-049 | Domain | Policy extraction | Structured metadata extraction | 3 | Impact analysis |
| D-050 | Domain | Event mapping | P3 EventType taxonomy alignment | 3 | Cross-event correlation |
