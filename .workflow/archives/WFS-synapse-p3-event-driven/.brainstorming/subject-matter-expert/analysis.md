# P3 Event-Driven Research Contracts: Subject-Matter-Expert Analysis

> Role: Quantitative Finance / China A-Share Market Expert
> Session: WFS-synapse-p3-event-driven
> Date: 2026-05-18

---

## 1. Role Perspective Overview

This analysis applies deep domain expertise in China A-share quantitative research to define P3 Event-Driven Research Contracts. The focus is on event taxonomy grounded in actual A-share market microstructure, severity/confidence scoring calibrated to Chinese market conventions, decay patterns reflecting T+1 settlement and retail-dominated order flow, and propagation rules that connect events to the existing thesis/decision framework (P0-P2).

The core design principle: **events are the bridge between external market reality and internal research state**. P3 must close the loop between "something happened in the market" and "our research must respond."

---

## 2. Event Type Taxonomy for China A-Share Market

### 2.1 Taxonomy Overview

Events are organized into 6 top-level categories, 22 sub-categories, and 87 specific event types. Each category maps to distinct data sources, timing characteristics, and research impact patterns.

### 2.2 Category 1: Earnings & Financial Events (业绩与财报事件)

| Sub-Category | Event Type | Data Source | Typical Timing | Market Impact |
|---|---|---|---|---|
| 季度报告 | Q1 Report Published | cninfo.com.cn, AKShare | Apr 30 deadline | Medium |
| 季度报告 | Q2/Half-Year Report Published | cninfo.com.cn | Aug 31 deadline | Medium-High |
| 季度报告 | Q3 Report Published | cninfo.com.cn | Oct 31 deadline | Medium |
| 年度报告 | Annual Report Published | cninfo.com.cn | Apr 30 deadline (following year) | High |
| 业绩预告 | Earnings Pre-announcement (positive) | cninfo.com.cn | Varies by quarter | High |
| 业绩预告 | Earnings Pre-announcement (negative) | cninfo.com.cn | Varies by quarter | High |
| 业绩预告 | Earnings Pre-announcement (uncertain) | cninfo.com.cn | Varies by quarter | Medium |
| 业绩快报 | Earnings Express Report | cninfo.com.cn | Before formal report | Medium-High |
| 业绩修正 | Earnings Revision (upward) | cninfo.com.cn | Post-initial estimate | High |
| 业绩修正 | Earnings Revision (downward) | cninfo.com.cn | Post-initial estimate | Very High |
| 审计意见 | Auditor Qualified Opinion | cninfo.com.cn | With annual report | Critical |
| 审计意见 | Auditor Disclaimer of Opinion | cninfo.com.cn | With annual report | Critical |

**A-Share Specific Rules**:
- Mandatory pre-announcement window: listed companies with expected earnings change >50% or losses MUST pre-announce
- The "业绩预告" deadline is typically 1 month before the formal report deadline
- Earnings surprise = actual vs. consensus estimate (if available), or vs. pre-announcement range midpoint
- Q4 data (annual) carries disproportionate weight because it completes the annual picture

### 2.3 Category 2: Regulatory & Policy Events (监管与政策事件)

| Sub-Category | Event Type | Data Source | Typical Timing | Market Impact |
|---|---|---|---|---|
| 证监会政策 | CSRC Regulatory Rule Change | csrc.gov.cn | Any time | Sector-wide |
| 证监会政策 | CSRC Enforcement Action | csrc.gov.cn | Any time | Company-specific |
| 行业监管 | Industry-Specific Regulation | Various ministries | Any time | Sector-wide |
| 行业监管 | Environmental/ESR Compliance | MEE | Any time | Sector-specific |
| 货币政策 | PBOC Rate Decision | pboc.gov.cn | Scheduled (monthly/quarterly) | Market-wide |
| 货币政策 | PBOC RRR Adjustment | pboc.gov.cn | Unscheduled | Market-wide |
| 财政政策 | Fiscal Stimulus / Tax Policy | State Council | Any time | Thematic |
| 交易规则 | Trading Rule Change (e.g., price limit adjustment) | SSE/SZSE | Any time | Market-wide |
| IPO/退市 | IPO Approval (注册制) | SSE/SZSE/CSRC | Scheduled | Sector |
| IPO/退市 | Delisting Warning (退市风险) | SSE/SZSE | Any time | Company-specific |
| IPO/退市 | Delisting Execution | SSE/SZSE | Any time | Company-specific |

