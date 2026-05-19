# Subject Matter Expert Analysis: P4 Chinese Financial NLP Layer

## Role Perspective Overview

This analysis examines the P4 Chinese Financial NLP Layer from the perspective of Chinese financial markets domain expertise. SYNAPSE is a personal quant research tool for A-share factor research, not an automated trading system. All NLP outputs serve as research inputs that inform the analyst's judgment. The analysis covers eight domain areas where generic NLP fails and financial-domain adaptation is essential for reliable A-share research.

---

## 1. Chinese Financial Text Challenges

### 1.1 Abbreviation Expansion

Chinese financial text is saturated with abbreviations that generic NLP tokenizers treat as separate, unrelated tokens. Without domain-aware expansion, downstream tasks (NER, sentiment, event extraction) degrade significantly.

**High-frequency abbreviations requiring a dedicated expansion table:**

| Abbreviation | Full Form | Impact if Missed |
|--------------|-----------|------------------|
| 营收 | 营业收入 | Missed revenue growth detection |
| 净利 | 净利润 | Missed profitability signal |
| 毛利 | 毛利润 | Missed margin analysis |
| 扣非 | 扣除非经常性损益 | Distorted core earnings view |
| EPS | 每股收益 | Lost valuation metric |
| ROE | 净资产收益率 | Lost profitability metric |
| PE | 市盈率 | Lost valuation metric |
| PB | 市净率 | Lost valuation metric |
| BVPS | 每股净资产 | Lost asset value metric |
| 同比 | 与上年同期相比 | Lost comparison direction |
| 环比 | 与上期相比 | Lost trend direction |
| 预盈 | 预计盈利 | Missed pre-announcement signal |
| 预亏 | 预计亏损 | Missed pre-announcement signal |
| 扭亏为盈 | 扭转亏损实现盈利 | Missed turnaround signal |
| 高送转 | 高比例送股转增 | Missed dividend/split signal |
| 股权激励 | 股票期权激励计划 | Missed incentive alignment signal |
| 定增 | 非公开发行股票 | Missed dilution/fundraising event |
| 配股 | 向原股东配售股票 | Missed dilution event |
| 可转债 | 可转换公司债券 | Missed hybrid instrument |
| 质押 | 股权质押 | Missed risk signal (pledge risk) |

**Requirement**: The NLP pipeline MUST maintain an abbreviation expansion table and apply it during text preprocessing before tokenization. The table MUST be extensible via a YAML/JSON configuration file without code changes. Abbreviation expansion MUST run before jieba segmentation to avoid splitting compound terms.

### 1.2 Number Format Normalization

Chinese financial text uses unit-based number notation that must be converted to standard numeric values for quantitative analysis.

**Conversion rules the system MUST implement:**

| Pattern | Example | Target |
|---------|---------|--------|
| X亿 | 32.5亿 | 3,250,000,000 |
| X万 | 1200万 | 12,000,000 |
| X亿元 | 32.5亿元 | 3,250,000,000 |
| X万元 | 1200万元 | 12,000,000 |
| X% | 增长15.3% | 0.153 |
| X倍 | 增长2.5倍 | 2.5 |
| X港元/美元 | 50美元 | 50 USD |
| 百分之X | 百分之十五点三 | 0.153 |
| X成 | 八成新 | 0.8 |

**Edge cases the system MUST handle:**
- Mixed units: "营收32.5亿元，同比增长15%" -- extract both absolute and relative values
- Negative values: "亏损约5000万元" -- recognize as negative earnings
- Ranges: "净利润约10-12亿元" -- extract range or midpoint
- Approximations: "约3亿"、"超5亿"、"近10亿" -- extract approximation markers
- Financial ratios: "ROE达18.5%" -- extract both metric name and value

**Requirement**: The system MUST provide a `FinancialNumberParser` utility that normalizes Chinese financial number expressions to float values. The parser MUST preserve approximation markers (约, 超, 近) as metadata alongside the numeric value, as these carry research significance.

### 1.3 Table Structure Extraction

A-share financial announcements (earnings reports, prospectuses) contain critical data in tables. The existing P4 guidance (D-043) acknowledges table extraction as v2 complexity. However, the system MUST be designed to accommodate table extraction without architectural changes.

**Current MVP scope (text-only)**: The system SHOULD extract data from tabular text when it appears in plain-text format (e.g., markdown tables in research reports, tab-separated data in copied announcements).

