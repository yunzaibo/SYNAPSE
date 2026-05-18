# China Market Semantics

## Purpose

Define the semantic primitives unique to China A-shares that SYNAPSE must model.

## Scope

P1 = China Market Semantics Layer only.

This document freezes the semantic definitions. Implementation is P1 scope.

## Semantic Primitives

### 1. Trading Calendar Semantics

```yaml
exchange: SSE | SZSE
trading_days: ~242/year
half_days: [Spring Festival eve, National Day eve]
holidays: annual (State Council announcement)
 weekend: Saturday, Sunday
```

**Rules**:
- No trading on non-trading days
- Half-day sessions end at 11:30 AM (morning session only)
- Full sessions: 09:30-11:30, 13:00-15:00
- Call auction: 09:15-09:25 (opening), 14:57-15:00 (closing)

### 2. T+1 Semantics

```yaml
settlement: T+1
constraint: shares_bought_today_cannot_sell_until_tomorrow
implication: no_intraday_reversal
```

**Rules**:
- Buy today → earliest sell is tomorrow
- Sell today → cash available for buying today
- Short selling available via margin account only (limited availability)
- Backtest must track purchase date per position

### 3. Price Limit Semantics

```yaml
main_board: ±10%
st_stocks: ±5%
star_market: ±20%
chinext: ±20% (since 2020-08-24)
bse: ±30%
```

**Rules**:
- Price limit based on previous close (not today's open)
- Limit-up: price = previous_close × 1.10, rounded to 2 decimals
- Limit-down: price = previous_close × 0.90, rounded to 2 decimals
- When at limit, trading continues but price cannot move beyond
- Limit-up with no sellers: order book is empty on ask side
- Limit-down with no buyers: order book is empty on bid side

### 4. Suspension Semantics

```yaml
reasons: [merger, investigation, restructuring,重大事项]
frequency: ~5-10% of universe on any day
impact: stock_cannot_be_traded
resumption: often_creates_price_gaps
```

**Rules**:
- Suspended stocks excluded from tradable universe
- Position in suspended stock is frozen (cannot buy or sell)
- Resumption price may gap significantly from pre-suspension close
- Backtest must handle: exclude from rebalance, or model as frozen position

### 5. Corporate Action Semantics

```yaml
types:
  - 除权除息 (ex_rights_ex_dividend)
  - 配股 (rights_issue)
  - 增发 (private_placement)
  - 转增股 (bonus_shares)
  - 缩股 (share_consolidation)
adjustment: price_adjusted_on_ex_date
```

**Rules**:
- Price adjusted on ex-date to reflect corporate action
- Adjustment factors available via AKShare (`stock_zh_a_hist` with `adjust="qfq"` or `adjust="hfq"`)
- Forward adjustment (前复权) vs backward adjustment (后复权) vs no adjustment
- SYNAPSE default: forward adjustment (前复权) for factor research

### 6. Northbound Flow Semantics

```yaml
channels:
  - 港股通-沪 (Shanghai Connect)
  - 港股通-深 (Shenzhen Connect)
data:
  - daily_net_buy: float
  - cumulative_holdings: float
  - top_buy_stocks: list
  - top_sell_stocks: list
```

**Rules**:
- Northbound flow reflects foreign investor sentiment
- Daily data available after market close (typically 18:00-19:00 HKT)
- Can be used as factor: northbound momentum, northbound concentration
- Data source: AKShare (`stock_hsgt_north_net_flow_in_em`)

### 7. Benchmark/Index Semantics

```yaml
primary:
  - CSI300: 沪深300 (large-cap)
  - CSI500: 中证500 (mid-cap)
secondary:
  - SSE50: 上证50 (mega-cap)
  - CSI1000: 中证1000 (small-cap)
  - ChiNext: 创业板指 (growth)
  - STAR50: 科创50 (innovation)
```

**Rules**:
- Default benchmark: CSI300
- Universe construction should reference index constituents
- Index rebalance dates affect factor research (survivorship bias)
- Point-in-time index composition required for accurate backtest

### 8. Event Timestamp Semantics

```yaml
event_types:
  - 公告 (announcement): company disclosures
  - 政策 (policy): government/regulatory announcements
  - 业绩 (earnings): quarterly/annual results
  - 风险提示 (risk_warning): risk disclosures
  - 龙虎榜 (dragon_tiger): top buyer/seller lists
timing:
  - 公告: typically after market close (15:00-18:00)
  - 政策: any time, market-moving
  - 业绩: pre-announce windows, quarterly cycle
```

**Rules**:
- Events have effective timestamp and publication timestamp
- Market reaction may occur at different time than publication
- Backtest must use correct timestamp to avoid look-ahead bias
- Event data is P2 scope (AnnouncementContract, PolicyEventContract)

### 9. Announcement Availability Semantics

```yaml
sources:
  - 巨潮资讯 (cninfo.com.cn): official disclosure platform
  - 上交所 (sse.com.cn): Shanghai exchange
  - 深交所 (szse.cn): Shenzhen exchange
availability:
  - real_time: some announcements
  - delayed: most announcements (after hours)
  - structured: financial statements
  - unstructured: narrative announcements
```

**Rules**:
- Structured data (financials) available in tabular format
- Unstructured data (narrative announcements) requires NLP (P3 scope)
- Availability timing affects factor construction (cannot use data not yet published)
- Point-in-time data loading required

## Implementation Boundary

| Semantic | P1 Scope | P2 Scope | P3 Scope |
|----------|----------|----------|----------|
| Trading Calendar | Yes | - | - |
| T+1 | Yes | - | - |
| Price Limits | Yes | - | - |
| Suspension | Yes | - | - |
| Corporate Actions | Yes | - | - |
| Northbound Flow | Yes (data) | - | - |
| Benchmark/Index | Yes | - | - |
| Event Timestamp | Yes (definition) | Yes (implementation) | - |
| Announcement Availability | Yes (definition) | Yes (ingestion) | Yes (NLP) |

## Data Sources for P1

| Semantic | Data Source | API |
|----------|------------|-----|
| Trading Calendar | AKShare | `tool_trade_date_hist_sina` |
| T+1 | Hardcoded rule | N/A |
| Price Limits | AKShare | `stock_zh_a_spot_em` (includes limit prices) |
| Suspension | AKShare | `stock_zh_a_spot_em` (status field) |
| Corporate Actions | AKShare | `stock_zh_a_hist` (adjust parameter) |
| Northbound Flow | AKShare | `stock_hsgt_north_net_flow_in_em` |
| Benchmark | AKShare | `index_zh_a_hist` |
| Announcement | cninfo.com.cn | Web scraping (P2) |