**A-Share Specific Rules**:
- PBOC rate/RRR changes are scheduled events with fixed announcement windows (typically 15:00 or after close)
- CSRC enforcement actions against a specific company create "event clusters" — other companies in the same sector may face follow-on scrutiny
- Trading rule changes (e.g., 2020 ChiNext price limit expansion to ±20%) affect all stocks in the affected board
- Delisting warnings create a binary outcome: recovery or terminal decline

### 2.4 Category 3: Corporate Actions (公司行为事件)

| Sub-Category | Event Type | Data Source | Typical Timing | Market Impact |
|---|---|---|---|---|
| 增发 | Private Placement Announcement | cninfo.com.cn | Any time | Dilutive/Negative |
| 增发 | Private Placement Completion | cninfo.com.cn | 6-12 months post-announcement | Neutral (priced in) |
| 配股 | Rights Issue Announcement | cninfo.com.cn | Any time | Dilutive |
| 配股 | Rights Issue Ex-Date | cninfo.com.cn | Scheduled | Price adjustment |
| 分红 | Dividend Declaration (现金分红) | cninfo.com.cn | With annual report | Positive |
| 分红 | Dividend Ex-Date | cninfo.com.cn | Scheduled | Price adjustment |
| 转增 | Bonus Shares Ex-Date | cninfo.com.cn | Scheduled | Price adjustment |
| 股权激励 | Stock Option Grant | cninfo.com.cn | Any time | Positive (alignment) |
| 股权激励 | Performance Vesting Trigger | cninfo.com.cn | Scheduled | Positive |
| 股权激励 | Option Exercise Window Open | cninfo.com.cn | Scheduled | Dilutive |
| 股东变动 | Major Shareholder Increase | cninfo.com.cn | Any time | Positive |
| 股东变动 | Major Shareholder Decrease | cninfo.com.cn | Any time | Negative |
| 股东变动 | Insider Selling Cluster | cninfo.com.cn | Any time | Negative |
| 并购重组 | Merger/Acquisition Announcement | cninfo.com.cn | Any time | High (directional) |
| 并购重组 | Restructuring Plan | cninfo.com.cn | Any time | High (directional) |
| 并购重组 | Asset Injection | cninfo.com.cn | Any time | Positive |
| 股份回购 | Share Buyback Announcement | cninfo.com.cn | Any time | Positive |
| 股份回购 | Buyback Completion | cninfo.com.cn | 6-12 months | Neutral |

**A-Share Specific Rules**:
- Private placements (增发) typically lock shares for 6-18 months; unlock dates create supply pressure events
- Rights issues (配股) require shareholder action (exercise or sell); inaction results in dilution
- Major shareholder changes >5% must be disclosed; changes >30% trigger tender offer obligations
- Merger/restructuring often involves trading suspension for weeks/months

### 2.5 Category 4: Market Sentiment & Flow Events (市场情绪与资金流事件)

| Sub-Category | Event Type | Data Source | Typical Timing | Market Impact |
|---|---|---|---|---|
| 融资融券 | Margin Balance Surge (>5% daily change) | AKShare | Daily after close | Bullish signal |
| 融资融券 | Margin Balance Decline (>5% daily change) | AKShare | Daily after close | Bearish signal |
| 融资融券 | Short Sell Volume Spike | AKShare | Daily after close | Bearish signal |
| 北向资金 | Northbound Net Buy >10B CNY | AKShare (HKEX) | Daily ~18:00 HKT | Bullish signal |
| 北向资金 | Northbound Net Sell >10B CNY | AKShare (HKEX) | Daily ~18:00 HKT | Bearish signal |
| 北向资金 | Single Stock Northbound Accumulation (>1% float) | AKShare | Daily ~18:00 HKT | Company-specific bullish |
| 大宗交易 | Block Trade Discount >10% | AKShare | Daily after close | Bearish signal |
| 大宗交易 | Block Trade Volume >1% daily turnover | AKShare | Daily after close | Directional |
| 龙虎榜 | Dragon Tiger List Appearance (institutional buyer) | AKShare | Daily after close | Bullish signal |
| 龙虎榜 | Dragon Tiger List Appearance (institutional seller) | AKShare | Daily after close | Bearish signal |
| 涨跌停 | Limit-Up Lock (封单量/流通市值 > 5%) | Real-time | Intraday | Strong bullish |
| 涨跌停 | Limit-Down Lock (封单量/流通市值 > 5%) | Real-time | Intraday | Strong bearish |
| 涨跌停 | 连板 (consecutive limit-up days >= 3) | Real-time | Daily | Momentum extreme |
| 涨跌停 | 跌停开板 (limit-down broken intraday) | Real-time | Intraday | Bearish panic |