**v2 table extraction requirements**:
- Income statement tables: revenue, costs, gross profit, operating profit, net profit rows with quarterly/annual columns
- Balance sheet tables: assets, liabilities, equity with category groupings
- Cash flow table: operating/investing/financing activities
- Shareholder tables: top 10 shareholders with percentage holdings
- The system SHOULD store extracted table data as structured JSON linked to the parent document via document_id

### 1.4 Jieba Segmentation Customization

Generic jieba segmentation produces incorrect token boundaries for financial text. The system MUST load a custom financial dictionary before segmentation.

**Dictionary categories and minimum term counts:**

| Category | Example Terms | Min Count |
|----------|--------------|-----------|
| Financial metrics | 每股收益, 净资产收益率, 毛利率 | 50+ |
| Market terms | 涨停板, 跌停板, 北向资金, 融资融券 | 80+ |
| Instrument types | 可转债, 优先股, 存托凭证 | 30+ |
| Regulatory bodies | 证监会, 银保监会, 央行, 交易所 | 20+ |
| Accounting terms | 营业收入, 营业成本, 资产减值 | 60+ |
| Event terms | 增持, 减持, 回购, 质押, 解除质押 | 40+ |

**Requirement**: The custom dictionary MUST be loaded as the first step in the NLP preprocessing pipeline. Dictionary entries MUST be sorted by frequency (highest frequency first) to ensure jieba prioritizes domain-specific segmentations over generic ones. The dictionary file MUST be external (YAML/CSV) and version-controlled.

---

## 2. Sentiment Analysis Domain Requirements

### 2.1 Financial Sentiment vs General Sentiment

The existing `LexiconAnalyzer` in `synapse/event/social.py` provides a foundation with 50+ positive and 52+ negative terms. However, financial sentiment differs fundamentally from general sentiment in three dimensions.

**Dimension 1: Context-dependent polarity**

| Term | General Context | Financial Context | Required Handling |
|------|----------------|-------------------|-------------------|
| 高增长 | Neutral/positive | Always positive (growth stock) | Context-aware polarity flip NOT needed |
| 高风险 | Negative | Negative (but sometimes neutral in risk disclosure) | Context window matters |
| 超预期 | Positive | Positive (earnings surprise) | Domain alignment |
| 大幅减少 | Negative | Negative for volume, potentially positive for costs | Aspect-level disambiguation |
| 估值修复 | Neutral | Positive (recovering from undervaluation) | Domain alignment |
| 强势回调 | Contradictory | Moderately positive (healthy pullback) | Nuanced scoring needed |

**Dimension 2: Negation handling in financial text**

Financial text frequently uses conditional negation that must be handled differently from general negation:

- "不构成重大影响" -- negative for "significance" but neutral overall (routine disclosure)
- "无重大风险" -- positive for risk profile
- "不保证未来收益" -- regulatory boilerplate, sentiment-neutral
- "业绩不会出现大幅下滑" -- moderate positive (management reassurance)

**Requirement**: The system SHOULD distinguish between negation in regulatory boilerplate (sentiment-neutral) and negation in substantive commentary (inverts sentiment). A simple negation window approach is insufficient; the system SHOULD use clause-level context.

**Dimension 3: Aspect-level sentiment**

A single earnings report paragraph may contain bullish and bearish signals for different aspects:

```
原文: "公司营收同比增长25%，但净利润下降8%，主要受原材料成本上涨影响。"
- aspect=revenue: positive (增长25%)
- aspect=profit: negative (下降8%)
- aspect=cost: negative (成本上涨)
- overall: mixed/neutral
```

**Requirement**: The system MUST support aspect-level sentiment extraction for financial documents. The `SentimentResult` schema MUST include an `aspects` field (list of `{aspect_name, sentiment_label, confidence, evidence_span}` tuples). The existing guidance specification (D-045) confirms this requirement.

### 2.2 Sentiment Categories for A-Share Research

Beyond bullish/bearish/neutral, A-share research sentiment analysis should capture:

| Sentiment Category | Description | Example Text |
|-------------------|-------------|--------------|
| Strongly Bullish | High conviction positive | "业绩超预期，上调目标价至50元" |
| Mildly Bullish | Moderate positive | "业绩符合预期，维持增持评级" |
| Neutral | No directional view | "公司发布年报，营收微增2%" |
| Mildly Bearish | Moderate negative | "业绩低于预期，下调评级至中性" |
| Strongly Bearish | High conviction negative | "业绩大幅不及预期，下调至卖出" |
| Uncertain | Cannot determine | "业绩存在不确定性，需进一步观察" |

