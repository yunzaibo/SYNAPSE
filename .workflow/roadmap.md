# Roadmap

## Market Domain: China A-Shares (ADR-005, ADR-006)

Research Focus: Event-driven + Sentiment-aware Research

**Core positioning**: Research Memory Infrastructure / Personal Cognitive Infrastructure for investing

**Extensibility principle**: Phase 划分是交付节奏，不是架构边界。自动交易后续会做，前期不做。架构必须为所有功能预留扩展点。

---

## P0: Research Loop Skeleton — COMPLETED (2026-05-17)

Focus:

- [x] Cross-sectional equity factor research (sample data)
- [x] Factor audit (IC/RankIC/coverage/leakage)
- [x] Simple backtest with explicit costs
- [x] Markdown report generation (10 sections)
- [x] AI prompt templates with boundary enforcement
- [x] Experiment tracking with 9-state machine
- [x] Governance: no-delete, explicit costs, AI boundary
- [x] Error hierarchy (SynapseError + 10 codes)
- [x] 124 tests passing

---

## P1: Daily Research Loop + Market Semantics + Research Memory

**Goal**: Transform from "factor research tool" to "daily investment research system". Add daily watchlist, position monitoring, decision memory, and market semantics foundation.

### P1.1: Daily Watchlist

Generate a daily research queue of stocks worth investigating.

| Component | Description |
|-----------|-------------|
| WatchlistEntry | Daily research queue item with 4 trigger types |
| Watchlist Generator | AI-powered daily research queue creation |
| Signal Types | Event-driven, Factor-driven, Attention-driven, Portfolio-related |

**Watchlist Card v1 (B+ format)**:
```yaml
ticker: 600519
headline: "茅台新品发布引发白酒板块关注"
why_now: "社交讨论度过去24小时上升240%，白酒板块出现联动放量"
signals: [attention_spike, sector_resonance, historical_pattern_match]
signal_strength: weak/medium/strong  # 不用百分比，避免 AI 权威感
risk_hint: "高波动 / 事件驱动可能快速衰减"
research_angle: "观察新品是否影响高端白酒估值逻辑"
action: "值得关注"
```

### P1.2: Position Monitor

Active Thesis Tracker — research-state-first (not red/green P&L).

| Layer | Name | Description |
|-------|------|-------------|
| 1 | Portfolio State | 盈亏、仓位、持仓周期 — 不作为主视觉 |
| 2 | Attention State | 新闻传播、板块关注度、市场讨论 |
| 3 | Research Flags | 轻量占位，非判断型提示（thesis 相关事件、时间窗口、风险假设变化） |
| 4 | Thesis Context | P2+，structured thesis + evidence graph |

**P2+ 暂不做**: Thesis Drift Engine, Correlation Intelligence, Autonomous Judgement

### P1.3: Decision Memory

Minimal Decision Memory — 冻结认知状态，不是交易日志.

**Entry Phase**:
```yaml
ticker: 600519
decision_type: buy  # only buy/sell, P1 no hold
thesis: "消费恢复预期 + 新品发布可能带动高端白酒关注度提升"
key_risk: "白酒板块整体估值偏高，消费恢复速度可能低于预期"
time_horizon: medium_term  # short_term / medium_term / long_term
attention_origin: event_attention  # factor_signal / event_attention / portfolio_review
created_at: 2026-05-18
source_type: human_written
```

**Review Phase** (optional, system-suggested but not mandatory):
```yaml
review_outcome: thesis_confirmed  # thesis_confirmed / partially_confirmed / thesis_invalidated
review_note: "新品确实带动了短期关注度，但消费恢复速度低于预期"
reviewed_at: 2026-08-18
```

Key principles:
- Use `thesis` not `reason` → 引导研究观点，不是交易冲动
- Use `key_risk` not `risk` → "这个 thesis 最可能错在哪里"
- Use `thesis_confirmed` not `profit/loss` → 盈亏 ≠ thesis 正确
- Review optional → 降低门槛，"持续记录"比"记录专业"更重要

### P1.4: Research Object Model (9 Objects)

| Object | Layer | Description |
|--------|-------|-------------|
| WatchlistEntry | 1 | Daily research queue item |
| Thesis | 1 | Research hypothesis |
| Decision | 1 | Buy/sell decision |
| Review | 1 | Decision post-mortem |
| Position | 1 | Current holding |
| Signal | 2 | Independent signal record (simplified entry) |
| Risk | 2 | Independent risk hypothesis (simplified entry) |
| Event | 2 | Market event (simplified entry) |
| ResearchTopic | 2 | Clustering tag (simplified entry) |

**Thesis Evolution**: append-only with `parent_thesis_id` + `revision` + `previous_revision`

**Source Attribution**: every AI-generated field has `source_type: ai_generated | human_written | imported | market_data`

**Lifecycle States**: `active → inactive → archived → abandoned → superseded`

### P1.5: China Market Semantics Foundation