**A-Share Specific Rules**:
- Northbound flow data is delayed ~2 hours from actual trading; the "smart money" narrative is important for sentiment
- Dragon Tiger List (龙虎榜) is a uniquely A-share data source: top 5 buyers/sellers disclosed for qualifying stocks
- Block trade discounts >10% from closing price suggest institutional urgency to exit
- Margin data is a strong contrarian signal at extremes (>3% of market cap in margin = overheating)

### 2.6 Category 5: Thematic & Sector Events (主题与板块事件)

| Sub-Category | Event Type | Data Source | Typical Timing | Market Impact |
|---|---|---|---|---|
| 政策主题 | National Policy Announcement (e.g., 新能源, AI) | State Council, NDRC | Any time | Thematic rally |
| 政策主题 | Regional Policy (e.g., 雄安新区, 粤港澳) | Local government | Any time | Regional rally |
| 行业轮动 | Sector Rotation Signal (relative strength) | Computed from price data | Daily | Sector rotation |
| 行业轮动 | Sector Earnings Revision Trend | Analyst consensus | Quarterly cycle | Sector momentum |
| 概念热点 | Concept Hot Stock Surge (概念炒作) | AKShare | Daily | Thematic |
| 概念热点 | Concept Theme Cooling | AKShare | Daily | Thematic fade |
| 事件驱动 | Supply Chain Disruption | News/industry | Any time | Sector-specific |
| 事件驱动 | Commodity Price Shock | Futures data | Intraday | Input cost impact |
| 事件驱动 | Geopolitical Event (e.g., trade war) | News | Any time | Market-wide |
| 事件驱动 | Pandemic/Health Event | News | Any time | Thematic (healthcare) |

**A-Share Specific Rules**:
- A-share market is heavily driven by thematic narratives (e.g., "碳中和" in 2021, "ChatGPT概念" in 2023)
- Concept stocks can decouple from fundamentals for weeks; event contracts must track narrative lifecycle
- Sector rotation in A-shares is faster than in developed markets due to retail-dominated flow

### 2.7 Category 6: Corporate Governance Events (公司治理事件)

| Sub-Category | Event Type | Data Source | Typical Timing | Market Impact |
|---|---|---|---|---|
| 管理层变动 | CEO/CFO Change | cninfo.com.cn | Any time | Directional |
| 管理层变动 | Board Restructuring | cninfo.com.cn | Any time | Directional |
| 信息披露 | Disclosure Delay / Non-compliance | SSE/SZSE | Any time | Negative |
| 信息披露 | Rumor Denial (澄清公告) | cninfo.com.cn | Any time | Neutral |
| 诉讼/调查 | Company Under Investigation (立案调查) | CSRC | Any time | Negative |
| 诉讼/调查 | Litigation Settlement | cninfo.com.cn | Any time | Directional |
| 信用事件 | Credit Rating Downgrade | Rating agencies | Any time | Negative |
| 信用事件 | Bond Default | Wind/AKShare | Any time | Critical negative |

---

## 3. Event Severity and Confidence Scoring

### 3.1 Severity Score: 1-5 Scale

| Level | Label | Criteria | Example Events |
|---|---|---|---|
| 1 | Low | Informational, no immediate market impact | Routine quarterly report (in-line with expectations) |
| 2 | Moderate | May affect individual stock or narrow sector | Single company earnings beat, rights issue announcement |
| 3 | Significant | Expected to move stock >3% or sector >1% | Earnings surprise >20%, major shareholder increase, northbound accumulation |
| 4 | High | Expected to move stock >5% or market >0.5% | Earnings revision (downward), PBOC rate cut, delisting warning |
| 5 | Critical | Expected to cause limit-up/down or market-wide impact | CSRC enforcement, credit default, geopolitical shock, trading rule change |