**Requirement**: The system SHOULD use a 6-point sentiment scale (strongly bullish to uncertain) rather than 3-point, with the 6 points mapping to the guidance specification's 3-point labels for P3 event engine compatibility: strongly bullish/mildly bullish -> bullish, neutral/uncertain -> neutral, mildly bearish/strongly bearish -> bearish.

---

## 3. Financial Entity Types and Taxonomy

### 3.1 Entity Type Hierarchy

The NER engine (F-041) MUST recognize the following entity types, organized into a two-level hierarchy:

**Level 1: Core Entity Types (MUST)**

| Entity Type | Chinese Label | Subtypes | Examples |
|-------------|--------------|----------|----------|
| COMPANY | 公司实体 | Listed, Unlisted, Parent, Subsidiary | 贵州茅台, 宁德时代, 比亚迪 |
| PERSON | 人物实体 | Executive, Analyst, Regulator, Investor | 马明哲, 但斌 |
| INSTITUTION | 机构实体 | Broker, Fund, Bank, Regulator | 中信证券, 易方达, 工商银行 |
| PRODUCT | 产品实体 | Stock, Fund, Bond, Derivative | 600519.SH, 510300.SH, 可转债23转债 |
| REGULATORY_BODY | 监管机构 | National, Provincial, Exchange | 证监会, 人民银行, 上交所 |

**Level 2: Extended Entity Types (SHOULD)**

| Entity Type | Chinese Label | Purpose | Examples |
|-------------|--------------|---------|----------|
| SECTOR | 行业板块 | Sector/industry classification | 半导体, 新能源, 白酒 |
| CONCEPT | 概念题材 | Theme/concept classification | ChatGPT概念, 光伏, 储能 |
| POLICY | 政策法规 | Regulatory documents | 国九条, 新证券法 |
| METRIC | 财务指标 | Quantitative metrics | ROE, 毛利率, 北向资金净流入 |

### 3.2 Company Name Disambiguation

A-share company names present unique disambiguation challenges:

**Full name vs abbreviation**: "中国贵州茅台酒股份有限公司" vs "贵州茅台" vs "茅台" -- all refer to the same entity. The system MUST match all forms to a canonical entity with linked_ticker.

**Group company confusion**: "比亚迪股份有限公司" (listed, 002594.SZ) vs "比亚迪股份有限公司" (unlisted subsidiary) vs brand name "比亚迪" (ambiguous). The system SHOULD use context clues (stock code mentions, financial metric proximity) to disambiguate.

**State-owned enterprise naming**: "中国XX集团" pattern where "中国" is a prefix indicating central SOE. Examples: 中国中免, 中国石油, 中国移动. The system MUST NOT strip "中国" as a generic prefix -- it is part of the entity name.

**Requirement**: The NER engine MUST provide a fuzzy matching mechanism that maps surface forms to canonical entities. The mapping table MUST include at minimum: full legal name, common abbreviation, stock code, and ticker (e.g., `600519.SH`). The system SHOULD use edit distance or phonetic matching (pinyin) for partial matches, with confidence scores.

### 3.3 Regulatory Body Taxonomy

| Body | Chinese | Abbreviation | Scope | Document Types |
|------|---------|-------------|-------|----------------|
| CSRC | 中国证券监督管理委员会 | 证监会 | Securities regulation | 行政处罚决定书, 公告, 通知, 规定 |
| PBOC | 中国人民银行 | 央行 | Monetary policy | 利率决定, 降准公告, 政策报告 |
| CBIRC | 中国银行保险监督管理委员会 | 银保监会 | Banking/insurance | 监管意见, 处罚决定 |
| NDRC | 国家发展和改革委员会 | 发改委 | Price controls, investment | 指导意见, 批复 |
| State Council | 国务院 | 国务院 | Executive policy | 国发文件, 常务会议决定 |
| MOF | 财政部 | 财政部 | Fiscal policy | 通知, 公告, 暂行规定 |
| SAFE | 国家外汇管理局 | 外管局 | Foreign exchange | 通知, 规定 |
| SSE | 上海证券证券交易所 | 上交所 | Exchange rules | 通知, 规则, 公告 |
| SZSE | 深圳证券交易所 | 深交所 | Exchange rules | 通知, 规则, 公告 |
| BSE | 北京证券交易所 | 北交所 | Exchange rules | 通知, 规则, 公告 |

