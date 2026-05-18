# ADR-005: Initial Market Domain

## Status

**Accepted** — 2026-05-17

## Context

P0 used synthetic/sample equity data only. The market domain was not frozen.

Before P1 could introduce real data connectors, methodology expansion, or market-specific production assumptions, the initial market domain had to be decided.

Two candidate paths were evaluated:

- **US Equities** — mature factor research ecosystem, abundant free data APIs, well-established IC/RankIC benchmarks, but low differentiation potential
- **China A-Shares** — unique market microstructure (T+1, price limits, suspension), growing quant community,大量非结构化市场语义（政策、公告、资金流、情绪），LLM 价值高

## Decision

Select **China A-Shares** as the initial market domain.

Select **Event-driven + Sentiment-aware Research** as the initial research focus.

## Rationale

1. **AI-native differentiation** — A-shares have大量传统量化难结构化的东西（政策公告、龙虎榜、资金情绪、产业链事件、监管风向），这些非常适合 LLM 处理。美股经典因子已研究几十年，methodology 难以形成差异化。

2. **Market semantics are unstructured** — A 股的市场语义（T+1、涨跌停、停牌、北向资金、政策事件）仍然很不结构化，这正是 AI-native 研究的机会。

3. **Not "another market"** — A 股不是"另一个 market"，而是另一种研究范式。需要专门的语义层来处理其独特微结构。

4. **Scope control** — Event-driven focus 后必须 freeze scope，避免 scope explosion（新闻、RAG、知识图谱、Agent 全做）。

## Frozen Constraints

- Initial market domain: **China A-Shares**
- Initial research focus: **Event-driven + Sentiment-aware Research**
- Research-first (ADR-001) and Governance-first (ADR-004) remain in effect
- P1 scope: **China Market Semantics Layer only** — NOT NLP, RAG, knowledge graph, multi-agent, news crawler, or trading system

## Consequences

- P0 sample data is market-agnostic — no changes needed
- P1 data connectors must handle A-share specific semantics (T+1, price limits, suspension)
- Backtest contract must extend for A-share cost model (stamp duty, commission, T+1 settlement)
- Factor methodology will evolve from pure cross-sectional to event-driven + sentiment-aware

## Related

- ADR-001: Research-first instead of Agent-first (accepted)
- ADR-002: Initial Alpha Domain = Cross-sectional Equity Factors (accepted)
- ADR-004: Research Governance Is First-class (accepted)
- ADR-006: Why SYNAPSE Chooses China A-Shares and Event-driven Research (accepted)