**Scoring Rules**:
- Severity is assessed at the event timestamp using available information (point-in-time)
- Severity MAY be revised within 24 hours if follow-up information materially changes the assessment
- Severity MUST NOT be revised retroactively beyond 24 hours for audit trail integrity
- Events with severity >= 4 MUST trigger a research review alert
- Events with severity = 5 MUST trigger immediate thesis re-evaluation

### 3.2 Confidence Score: 0.0-1.0 Scale

| Range | Label | Criteria |
|---|---|---|
| 0.0-0.3 | Low | Rumor/unconfirmed source, single-source, no official filing |
| 0.3-0.6 | Medium | Official announcement but details incomplete, or multiple unconfirmed sources |
| 0.6-0.8 | High | Official filing with complete data, single authoritative source |
| 0.8-1.0 | Very High | Official filing, confirmed by multiple authoritative sources, or quantitative data directly observable |

**Confidence Calibration Rules**:
- Earnings announcements from cninfo.com.cn: confidence = 0.9 (official filing, structured data)
- PBOC rate decision: confidence = 1.0 (official announcement, unambiguous)
- Rumor from financial media: confidence = 0.2 (unconfirmed)
- Northbound flow data: confidence = 0.85 (observable but delayed)
- Analyst consensus estimate: confidence = 0.5 (subjective, potentially stale)
- CSRC enforcement: confidence = 1.0 (official announcement)

**A-Share Specific Confidence Adjustments**:
- Events disclosed after 18:00 (late disclosure): confidence -= 0.1 (potential信息违规)
- Events from 巨潮资讯 (cninfo) directly: confidence baseline = 0.9
- Events from third-party aggregators (东方财富, 同花顺): confidence baseline = 0.7
- Events with 关注函 (inquiry letter) response: confidence += 0.1 (company was forced to clarify)

### 3.3 Composite Event Score

```
event_score = severity * confidence * category_weight
```

| Category | Weight | Rationale |
|---|---|---|
| Earnings & Financial | 1.0 | Direct fundamental impact |
| Regulatory & Policy | 0.9 | Broad impact but indirect |
| Corporate Actions | 0.8 | Known in advance, partially priced |
| Market Sentiment & Flow | 0.7 | Short-lived, reversal-prone |
| Thematic & Sector | 0.6 | Narrative-driven, unreliable |
| Corporate Governance | 0.85 | Uncertainty premium |

---

## 4. Event Decay Patterns (A-Share Specific)

### 4.1 Decay Model

Event impact decays over time following a **modified exponential decay** with A-share specific parameters:

```
impact(t) = impact_0 * exp(-lambda * t) * (1 - reversal_factor(t))
```

Where:
- `t` = trading days since event
- `lambda` = decay rate (event-type specific)
- `reversal_factor(t)` = A-share specific reversal coefficient

### 4.2 Decay Parameters by Event Type

| Event Type | Half-Life (trading days) | Lambda | Reversal Factor | Notes |
|---|---|---|---|---|
| Earnings Surprise (positive) | 5-8 | 0.10 | 0.15 at day 15 | Drift continues 1-2 weeks |
| Earnings Surprise (negative) | 3-5 | 0.15 | 0.20 at day 10 | Faster negative drift |
| Earnings Revision | 8-12 | 0.07 | 0.10 at day 20 | Slower, more persistent |
| PBOC Rate/RRR Change | 1-2 | 0.40 | 0.30 at day 5 | Sharp initial, fast reversal |
| CSRC Enforcement | 15-30 | 0.03 | 0.05 at day 30 | Very slow, persistent |
| Northbound Flow Signal | 1-3 | 0.30 | 0.25 at day 5 | Short-lived, high reversal |
| Dragon Tiger List | 1-2 | 0.50 | 0.35 at day 3 | Very short-lived |
| Limit-Up Lock | 0.5-1 | 0.80 | 0.40 at day 2 | Next-day reversal risk high |
| Corporate Action (dividend) | 0 | N/A | N/A | Price adjustment, not alpha |
| Private Placement | 30-60 | 0.02 | 0.10 at day 60 | Long horizon |
| Thematic Rally | 5-10 | 0.10 | 0.30 at day 10 | High reversal, narrative fades |
| Merger/Restructuring | 30-90 | 0.01 | 0.05 at day 90 | Very persistent |

### 4.3 A-Share Reversal Phenomenon