**Requirement**: The system MUST recognize all regulatory body variants (full name, abbreviation, commonly used short name) as the same REGULATORY_BODY entity. The entity linking table MUST be maintained as an external configuration.

---

## 4. Event Extraction Patterns

### 4.1 Event Types Mapping to P3 Taxonomy

The existing `EVENT_TYPES` in `synapse/event/taxonomy.py` defines nine event types. NLP-extracted events MUST map to these types. The following table specifies extraction patterns for each type:

**Earnings Events (`earnings`)**

| Pattern | Trigger Phrases | Extracted Fields |
|---------|----------------|------------------|
| Earnings release | "发布年报", "披露季报", "发布业绩快报" | company, period, revenue, net_profit, yoy_change |
| Pre-announcement | "预盈", "预亏", "业绩预告", "预计净利润" | company, type(bullish/bearish), range, period |
| Earnings revision | "修正业绩", "业绩更正", "下修/上修预期" | company, direction(up/down), original, revised |
| Dividend announcement | "每10股派X元", "分红方案", "送转方案" | company, dividend_per_share, record_date, ex_date |
| Audit opinion | "审计意见", "保留意见", "无法表示意见" | company, auditor, opinion_type |

**Corporate Action Events (`corporate_action`)**

| Pattern | Trigger Phrases | Extracted Fields |
|---------|----------------|------------------|
| Shareholding change | "增持", "减持", "举牌", "权益变动" | company, person/entity, direction, percentage, shares |
| Equity pledge | "质押", "解除质押", "质押比例" | company, pledgor, shares, percentage, status |
| Buyback | "回购", "回购方案", "注销回购" | company, shares, amount, period, purpose |
| M&A | "收购", "并购", "重组", "资产注入" | acquirer, target, price, percentage, status |
| Secondary offering | "定增", "非公开发行", "配股" | company, shares, price, amount, purpose |
| Listing/delisting | "上市", "退市", "暂停上市", "摘帽/戴帽" | company, action, exchange, effective_date |

**Policy Events (`policy` and `policy_change`)**

| Pattern | Trigger Phrases | Extracted Fields |
|---------|----------------|------------------|
| Rate decision | "降息", "加息", "利率调整", "LPR" | body(PBOC), rate_type, direction, magnitude, effective_date |
| RRR adjustment | "降准", "上调存款准备金率" | body(PBOC), direction, magnitude, effective_date |
| Regulatory change | "修订", "发布新规", "征求意见稿" | body, title, scope, effective_date, impact_scope |
| Trading rule change | "调整涨跌幅", "修改交易规则" | body(exchange), rule, change, effective_date |
| Sector regulation | "行业整顿", "反垄断", "安全生产" | body, sector, action, severity |

**Sentiment Events (`sentiment` and `social_sentiment`)**

| Pattern | Trigger Phrases | Extracted Fields |
|---------|----------------|------------------|
| Northbound flow | "北向资金净流入", "北向资金大幅买入" | direction(inflow/outflow), amount, top_stocks |
| Margin trading | "融资余额", "融券余额", "融资买入" | company, margin_type, change, amount |
| Block trade | "大宗交易", "溢价成交", "折价成交" | company, price, discount_rate, volume |
| Dragon-tiger list | "龙虎榜", "机构席位买入" | company, reason, institutional_buy, retail_buy |
| Social buzz | "热搜", "讨论量飙升", "关注度" | company, platform, volume_change |

**Capital Flow Events (`capital_flow`)**

| Pattern | Trigger Phrases | Extracted Fields |
|---------|----------------|------------------|
| Fund flow | "主力资金流入", "主力净买入" | company, direction, amount, fund_type |
| ETF flow | "ETF净申购", "ETF份额增长" | etf_name, direction, amount |

### 4.2 Event Extraction Output Schema

Every extracted event MUST include:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| event_type | str | Yes | Maps to P3 EventType taxonomy key |
| confidence | float | Yes | Extraction confidence [0.0, 1.0] |
| source_text | str | Yes | Original text span that triggered extraction |
| entities | dict | Yes | Extracted entity relationships (key-value pairs) |
| timestamp | datetime | Yes | Event date from text (not extraction date) |
| priority | str | Yes | Maps to P3 PRIORITY_LEVELS (P0-P3) |
| raw_document_id | str | Yes | Link to source document for traceability |

