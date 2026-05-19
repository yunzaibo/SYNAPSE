# P1 Market Semantics Foundation — A-Share Domain Expert Analysis

## 1. Trading Calendar Edge Cases

### Current Gap in `calendar.py`

The existing `is_trading_day()` uses a two-step check: weekday filter then holiday exclusion. This is structurally sound but has one blind spot.

###补班日 (Makeup Workdays)

**Business rule**: Weekends designated as workdays by the State Council are NOT trading days. The SSE/SZSE never open on Saturday or Sunday regardless of national workday status.

**Current code is correct**: `weekday in _WEEKEND` check runs first, so a Saturday that is a makeup workday correctly returns False. No change needed.

### Holiday-Shifted Weekdays (Critical Gap)

**Business rule**: When the State Council announces holiday adjustments, it often shifts a nearby weekend into the holiday block and designates a previously-holiday weekday as a compensatory trading day. Example — 2024 Spring Festival: Feb 4 (Sun) becomes a workday, while Feb 18 (Sun) is the actual holiday. The net effect is that **some weekdays that appear to be holidays are actually trading days, and some weekend days that appear to be workdays are not**.

**Impact**: If a user queries "is Feb 18, 2024 a trading day?" the current code returns True (it is a Sunday, not in CHINA_HOLIDAYS). But Feb 18 is actually a holiday. Conversely, Feb 4 is a Sunday and correctly returns False.

**Fix required**: Maintain a `CHINA_TRADING_DAYS` override set — explicit dates that are trading days despite being weekdays in the holiday block. Currently the hardcoded holidays for 2024-2026 already encode the correct holidays, so this is mostly a maintenance concern. The real risk is **adding new years without verifying the shifted days**.

### Long-Holiday Gap Effects

**Business rule**: After Spring Festival (7-8 days) or National Day (7 days), the first trading day back often has pent-up order flow. `trading_days_between()` is used for return calculations — a 7-day gap produces a larger implied return than a 2-day gap.

**Implementation note**: No special logic needed, but downstream consumers (e.g., volatility calculations) should be aware that `return = close[-1]/close[0] - 1` over a 7-day gap is not comparable to a 2-day gap. Consider normalizing by actual calendar days, not trading days.

### Priority: P0

| Rule | Pitfall | Data Required |
|------|---------|---------------|
| Weekends always non-trading | Forgetting to check weekday before holiday | None (built-in) |
| Holiday-shifted weekdays need override set | Hardcoding 2025 holidays from 2024 template | State Council annual announcement |
| Long gaps affect return normalization | Naive `trading_days_between` for annualized metrics | None |

---

## 2. Price Limit Nuances

### Current Coverage in `semantics.py`

`SymbolType` enum covers 5 types. `PRICE_LIMITS` dict maps each to a percentage. Missing: IPO first-day, intraday halt, and rounding.

### IPO First-Day (注册制新股)

**Business rule**: Under the registration system (注册制), new shares have NO price limit on their first trading day. On day 2+, normal limits apply.

**Implementation**: `is_ipo_first_day(symbol: str, listing_date: date, current_date: date) -> bool`. Needs a listing_date data source. For P1, this can be a manual override set; for P5, pull from exchange IPO data.

### Intraday Halt (盘中临停)

**Business rule**:
- 科创板/创业板: First halt at ±30% from open, resumes after 10 min; second halt at ±60%, resumes after 10 min; beyond that, continuous trading until close.
- 主板 (2020 reform): No intraday halt, only daily limit.

**Impact on data**: During halt periods, no trades execute. If building tick-level analytics, halt timestamps matter. For daily OHLCV, this is a no-op — the final close still respects the daily limit.

**Priority**: P2 for daily-level systems, P0 for tick-level.

### Price Limit Calculation Precision

**Business rule**: Limit prices are rounded to the nearest fen (0.01 CNY). The rounding method matters:

```python
# WRONG: float arithmetic
limit_up = round(close * 1.10, 2)  # 13.20 for close=12.00 ✓, but 26.41 for close=24.01 ✗

# CORRECT: Decimal with quantize
from decimal import Decimal, ROUND_HALF_UP
limit_up = (close_dec * Decimal("1.10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

**Pitfall**: `24.01 * 1.10` in float = `26.411000000000002`, `round()` gives `26.41`. But `26.411` should round to `26.41`. The edge case is values like `x.x05` — banker's rounding (`round()`) rounds to even, while `ROUND_HALF_UP` rounds away from zero. Chinese exchanges use **ROUND_HALF_UP** (四舍五入).

**The existing `Decimal` usage in semantics.py is correct.** Ensure all downstream code uses `Decimal` for limit price calculations, never `float`.

### Priority: P0

| Rule | Pitfall | Data Required |
|------|---------|---------------|
| IPO first day: no limit | Applying ±10% to new listings | listing_date per symbol |
| 科创板/创业板 intraday halt at ±30%/±60% | Only relevant for tick data | None for daily OHLCV |
| Limit price = ROUND_HALF_UP to fen | Using float or banker's rounding | None |

---

## 3. Ex-Right (复权) Specifics

### Why This Matters for SYNAPSE

Every downstream feature (Watchlist returns, Position Monitor P&L, Decision Memory backtests) depends on correctly adjusted prices. Unadjusted prices produce false signals at every dividend/split event.

### Business Rules

| Event | 复权处理 | 复权因子 |
|-------|---------|---------|
| 现金分红 (cash dividend) | 除息: price drops by dividend amount | factor < 1.0 |
| 送股 (bonus shares) | 除权: price diluted by new shares | factor < 1.0 |
| 转增 (capital reserve to shares) | 除权: same as 送股 | factor < 1.0 |
| 配股 (rights issue) | 除权: price adjusted by issue price | factor < 1.0 |
| 增发 (secondary offering) | Less common impact on price | factor ≈ 1.0 |

### 前复权 vs 后复权

- **前复权 (forward-adjusted)**: Adjusts historical prices to match current price level. Best for: chart visualization, current-price comparisons, technical indicators. **Use this as default.**
- **后复权 (backward-adjusted)**: Adjusts current price to match historical level. Best for: long-term return calculations, backtesting buy-and-hold.

**Recommendation for SYNAPSE**: Default to 前复权 for display and user-facing features. Use 后复权 internally for cumulative return calculations. Store the raw 复权因子 so both can be computed on the fly.

### High-Bonus Shares (高送转)

**Business rule**: 10送10 (1:1 bonus) halves the price. The 复权因子 becomes 0.5 (approximately). Combined with cash dividends, the factor compounds.

**Pitfall**: Some data providers report 复权因子 inconsistently for high-ratio events. Validate that `adjusted_close = raw_close * factor` holds for known events.

### Data Requirements

- Adjustment factor per symbol per date (from data provider)
- Corporate action calendar (dividend公告日, 除权除息日, 股权登记日)
- For P1: accept pre-computed factors from data source; for P5: compute from raw corporate actions

### Priority: P1

| Rule | Pitfall | Data Required |
|------|---------|---------------|
| Forward-adjusted for display | Using raw prices in return calculations | 复权因子 per symbol-date |
| Backward-adjusted for cumulative returns | Mixing adjusted/unadjusted in same series | 同上 |
| Factor validation: adj_close = raw_close * factor | Trusting provider factors blindly | Raw OHLCV + factors |
| 除权除息日跳空 is not a signal | Treating dividend drops as price crashes | Corporate action calendar |

---

## 4. Northbound Flow (北向资金)

### Architecture Note

北向资金 is consumed by the Watchlist and Decision Memory features but is NOT part of core price semantics. It belongs in the data layer, not the semantics layer. However, the semantic definitions (what净流入 means, quota rules) should be documented here.

### Business Rules

| Concept | Definition | Pitfall |
|---------|-----------|---------|
| 沪股通 quota | Daily aggregate quota: 520 billion CNY (net buy limit) | Individual stock quota: 10% of free float |
| 深股通 quota | Same 520 billion CNY | Quota rarely binds in practice; historical usage < 5% |
| 净流入 (net inflow) | Buy amount minus sell amount | ≠ 成交额 (turnover). Net can be negative |
| 成交额 (turnover) | Total buy + sell amount | Much larger than net; noisy signal |
| 盘中实时 vs 收盘 | Real-time data available ~every 5 min during trading; final data after 15:00 close | Real-time has sampling error; final data is authoritative |

### 假北向 (Disguised Northbound Flow)

**Business rule**: Some mainland capital uses Hong Kong-domiciled entities to trade through Stock Connect, creating fake "northbound" signals. Detection heuristic:
- Unusual concentration in small-cap stocks not typically held by foreign institutions
- Sudden large inflows without corresponding H-share or ADR activity
- Flow patterns that correlate more with domestic sentiment than global factors

**Implementation**: For P1, this is documentation-only. For P2+, implement a simple anomaly score based on stock cap tier and flow magnitude.

### Priority: P1 (definitions), P2 (analysis features)

| Rule | Pitfall | Data Required |
|------|---------|---------------|
| Net inflow ≠ turnover | Using turnover as "northbound signal" | 北向成交明细 |
| Real-time data is approximate | Making decisions on incomplete intraday data | Real-time feed + post-close final |
| 520B quota rarely binds | Over-engineering quota exhaustion logic | Quota usage stats |
| 假北向 exists | Treating all northbound as foreign conviction | Trading pattern data |

---

## 5. Index Constituent (指数成分)

### Business Rules

| Index | Adjustment Frequency | Announcement Lead Time | Effective Date |
|-------|---------------------|----------------------|----------------|
| 沪深300 | Semi-annual (Jun/Dec) | ~2 weeks before | Quarterly review day |
| 中证500 | Semi-annual (Jun/Dec) | ~2 weeks before | Quarterly review day |
| 中证1000 | Semi-annual (Jun/Dec) | ~2 weeks before | Quarterly review day |
| 创业板指 | Quarterly | ~1 week before | Review day |
| 科创50 | Quarterly | ~1 week before | Review day |

### Temporary Adjustments

**Business rule**: Indices remove components immediately upon:
- ST designation (Special Treatment)
- Delisting risk (退市风险警示, *ST)
- Suspension exceeding threshold (varies by index)

**Impact**: Position Monitor must flag when a held stock is removed from its benchmark index. This changes the "benchmark-relative" context.

### Weight Calculation

**Business rule**: Most A-share indices use **free-float market cap weighting** (自由流通市值加权):

```
weight_i = (price_i * free_float_shares_i) / sum(price_j * free_float_shares_j for all j in index)
```

**Pitfall**: Total market cap ≠ free-float market cap. State-owned shares, locked strategic holdings, and restricted shares are excluded. Using total market cap inflates weights of SOE-heavy components.

### Forward-Looking Adjustments

**Business rule**: When an index announces a component change, the effective date is in the future. Between announcement and effective date, the "expected" new component may experience price movement (index fund front-running).

**Implementation**: Store `announcement_date` and `effective_date` separately. Decision Memory should tag trades in this window as "index-rebalancing-adjacent."

### Priority: P1 (constituent lists), P2 (weight/adjustment logic)

| Rule | Pitfall | Data Required |
|------|---------|---------------|
| Semi-annual/quarterly rebalance | Using stale constituent lists | Index constituent snapshots |
| Remove on ST/delisting | Holding removed component without notification | ST designation feed |
| Free-float weighting | Using total market cap | Free-float share data |
| Announcement vs effective date gap | Missing front-running window | Index announcement calendar |

---

## Cross-Cutting Concerns

### Data Freshness Requirements

| Data Type | Max Staleness | Source |
|-----------|--------------|--------|
| Trading calendar | 1 year (hardcoded OK) | State Council |
| Price limits | Real-time (symbol type changes) | Exchange |
| 复权因子 | T+1 (after corporate action) | Data provider |
| 北向资金 | T+1 (final), 5min (real-time) | HKEX/SSE/SZSE |
| 指数成分 | Per adjustment schedule | Index provider |

### Existing Code Gaps Summary

| File | Gap | Priority |
|------|-----|----------|
| `calendar.py` | No `CHINA_TRADING_DAYS` override set for shifted weekdays | P1 |
| `semantics.py` | No IPO first-day exception | P0 |
| `semantics.py` | No intraday halt (P2, not needed for daily OHLCV) | P2 |
| `semantics.py` | Missing `ROUND_HALF_UP` documentation (Decimal usage is correct) | P2 |
| (new) `adjustment.py` | No 复权 logic anywhere | P1 |
| (new) `northbound.py` | No 北向 data definitions | P1 |
| (new) `constituent.py` | No 指数成分 handling | P1 |