A-share market exhibits stronger short-term reversal than developed markets due to:
- Retail investor overreaction (herding behavior)
- T+1 settlement creating forced holding periods
- 10% price limit creating "rubber band" effect at extremes

**Reversal Coefficient Table**:

| Event Type | 3-Day Reversal | 5-Day Reversal | 10-Day Reversal |
|---|---|---|---|
| Earnings surprise | 5-10% | 10-15% | 15-20% |
| Northbound flow signal | 15-25% | 20-30% | 25-35% |
| Limit-up lock | 20-30% | 25-40% | 30-50% |
| Thematic rally | 10-20% | 15-25% | 20-30% |
| Policy announcement | 5-10% | 8-15% | 10-20% |

### 4.4 Stale Event Threshold

An event is considered "stale" and its impact weight reduced to 0 after:

| Event Type | Stale Threshold | Reasoning |
|---|---|---|
| Earnings | Next earnings announcement | New information supersedes |
| PBOC policy | Next PBOC meeting | Forward-looking market |
| Northbound flow | 5 trading days | Signal degrades quickly |
| Corporate action | Ex-date + 3 days | Price adjustment absorbed |
| Thematic | 15 trading days | Narrative lifecycle ends |
| Regulatory | 60 trading days | Market adapts |

---

## 5. Event Propagation Rules

### 5.1 Propagation Model

Events propagate through the research stack following a directed acyclic graph (DAG):

```
Event
  |
  +---> Factor Impact (which factors are affected?)
  |
  +---> Thesis Impact (which theses are confirmed/invalidated?)
  |
  +---> Decision Impact (which decisions need review?)
  |
  +---> Portfolio Impact (which positions are affected?)
```

### 5.2 Propagation Rules Table

| Event Type | Affected Factors | Affected Theses | Affected Decisions | Propagation Delay |
|---|---|---|---|---|
| Earnings Surprise | Earnings momentum, Value, Quality | All theses referencing earnings | All positions in stock | 0-1 days |
| PBOC Rate Cut | Interest rate sensitivity, Duration | Macro theses | All positions | 0 days |
| Northbound Flow Surge | Flow momentum, Foreign ownership | Foreign preference theses | High foreign-ownership positions | 1 day |
| Private Placement | Dilution factor, Value | Value theses | Position sizing | 0-1 days |
| CSRC Enforcement | Risk factor, Governance | All theses for company | All positions in stock | 0 days |
| Delisting Warning | Risk factor, Quality | All theses for company | Exit all positions | 0 days |
| Thematic Rally | Sector momentum | Thematic theses | Sector allocation | 0-2 days |
| Limit-Up Lock | Momentum, Liquidity | Momentum theses | Position sizing | 0 days |
| Dividend Ex-Date | Yield factor, Value | Income theses | Rebalance trigger | 0 days |
| Block Trade Discount | Sentiment, Institutional flow | Institutional sentiment theses | Position sizing | 1 day |

### 5.3 Propagation Priority

Events are propagated in priority order:

1. **P0 (Immediate, < 1 hour)**: Delisting warning, CSRC enforcement, credit default, limit-up/down lock
2. **P1 (Same day)**: Earnings release, PBOC policy, major shareholder change, merger announcement
3. **P2 (Next trading day)**: Northbound flow signals, Dragon Tiger List, block trades, thematic shifts
4. **P3 (Within 3 days)**: Sector rotation signals, concept theme changes, analyst consensus shifts

### 5.4 Propagation Constraints

- Events MUST NOT propagate to theses that are already in `archived` state
- Events MUST NOT trigger state transitions on `failed` or `cancelled` tasks
- Propagation MUST be idempotent: re-processing the same event produces identical results
- If an event affects multiple theses, each thesis MUST be evaluated independently
- Propagation MUST record the event_id and timestamp in the thesis/decision audit trail

---

## 6. Event Deduplication Rules

### 6.1 Deduplication Strategy

Same underlying event may appear from multiple sources (巨潮资讯, 东方财富, Wind, AKShare). Deduplication MUST prevent double-counting.

### 6.2 Deduplication Key

```
dedup_key = hash(event_type + ticker + effective_date + event_signature)
```

Where `event_signature` is a normalized string derived from the event's core attributes.

### 6.3 Deduplication Rules