**Requirement**: The event extraction engine MUST return confidence scores. Events below a configurable threshold (default 0.6) SHOULD be flagged for human review rather than silently dropped. The system MUST NOT discard low-confidence events entirely -- they may still be useful as weak signals when aggregated.

### 4.3 Temporal Expression Extraction

Financial event extraction requires precise temporal understanding:

| Expression Type | Example | Extracted Value |
|----------------|---------|-----------------|
| Absolute date | "2024年3月15日" | date(2024, 3, 15) |
| Relative date | "未来三个月" | timedelta(days=90) from extraction date |
| Fiscal period | "2024年三季度" | Q3 2024 |
| Fiscal year | "2024财年" | FY2024 |
| Deadline | "在30个交易日内" | trading_days_between(start, start+30) |
| Effective date | "自发布之日起施行" | extraction_date |

**Requirement**: The system MUST use the TradingCalendar from `synapse/core/market/calendar.py` for trading-day-relative expressions. Calendar-aware temporal resolution ensures extracted deadlines and effective dates align with actual A-share trading days.

---

## 5. Policy Document Structure

### 5.1 Document Format Taxonomy

A-share policy documents follow predictable structural patterns that enable structured extraction.

**PBOC Documents**

| Document Type | Chinese Name | Structure | Key Extractable Fields |
|--------------|-------------|-----------|----------------------|
| Rate decision | 利率决定 | Title + body (1-2 paragraphs) + effective date | rate_type, old_value, new_value, effective_date |
| RRR adjustment | 存款准备金率调整 | Title + body + tables (by institution type) | direction, magnitude, applicable_institutions, effective_date |
| Monetary policy report | 货币政策执行报告 | Multi-section (macro, monetary, financial, outlook) | sections, key_statements, policy_direction |
| Window guidance | 窗口指导 | Brief directive | target_sectors, guidance_content |

**CSRC Documents**

| Document Type | Chinese Name | Structure | Key Extractable Fields |
|--------------|-------------|-----------|----------------------|
| Administrative penalty | 行政处罚决定书 | Header (party, violation) + facts + legal basis + penalty | violator, violation_type, penalty_amount, date |
| Public notice | 公告 | Title + body | title, effective_date, scope |
| IPO registration | IPO注册 | Title + company + amount | company, shares, amount, exchange |
| Regulatory interpretation | 监管问答 | Q&A format | question_topic, interpretation, scope |

**State Council Documents**

| Document Type | Chinese Name | Structure | Key Extractable Fields |
|--------------|-------------|-----------|----------------------|
| State Council opinion | 国务院意见 | Multi-section with numbered points | title, sections, effective_date, scope |
| Executive meeting decision | 国务院常务会议 | Bullet points of decisions | decisions[], affected_sectors |
| State Council regulation | 行政法规 | Chapters with articles | title, chapters, effective_date |

### 5.2 Policy Impact Extraction

Policy documents require a specialized extraction template that captures:

**Required extraction fields:**

| Field | Description | Example |
|-------|-------------|---------|
| issuing_body | Regulatory authority | PBOC |
| document_number | Official document reference | 银发[2024]15号 |
| effective_date | When the policy takes effect | 2024-04-01 |
| policy_type | Category of regulation | 利率调整 |
| target_sectors | Affected industries | 房地产, 银行, 制造业 |
| target_entities | Affected entity types | 全国性商业银行, 房地产企业 |
| key_changes | Specific regulatory changes | LPR下调10bp |
| previous_policy | Superseded or modified policy | 银发[2023]12号 |
| impact_direction | Positive/negative/neutral per sector | banking: positive, real_estate: positive |
| impact_magnitude | Strong/moderate/weak | moderate |

**Requirement**: The policy document processor MUST extract the document number (文号) using the standard Chinese government document numbering format: `[机关代字][年份]第[序号]号`. This number serves as a unique identifier for deduplication and policy chain tracking (which policy supersedes which).

### 5.3 Policy Chain Tracking

Policy documents frequently reference, amend, or supersede previous documents. The system SHOULD build a policy chain graph:

```
国发[2024]1号 (国务院意见)
  └─ 银发[2024]15号 (PBOC实施细则)
      └─ 银保监发[2024]8号 (CBIRC配套通知)
```

**Requirement**: The system SHOULD store `previous_policy` and `amended_by` relationships when extracting policy documents. This enables longitudinal policy impact tracking: "since the State Council issued X, three regulatory bodies have issued implementation rules."

