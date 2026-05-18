# Market Domain Assumptions

## Purpose

Freeze market-specific assumptions that affect all layers of SYNAPSE.

## Accepted Market Domain

**China A-Shares** (ADR-005, ADR-006)

## Market Characteristics

### Trading Calendar

- Shanghai Stock Exchange (SSE) and Shenzhen Stock Exchange (SZSE)
- ~242 trading days per year (fewer than US due to longer holidays)
- Half-day sessions before major holidays (Spring Festival, National Day)
- Holiday calendar shifts annually (set by State Council)
- No trading on weekends

### Settlement

- **T+1 settlement** — shares bought today cannot be sold until tomorrow
- Implication: no intraday reversal, no day-trading on long positions
- Backtest must enforce T+1 constraint

### Price Limits

- **Main board**: ±10% daily price limit (based on previous close)
- **ST stocks**: ±5% daily price limit
- **STAR Market (科创板)**: ±20% daily price limit
- **ChiNext (创业板)**: ±20% daily price limit (since 2020 reform)
- **Beijing Stock Exchange**: ±30% daily price limit
- When price hits limit, trading continues but price cannot move beyond limit
- Limit-up with no sellers = cannot buy; limit-down with no buyers = cannot sell

### Suspension

- Stocks can be suspended for various reasons (merger, investigation, restructuring)
- ~5-10% of A-shares may be suspended on any given day
- Suspended stocks cannot be traded
- Backtest must handle suspension (exclude from universe or model as frozen position)
- Resumption often creates price gaps

### Corporate Actions

- **除权除息 (Ex-rights/Ex-dividend)**: Price adjusted on ex-date
- **配股 (Rights issue)**: Existing shareholders can subscribe at discount
- **增发 (Private placement)**: New shares issued to specific investors
- **转增股 (Bonus shares)**: Free shares from capital reserve
- Adjustment factors available via AKShare but less standardized than CRSP

### Transaction Costs

- **Commission**: 0.02-0.03% (negotiable, minimum 5 yuan per trade)
- **Stamp duty**: 0.1% (sell-side only, reduced from 0.1% to 0.05% in 2023)
- **Transfer fee**: 0.001% (Shanghai only, for SSE settlement)
- **No SEC-style filing fees**

### Capital Flow

- **Northbound flow (北向资金)**: Foreign investors buying A-shares via Stock Connect (Shanghai-Hong Kong, Shenzhen-Hong Kong)
- **Southbound flow (南向资金)**: mainland investors buying HK stocks
- **Margin trading (融资融券)**: Leveraged long/short positions
- **Block trades (大宗交易)**: Large block trades reported separately

### Index/Benchmark

- **CSI 300 (沪深300)**: Top 300 A-shares by market cap and liquidity
- **CSI 500 (中证500)**: Mid-cap 500 stocks
- **CSI 1000 (中证1000)**: Small-cap 1000 stocks
- **SSE 50 (上证50)**: Top 50 Shanghai stocks
- **ChiNext Index (创业板指)**: ChiNext composite
- **STAR 50 (科创50)**: STAR Market top 50

## Implications for SYNAPSE

### Data Layer

- Must handle A-share specific fields (price limits, suspension status, ST flag)
- Must track corporate action adjustment factors
- Must support northbound flow data
- Must handle variable trading calendars

### Factor Layer

- Event-driven factors require event extraction capability
- Sentiment factors require Chinese NLP (P3 scope)
- Capital flow factors require northbound/margin data
- Cross-sectional factors must respect price limits and suspension

### Backtest Layer

- T+1 constraint must be enforced
- Price limit impact must be modeled
- Suspension must be handled (position frozen or excluded)
- Cost model must include stamp duty (sell-side only)
- Commission structure differs from US (minimum 5 yuan)

### Report Layer

- Must include A-share specific risk factors
- Must document price limit and suspension assumptions
- Must reference correct benchmarks (CSI 300, not S&P 500)

## What This Document Does NOT Cover

- NLP / sentiment analysis (P3 scope)
- Event extraction engine (P2 scope)
- News ingestion (out of scope)
- Real-time data feeds (out of scope)