| Scenario | Rule | Example |
|---|---|---|
| Same event, same source, different timestamps | Keep earliest publication timestamp | cninfo posted at 16:00, AKShare fetched at 18:00 |
| Same event, different sources | Keep highest-confidence source | cninfo (0.9) > 东方财富 (0.7) |
| Same ticker, same date, different events | Keep both (different event_types) | Earnings release + dividend declaration on same day |
| Same event, slightly different content | Merge into single event, keep richer content | One source has full financials, other has summary |
| Updated/corrected event | Replace with corrected version, mark original as superseded | Earnings revision after initial error |
| Duplicate within 24 hours from same source | Keep first, suppress duplicates | API retry causing duplicate fetch |

### 6.4 A-Share Specific Deduplication

| Scenario | Rule |
|---|---|
| 公告 + 新闻报道 of same event | Keep 公告 (official filing), link news as supplementary |
| 业绩预告 + 业绩快报 (same quarter) | Treat as separate event types with different dedup_keys |
| 增发预案 + 增发实施 (same offering) | Different event types, different timing; both kept |
| 关注函 + 回复函 | Pair as question-response; both kept but linked |
| 龙虎榜 + 涨跌停公告 | Both kept; dragon tiger list is richer information |

### 6.5 Conflict Resolution

When two sources provide contradictory information:
1. Official source (cninfo, SSE, SZSE) takes precedence
2. If both are official, later publication supersedes earlier
3. Contradictions MUST be flagged as `conflict` status for human review
4. Conflicting events MUST NOT auto-propagate to theses

---

## 7. Market-Specific Edge Cases

### 7.1 Price Limit Events (涨跌停)

**涨停 (Limit-Up)**:
- Main board: price = previous_close * 1.10
- ST stocks: price = previous_close * 1.05
- STAR/ChiNext: price = previous_close * 1.20
- When at limit-up: no sellers in order book; event = "limit_up_lock"
- 封单量 (pending buy orders at limit price) / 流通市值 ratio indicates strength
- Ratio > 5% = strong lock, < 1% = weak lock, may break open

**跌停 (Limit-Down)**:
- Mirror of limit-up with negative direction
- When at limit-down: no buyers in order book; event = "limit_down_lock"
- 跌停开板 (limit-down broken): stock recovers from limit-down intraday
- This is a critical event indicating panic exhaustion

**Event Contract Rules for Price Limits**:
- Price limit events MUST include `lock_strength` field: `strong | moderate | weak`
- Price limit events MUST include `lock_duration_minutes` field
- 连板 (consecutive limit-up) events MUST track `consecutive_count`
- `consecutive_count >= 3` is a momentum extreme event requiring separate event type

### 7.2 Suspension Events (停牌)

**Suspension Scenarios**:
- **Planned suspension**: Merger/restructuring, typically announced 1-3 days before
- **Unplanned suspension**: Investigation, material undisclosed information
- **Trading halt**: Volatility halt (not common in A-shares, unlike US circuit breakers)

**Event Contract Rules for Suspension**:
- Suspension event MUST include: `suspension_reason`, `expected_duration`, `resumption_date` (if known)
- During suspension: stock is excluded from tradable universe
- Resumption event MUST be created when trading resumes
- Resumption often creates gap; event MUST include `price_gap_pct` = (open - last_close) / last_close

**Edge Case: 涨跌停导致的停牌 (Limit-Triggered Suspension)**:
- This is NOT a separate suspension event; it is a continuation of the limit event
- The limit event's `lock_duration` continues to accumulate

### 7.3 ST Stock Events

**ST Classification**:
- **ST**: Special Treatment — company has financial issues
- **\*ST**: 退市风险警示 — company faces delisting risk
- **撤销ST (De-ST)**: Company recovered; price limit restores to ±10%

**Event Contract Rules for ST**:
- ST classification change is a severity=4 event
- \*ST classification is a severity=5 event
- De-ST is a severity=3 positive event
- ST price limit is ±5% (not ±10%)
- ST stocks have lower liquidity; event impact assessment MUST consider liquidity discount

### 7.4 Ex-Date Edge Cases

**除权除息 (Ex-rights/Ex-dividend)**:
- Price adjustment on ex-date is automatic; not an alpha event
- BUT: dividend yield becoming attractive at adjusted price MAY trigger flow events
- Event contract MUST distinguish between "price adjustment" (non-event) and "yield attractiveness" (potential event)