---

## 6. Domain-Specific Lexicon Requirements

### 6.1 Lexicon Scope and Categories

The guidance specification (D-048) confirms a 500+ term lexicon. The existing `social.py` provides 50 positive + 52 negative terms. The lexicon MUST be expanded to cover the following categories:

| Category | Min Terms | Purpose | Example Terms |
|----------|----------|---------|---------------|
| Bullish sentiment | 80 | Upside signal detection | 利好, 涨停, 大涨, 突破, 新高, 放量, 金叉, 龙头 |
| Bearish sentiment | 80 | Downside signal detection | 利空, 跌停, 大跌, 崩盘, 死叉, 套牢, 割肉, 暴雷 |
| Neutral/technical | 50 | Factual signal detection | 成交量, 换手率, 市盈率, 市净率, 振幅 |
| Regulatory | 60 | Policy impact classification | 处罚, 警告, 立案, 整顿, 暂停, 约谈, 窗口指导 |
| Accounting | 70 | Financial data understanding | 营业收入, 净利润, 毛利率, 资产负债率, 经营现金流 |
| Market microstructure | 50 | Trading signal vocabulary | 涨停板, 跌停板, 炸板, 封单, 龙虎榜, 大宗交易 |
| Sector/industry | 60 | Sector classification vocabulary | 半导体, 光伏, 新能源, 白酒, 医药, 银行, 券商 |
| Instrument types | 30 | Product vocabulary | 可转债, 优先股, ETF, LOF, QDII, RQFII |
| Risk/regulatory | 50 | Risk signal vocabulary | ST, *ST, 退市风险, 诉讼, 处罚, 立案调查, 问询函 |
| Corporate governance | 50 | Governance signal vocabulary | 独董, 关联交易, 内幕交易, 信息披露违规 |

**Total minimum: 580 terms**

### 6.2 Lexicon Data Structure

Each lexicon entry SHOULD include:

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| term | str | Yes | The lexicon term |
| category | str | Yes | Category classification |
| polarity | float | Yes | Sentiment weight in [-1.0, 1.0] |
| frequency | int | Yes | Usage frequency in financial corpus |
| examples | list[str] | No | Usage examples for validation |
| is_negation_sensitive | bool | Yes | Whether polarity inverts under negation |

**Example entry:**
```yaml
- term: "超预期"
  category: "bullish_sentiment"
  polarity: 0.7
  frequency: 850
  examples:
    - "业绩超预期"
    - "营收超市场预期"
  is_negation_sensitive: true
```

**Requirement**: The lexicon MUST be stored as a YAML file (not hardcoded in Python). Lexicon entries MUST be version-controlled with change logs. The system SHOULD include a `LexiconManager` class that supports hot-reloading without pipeline restart, enabling iterative lexicon refinement during research.

### 6.3 Lexicon Maintenance Workflow

For a personal research tool, lexicon maintenance MUST be practical:

1. **Initial seeding**: Bootstrap from the existing 102 terms in `social.py` plus curated financial dictionaries
2. **Discovery**: The NLP pipeline SHOULD log terms that appear in financial text but are absent from the lexicon, with their context windows
3. **Validation**: The user SHOULD be able to review discovered terms and assign polarity/category manually
4. **Versioning**: Each lexicon update MUST be versioned with a changelog (terms added, polarity adjusted, terms removed)
5. **A/B comparison**: The system SHOULD support running sentiment analysis with different lexicon versions side-by-side on the same text, enabling quality comparison

**Requirement**: The system MUST provide a CLI command or API to add/remove/update lexicon entries. Manual curation is the primary maintenance mechanism for a personal research tool -- automated lexicon induction from corpus statistics is a future enhancement, not an MVP requirement.

---

## 7. Quality Metrics for NLP Output

### 7.1 Precision/Recall Expectations

Based on typical Chinese financial NLP benchmarks and the maturity of available tools:

