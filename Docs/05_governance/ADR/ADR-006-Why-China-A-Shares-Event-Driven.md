# ADR-006: Why SYNAPSE Chooses China A-Shares and Event-driven Research

## Status

**Accepted** — 2026-05-17

## Context

SYNAPSE needs a differentiated positioning in the AI-native quant research space.

US equity factor research is mature — decades of published papers, well-established benchmarks (Fama-French, Barra, Axioma), and standardized methodologies (IC, RankIC, neutralization, monthly rebalance). Building "another factor platform" on US equities offers limited differentiation.

China A-shares present a fundamentally different research landscape where LLM capabilities provide genuine value.

## Decision

SYNAPSE positions itself as a **Chinese AI-native Financial Research System**, not a standard factor platform.

Core thesis: A-shares have大量传统量化难结构化的东西，这些正是 LLM 的机会。

## Why A-Shares Are More AI-native

### 1. Unstructured Market Semantics

A-shares contain rich, unstructured information that traditional quantitative models struggle to capture:

```txt
政策 (Policy)          — 央行、国务院、证监会公告
公告 (Announcements)   — 上市公司公告、业绩预告、风险提示
舆情 (Sentiment)       — 市场情绪、社交媒体、财经新闻
主题 (Themes)          — 概念板块、产业链、主题投资
龙虎榜 (Dragon Tiger)  — 游资动向、机构席位
资金流 (Capital Flow)  — 北向资金、融资融bag、主力资金
监管 (Regulation)      — 监管风向、政策窗口指导
```

These are inherently semantic, context-dependent, and language-rich — exactly where LLMs excel.

### 2. Event-driven ≠ Another Factor

Classic factor research:
```txt
IC → RankIC → Neutralization → Monthly Rebalance → Backtest
```

Event-driven A-share research:
```txt
Event Extraction → Policy Interpretation → Theme Propagation
→ Market Sentiment → Attention Dynamics → Capital Flow → Regime Switching
```

This is a different research paradigm, not just a different market.

### 3. LLM Value Proposition

| Task | US Equities | China A-Shares |
|------|-------------|----------------|
| Factor computation | Well-structured, formulaic | Partially structured, partially semantic |
| Data interpretation | Numerical | Numerical + textual + contextual |
| Event understanding | Earnings dates, Fed meetings | Policy nuance, regulatory intent, market narrative |
| Sentiment analysis | English NLP, mature tools | Chinese NLP, domain-specific, less mature |
| Regime detection | Statistical methods | Policy-driven regime shifts, harder to model |

LLMs provide disproportionate value in the right column.

### 4. Differentiation Barrier

A-shares event-driven research requires:
- Chinese financial language understanding
- Market microstructure semantics (T+1, price limits, suspension)
- Policy interpretation capability
- Theme/concept propagation modeling
- Capital flow sentiment analysis

These create a meaningful differentiation barrier that pure factor platforms cannot easily replicate.

## Scope Freeze (Critical)

Choosing A-shares + event-driven creates severe scope explosion risk. The following are explicitly OUT OF SCOPE for current phases:

| Phase | In Scope | Explicitly Out of Scope |
|-------|----------|------------------------|
| P0 | Research loop skeleton | (completed) |
| P1 | China market semantics layer | NLP, RAG, knowledge graph, multi-agent, news crawler |
| P2 | Event-driven research contracts | Full NLP pipeline, autonomous agents |
| P3 | Chinese financial NLP layer | Real-time trading, broker integration |
| P4 | Agentic research workflow | Autonomous trading, production deployment |

**Rule**: If a feature is not listed in the "In Scope" column for the current phase, it must not be implemented.

## What Must Change

### Data Contract

Add market-specific fields:
- `market`: `CN_A` (vs `US`, `HK`)
- `exchange`: `SSE`, `SZSE`
- `settlement`: `T+1`
- `price_limit_pct`: `10.0` (or `5.0` for ST stocks)
- `stamp_duty_bps`: `10` (sell-side only)

### Factor Contract

Extend for event-driven factors:
- `factor_type`: `cross_sectional` | `event_driven` | `sentiment` | `hybrid`
- `event_source`: `announcement` | `policy` | `sentiment` | `capital_flow`

### Backtest Contract

A-share specific assumptions:
- T+1 settlement (no intraday reversal)
- Price limit impact modeling
- Suspension handling (cannot trade suspended stocks)
- Stamp duty (sell-side only, 0.1%)
- Commission structure (0.02-0.03%)

### Architecture

New layer required:
```
China Market Semantics Layer
├─ Trading Calendar (SSE/SZSE holidays, half-day sessions)
├─ T+1 Semantics (settlement constraints)
├─ Price Limit Semantics (涨跌停, ST stocks)
├─ Suspension Semantics (停牌、复牌)
├─ Corporate Action Semantics (除权除息、配股、增发)
├─ Northbound Flow Semantics (沪深港通)
├─ Benchmark/Index Semantics (CSI300, CSI500, 中证全指)
└─ Event Timestamp Semantics (公告时间、政策发布时间)
```

## Related

- ADR-001: Research-first instead of Agent-first (accepted)
- ADR-002: Initial Alpha Domain = Cross-sectional Equity Factors (accepted)
- ADR-004: Research Governance Is First-class (accepted)
- ADR-005: Initial Market Domain = China A-Shares (accepted)