| Module | Semantics | Description |
|--------|-----------|-------------|
| MarketClock | `MarketClock` | Research time ≠ market time (market_context field) |
| Trading Calendar | `CNTradingCalendar` | SSE/SZSE holidays, half-day sessions |
| T+1 Settlement | `T1Constraint` | Buy-today-sell-tomorrow rule |
| Price Limits | `PriceLimitModel` | ±10% main, ±5% ST, ±20% STAR/ChiNext |
| Suspension | `SuspensionHandler` | Detect suspended stocks |
| Corporate Actions | `CorporateActionAdapter` | Forward adjustment (前复权) |
| Northbound Flow | `NorthboundFlowLoader` | Daily net buy data |
| Benchmark/Index | `IndexConstituentLoader` | CSI300/CSI500 constituents |

### P1 NOT in Scope

- NLP system
- RAG platform
- Knowledge graph
- Multi-agent orchestration
- News crawler platform
- Event extraction engine
- Autonomous trading system
- Real-money trading (architecture reserves extension points)

### P1 Data Sources

| Data | Source | Cost |
|------|--------|------|
| Trading calendar | AKShare | Free |
| Daily OHLCV | AKShare / Tushare | Free |
| Suspension status | AKShare | Free |
| Price limit data | AKShare | Free |
| Corporate actions | AKShare | Free |
| Northbound flow | AKShare | Free |
| Index constituents | AKShare | Free |

---

## P2: Advanced Research Memory Layer

**Goal**: Transform from "record" to "cognition". Add behavioral analysis, error patterns, research evolution.

### P2 Scope

| Component | Description |
|-----------|-------------|
| Error Pattern Recognition | 聚合重复错误模式 |
| Behavioral Statistics | 用户行为统计 |
| Research Evolution | 研究观点演化追踪 |
| Decision Bias Detection | 决策偏差检测 |
| Thesis Drift Engine | Thesis 漂移检测（P1 parent_thesis_id 基础上） |
| Correlation Intelligence | 相关性智能分析 |
| Signal/Risk/Event 独立追踪 | P1 简化入口升级为完整功能 |

### P2 NOT in Scope

- Autonomous Judgement
- Real-time trading signals
- Full NLP pipeline (P3)

---

## P3: Event-driven Research Contracts

**Goal**: Define and implement contracts for event-driven research.

### P3 Scope

| Contract | Description |
|----------|-------------|
| `AnnouncementContract` | Company announcement ingestion and structured extraction |
| `PolicyEventContract` | Government/regulatory policy event modeling |
| `SentimentArtifact` | Market sentiment data structure |
| `ThemePropagation` | Concept/theme sector propagation model |
| `DragonTigerContract` | 龙虎榜 data and analysis |
| `CapitalFlowContract` | 资金流向 (margin, block trade, main force) |

### P3 NOT in Scope

- Full NLP pipeline (P4)
- Autonomous agents (P4-P5)
- Real-time trading
- News crawling at scale

---

## P4: Chinese Financial NLP Layer

**Goal**: Build Chinese financial language understanding capability.

### P4 Scope

| Component | Description |
|-----------|-------------|
| 公告抽取 | Announcement information extraction |
| 政策理解 | Policy intent interpretation |
| 情绪分析 | Market sentiment analysis |
| 产业链事件 | Supply chain event modeling |
| 风险语义 | Risk disclosure understanding |
| Financial Semantic Registry | 语义 constantly evolving 的管理 |

### P4 Constraints

- Must be research-grade, not production-grade
- No real-time trading signals
- Human review required for all NLP outputs

---

## P5: Agentic Research Workflow

**Goal**: Deploy AI agents within the research workflow with proper governance.

### P5 Scope

| Agent | Role |
|-------|------|
| Research Agent | Draft research plans, suggest hypotheses |
| Factor Agent | Generate factor definitions, suggest formulas |
| Backtest Agent | Configure and run backtests |
| Risk Agent | Identify risks, suggest mitigations |
| Report Agent | Generate research reports |
| Autonomous capabilities | GenericAgent autonomous agent growth |

### P5 Governance

- All agent actions logged and auditable
- Human review required for all outputs
- Agents must not modify experiment records (ADR-004)
- Runtime serves Research Lifecycle, not itself

---

## P6+: Automatic Trading (future, not now)

Architecture reserves extension points for:

- Paper trading
- Order simulation
- Strategy optimization
- Execution engine
- Risk management
- Broker gateway
- Compliance gates

**Key principle**: Automatically trading will be implemented in later phases. P0-P2 does not include real trading. Architecture must not limit this capability.

---

## Scope Freeze Rules

1. Each phase has explicit "In Scope" and "NOT in Scope"
2. Features not listed in current phase "In Scope" must not be implemented
3. Phase completion requires audit (maestro-milestone-audit)
4. No phase skipping without ADR update

## Deferred (No Phase Assigned)

- Real-time data feeds
- Multi-asset support (futures, crypto)
- Cloud backend / multi-tenant SaaS
- Production compliance