| Task | Metric | MVP Target | Stretch Target | Notes |
|------|--------|-----------|----------------|-------|
| Sentiment classification | F1 (3-class) | 0.75 | 0.85 | FinBERT-class models on A-share text |
| Sentiment classification | F1 (6-class) | 0.60 | 0.75 | Harder fine-grained task |
| Named entity recognition | F1 (company) | 0.80 | 0.90 | High due to structured naming |
| Named entity recognition | F1 (person) | 0.70 | 0.80 | Moderate ambiguity |
| Named entity recognition | F1 (institution) | 0.75 | 0.85 | Well-structured taxonomy |
| Event extraction | Precision | 0.70 | 0.85 | False positives are costly for research |
| Event extraction | Recall | 0.60 | 0.75 | Better to miss some than fabricate |
| Temporal extraction | Accuracy | 0.80 | 0.90 | Structured patterns help |
| Number extraction | Accuracy | 0.85 | 0.95 | Regex-based, high reliability |

**Requirement**: The system MUST track precision and recall metrics per task. The system SHOULD store evaluation results alongside model version information, enabling quality regression detection when models are updated.

### 7.2 Evaluation Methodology

**Automated evaluation (MUST)**:
- Maintain a labeled evaluation set of at least 200 documents per task type
- Run evaluation on every model/lexicon change
- Track metrics over time in a results log

**Human evaluation (SHOULD)**:
- Monthly review of 50 randomly sampled NLP outputs per task type
- Focus on false positives in event extraction (fabricated events are more harmful than missed events)
- Track inter-annotator agreement when multiple evaluators are available

**Error taxonomy the system SHOULD support:**

| Error Type | Description | Example |
|-----------|-------------|---------|
| FALSE_POSITIVE | NLP detects event that didn't happen | "公司否认收购传闻" extracted as M&A |
| FALSE_NEGATIVE | NLP misses real event | Failing to detect "减持计划" |
| WRONG_TYPE | Correct detection, wrong event type | Dividend classified as secondary offering |
| WRONG_ENTITY | Correct event, wrong entity linked | Attributing Company A's earnings to Company B |
| WRONG_SENTIMENT | Correct entity/event, wrong polarity | "高风险" scored as positive |
| WRONG_TIME | Correct event, wrong temporal extraction | 2024 Q3 report dated as 2024 Q4 |

### 7.3 Confidence Calibration

**Requirement**: The system SHOULD produce calibrated confidence scores. If the system reports 0.8 confidence on 100 extractions, approximately 80 should be correct. The system SHOULD periodically run calibration analysis on held-out evaluation data.

**Requirement**: The system MUST log confidence distribution statistics. A sudden shift in confidence distribution (e.g., mean confidence drops from 0.75 to 0.55) SHOULD trigger a warning, indicating potential data quality or model degradation issues.

---

## 8. Integration with Research Workflow

### 8.1 NLP Output Flow

The NLP layer sits between raw data ingestion (P5) and the P3 event engine. The research workflow integration follows this path:

```
P5 Data Pipeline (raw text)
  └─> P4 NLP Layer
       ├─> Text Preprocessing (abbreviation, number normalization, segmentation)
       ├─> NER Engine (entity extraction and linking)
       ├─> Sentiment Classifier (bullish/bearish/neutral + aspect)
       ├─> Event Extractor (structured events)
       └─> Policy Processor (regulatory document understanding)
           └─> BaseDetector implementations (P3 integration)
               └─> DetectorRegistry (P3 event engine)
                   ├─> Watchlist enrichment
                   ├─> Event correlation graph
                   ├─> Impact analysis
                   └─> Thesis evolution tracking
```

### 8.2 Watchlist Integration

The watchlist is the user's primary research interface. NLP outputs enrich the watchlist in three ways:

**Signal aggregation**: Multiple NLP outputs for the same ticker are aggregated into a rolling signal. The system SHOULD provide a "sentiment momentum" metric: the trend of sentiment scores over the trailing N trading days.

**Event timeline**: Extracted events for watchlist tickers are displayed as a chronological timeline. The system MUST link each event to its source document for drill-down investigation.

**Alert triggers**: The system SHOULD allow the user to define alert conditions based on NLP outputs:
- Sentiment score crosses a threshold (e.g., drops below -0.5)
- New event type appears (e.g., first "regulatory penalty" event for a ticker)
- Entity relationship change (e.g., new major shareholder appears in NER output)

### 8.3 Decision Log Integration

SYNAPSE's research memory system tracks the evolution of investment theses. NLP outputs feed into this system:

**Thesis validation**: When the user forms a thesis (e.g., "半导体 sector will benefit from policy support"), NLP outputs that validate or challenge the thesis SHOULD be automatically linked. The system tracks thesis health as a function of supporting and contradicting NLP signals.