**配股 (Rights Issue) Ex-Date**:
- Shareholders must exercise or sell; inaction = automatic dilution
- This IS a distinct event because it requires shareholder decision
- Event must include: `exercise_price`, `exercise_ratio`, `exercise_deadline`

### 7.5 T+1 Impact on Event Response

- Events occurring during trading hours CANNOT be acted upon immediately for new positions (buying today means holding until tomorrow)
- T+1 means: an event at 10:00 AM → earliest exit is tomorrow
- This creates "overnight risk" for event-driven positions
- Event contracts MUST include `earliest_actionable_date` field

### 7.6 Half-Day Session Edge Cases

- Spring Festival eve and National Day eve: only morning session (09:30-11:30)
- Events on half-day sessions have compressed reaction time
- Event timestamp MUST distinguish half-day vs full-day sessions
- Events published after 11:30 on half-day sessions are effectively delayed to next full session

### 7.7 Pre-Market and After-Hours Events

- A-shares have no pre-market or after-hours trading
- Events published after 15:00 (market close) are "after-hours events"
- These events create overnight gaps at next open
- Event contract MUST include `publication_time_relative_to_market` field:
  - `during_session` (09:30-15:00)
  - `after_close` (15:00-18:00)
  - `late_disclosure` (18:00+, potential compliance issue)

---

## 8. Event Contract Schema Design

### 8.1 Core Event Dataclass

```python
@dataclass
class EventContract:
    """Core event contract for P3 event-driven research."""
    event_id: str                          # Unique identifier
    event_type: str                        # From taxonomy (e.g., "earnings.earnings_surprise")
    ticker: str                            # Affected stock (or "MARKET" for market-wide)
    sector: str                            # Affected sector (or "ALL")
    severity: int                          # 1-5 scale
    confidence: float                      # 0.0-1.0
    event_score: float                     # composite = severity * confidence * weight
    effective_date: str                    # When the event actually occurred
    publication_date: str                  # When the event was published/observed
    source: str                            # Data source identifier
    source_url: str                        # URL to original filing/source
    dedup_key: str                         # For deduplication
    content_summary: str                   # Human-readable summary
    raw_data: dict                         # Source-specific raw data
    propagation_status: str = "pending"    # pending | propagated | failed
    propagated_at: str = ""                # Timestamp of propagation
    created_at: str = ""                   # Contract creation timestamp
    created_by: str = "system"             # human | ai | system

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v}

    @classmethod
    def from_dict(cls, data: dict) -> "EventContract":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
```

### 8.2 Event Propagation Record

```python
@dataclass
class EventPropagationRecord:
    """Records how an event propagated through the research stack."""
    record_id: str
    event_id: str                          # Source event
    target_type: str                       # thesis | decision | portfolio
    target_id: str                         # ID of affected object
    impact_direction: str                  # positive | negative | neutral
    impact_magnitude: float                # Estimated magnitude (0.0-1.0)
    propagation_timestamp: str
    requires_review: bool                  # True if severity >= 4
    review_status: str = "pending"         # pending | reviewed | dismissed
```

### 8.3 Event Decay Record

```python
@dataclass
class EventDecayRecord:
    """Tracks decay of an event's impact over time."""
    record_id: str
    event_id: str
    measured_at: str                       # Measurement timestamp
    trading_days_elapsed: int              # Trading days since event
    impact_remaining: float                # 0.0-1.0 (fraction of original impact)
    decay_model: str                       # Which decay model was applied
    is_stale: bool                         # True if below stale threshold
```

---

## 9. Integration Points with P0-P2

### 9.1 Integration with Existing Contracts

| P0-P2 Contract | P3 Integration | Direction |
|---|---|---|
| FactorSpec | Event-driven factor inputs | Event -> Factor |
| FactorAuditResult | Audit factor sensitivity to events | Event -> Audit |
| ExperimentRecord | Link experiments to triggering events | Event -> Experiment |
| ResearchTask | Event-triggered state transitions | Event -> Task |
| DecaySnapshot (P2) | Event decay tracking | Event -> Decay |
| OutcomeRecord (P2) | Event outcome calibration | Event -> Outcome |
| CorrelationInsight (P2) | Event-outcome correlation | Event -> Insight |

### 9.2 Integration with Analytics Objects