**Evidence accumulation**: Each NLP output that relates to a thesis becomes a piece of evidence. The system SHOULD track evidence count, recency, and direction as thesis strength indicators.

**Contradiction detection**: When NLP outputs contradict an existing thesis (e.g., bearish sentiment for a bullish-positioned ticker), the system SHOULD flag the contradiction prominently rather than burying it in aggregated signals.

### 8.4 Factor Research Integration

NLP outputs can serve as alternative data inputs for factor research:

**Sentiment factor**: Aggregate sentiment scores across a universe of stocks can form a sentiment factor. The system SHOULD provide sentiment factor values aligned with the P2 backtest framework's date conventions.

**Event frequency factor**: The volume and type of events per ticker can form event-based factors. The system SHOULD expose event counts by type and time window.

**Policy sensitivity factor**: Tickers or sectors that appear in many policy documents may have higher policy sensitivity. The system SHOULD track policy exposure as a research metric.

**Requirement**: NLP-derived factor values MUST use the TradingCalendar from `synapse/core/market/calendar.py` for date alignment. Factor values MUST be aligned to trading day close (PM session end), not calendar day boundaries.

### 8.5 Output Schema for P3 Integration

All NLP outputs destined for the P3 event engine MUST implement the `BaseDetector` ABC interface. The detector implementations MUST:

1. Accept raw text or preprocessed text as input
2. Return a list of `Event` objects compatible with the P3 event schema
3. Include `event_type` mapped to P3's `EVENT_TYPES` taxonomy
4. Include `priority` mapped to P3's `PRIORITY_LEVELS`
5. Include `source_priority` mapped to P3's `SOURCE_PRIORITY` for deduplication

**Requirement**: Each NLP detector MUST register itself with `DetectorRegistry` at module import time. The detector registry name MUST follow the pattern `nlp_{task_type}` (e.g., `nlp_sentiment`, `nlp_event_extraction`). The system MUST support enabling/disabling individual detectors via configuration, allowing the user to control which NLP analyses run.

---

## Cross-Cutting Concerns

### C1. Error Handling for Domain Failures

The guidance specification (D-042) mandates graceful degradation. Domain-specific failure modes include:

| Failure Mode | Detection | Recovery |
|-------------|-----------|----------|
| Model load failure | Exception during model initialization | Return empty results + log warning |
| Unparseable text | Encoding errors, garbled text | Skip document + log with document_id |
| Empty text | Zero-length input | Return neutral/empty result immediately |
| Unknown abbreviation | Term not in expansion table | Pass through unexpanded + log discovery |
| Ambiguous entity | Multiple candidate matches | Return top-1 with confidence < 0.7 + log ambiguity |
| Lexicon gap | Term in text but not in lexicon | Skip term in scoring + log discovery |

**Requirement**: The system MUST NOT raise exceptions for domain-specific failures. All domain failures MUST be logged with sufficient context (document_id, text snippet, error type) for later analysis without breaking the research workflow.

### C2. Performance Budget

For a personal research tool processing batch data:

| Operation | Latency Target | Throughput Target |
|-----------|---------------|-------------------|
| Sentiment classification | < 50ms per document | > 20 docs/sec |
| NER extraction | < 100ms per document | > 10 docs/sec |
| Event extraction | < 200ms per document | > 5 docs/sec |
| Policy document processing | < 500ms per document | > 2 docs/sec |
| Full pipeline (all tasks) | < 1s per document | > 1 doc/sec |

**Requirement**: These targets are for CPU inference as specified in the non-goals (GPU optimization out of scope). The system SHOULD profile latency per task and report statistics in processing logs.

### C3. Lexicon Consistency with Existing Code

The existing `POSITIVE_LEXICON` and `NEGATIVE_LEXICON` in `synapse/event/social.py` MUST be treated as the authoritative seed for the expanded lexicon (F-044). The expanded lexicon MUST:

1. Include all 102 existing terms with their current polarity
2. Add new terms to existing categories or create new categories
3. Not change polarity of existing terms without explicit justification and changelog entry
4. Be loadable by the existing `LexiconAnalyzer` class with backward compatibility
5. Provide a migration path from hardcoded lists to YAML-based lexicon loading

**Requirement**: The system MUST provide a `LexiconAnalyzer` subclass or configuration that loads from the external lexicon file while maintaining the same `score()` and `score_batch()` API. Existing callers of `LexiconAnalyzer` MUST NOT break when the lexicon source changes from hardcoded to file-based.