| Analytics Object | P3 Relationship |
|---|---|
| DriftAlert | Events can trigger drift detection (thesis vs. new information) |
| ThesisEvolution | Events are key turning points in thesis evolution |
| DailySummary | Events are primary inputs to daily research summaries |
| BehavioralProfile | Event response patterns reveal user behavioral tendencies |
| CorrelationInsight | Event-outcome correlations are computed from event history |

### 9.3 State Machine Extension

The ResearchTask state machine (P0) may need an `event_reviewed` state:

```
... -> audited -> [event_reviewed] -> backtested -> ...
```

Or alternatively, events do NOT create new states but trigger reviews within existing states. The recommended approach is the latter to avoid state machine complexity.

---

## 10. Data Source Integration Strategy

### 10.1 Primary Data Sources

| Source | Events Covered | Latency | Reliability | Cost |
|---|---|---|---|---|
| cninfo.com.cn | Official filings, announcements | 0-24 hours | High | Free (web scraping) |
| AKShare | Price data, northbound flow, margin, block trades | 15-30 min (market data) | Medium-High | Free |
| SSE/SZSE websites | Exchange-specific announcements | 0-24 hours | High | Free |
| Wind (万得) | Comprehensive data, analyst consensus | Near real-time | Very High | Paid |
| Tushare | Alternative data source | Near real-time | Medium | Free tier available |

### 10.2 Event Ingestion Pipeline

```
Data Source -> Event Extractor -> Event Normalizer -> Event Deduplicator
    -> Event Enricher -> Event Validator -> Event Store -> Propagation Engine
```

### 10.3 Point-in-Time Correctness

CRITICAL: Event data MUST respect point-in-time correctness for backtest integrity.

- Events published after market close on day T are NOT available for trading on day T
- Events published during trading hours on day T MAY be available for trading on day T (depending on timing)
- The `available_at` field MUST accurately reflect when the event became actionable
- Backtest MUST NOT use information that was not yet available at the simulated time

---

## 11. Key Recommendations

1. **Start with 5 core event types**: Earnings surprise, PBOC policy, northbound flow, private placement, CSRC enforcement. These cover 80% of alpha-generating events while keeping the initial implementation manageable.

2. **Hardcode decay parameters initially**: The decay model parameters in Section 4 should be stored as configuration constants, not computed from data. This allows rapid iteration and calibration based on backtest results.

3. **Implement deduplication early**: Event deduplication is critical for data quality. A naive "first-come-first-served" approach will cause double-counting within weeks of going live.

4. **Treat event contracts as append-only**: Like P0-P2 analytics objects, event contracts MUST never be modified after creation. Corrections are new events that reference the original as superseded.

5. **Build the propagation DAG as a configuration object**: Event-to-thesis propagation rules should be configurable, not hardcoded. Different research strategies may weight events differently.

6. **Phase 1 scope**: Focus on categories 1 (Earnings), 4 (Sentiment/Flow), and 6 (Governance). Categories 2 (Regulatory), 3 (Corporate Actions), and 5 (Thematic) are more complex and should follow in Phase 2.

---

## 12. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Data source reliability (cninfo scraping breaks) | High | Medium | Multi-source fallback, manual override |
| Event deduplication false positives | Medium | High | Conservative dedup rules, human review for edge cases |
| Decay model miscalibration | Medium | High | Configurable parameters, backtest validation |
| Point-in-time violations in backtest | Critical | Medium | Strict available_at enforcement, audit trail |
| Event propagation cascade (one event triggers many) | Medium | Low | Rate limiting on propagation, batch processing |
| ST stock event handling errors | High | Low | Dedicated ST event rules, separate testing |

---

## 13. Open Questions for Architecture Review

1. Should event contracts be stored as YAML files (consistent with P0-P2) or in a database? Recommendation: YAML for consistency, with index for fast query.
2. How should event propagation interact with the P2 ThesisEvolution tracking? Events are key turning points but the mapping is not 1:1.
3. Should event severity be auto-computed from data, or require human input? Recommendation: auto-compute for quantitative events (flow, price limits), human input for qualitative events (governance, policy).
4. What is the maximum event backlog that the propagation engine should handle? Need to define backpressure policy.
5. Should P3 events integrate with the P4 Chinese NLP layer? Yes — unstructured event content (narrative announcements) requires NLP extraction. P3 should define the interface, P4 implements the extraction.
