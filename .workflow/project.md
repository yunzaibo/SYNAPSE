# Project: SYNAPSE

## What This Is

SYNAPSE is an AI-native Personal Investment Research System (ADR-005, ADR-006). It focuses on China A-shares event-driven and sentiment-aware research, helping individual investors build, track, and evolve their investment research over time.

Core positioning: **Research Memory Infrastructure** / **Personal Cognitive Infrastructure for investing**.

## Core Value

Research-first, agent-enhanced investment research workflow with 4 core features. If everything else fails, the system must produce **reproducible, governance-checked research artifacts** — not auto-trading, not stock recommendations, not agent demos.

## 4 Core Features

| Feature | Positioning |
|---------|------------|
| Daily Watchlist | Research Queue, not Stock Recommendation Feed |
| Position Monitor | Active Thesis Tracker (research-state-first, not P&L) |
| Factor Research | P0 completed (124 tests, governance-first) |
| Research Memory | Freeze cognitive state, not a trading log |

## Requirements

### Validated

- [x] P0: Cross-sectional equity factor research loop (data → factor → audit → backtest → report)
- [x] P1: Daily Research Loop (Watchlist + Position Monitor + Decision Memory + Research Object Model + Market Semantics) — 369 tests, 28 new source files

### Active
- [ ] P2: Advanced Research Memory Layer (error patterns, behavioral stats, research evolution)
- [ ] P3: Event-driven Research Contracts (AnnouncementContract, PolicyEventContract, SentimentArtifact)
- [ ] P4: Chinese Financial NLP Layer (公告抽取, 政策理解, 情绪分析)
- [ ] P5: Agentic Research Workflow (Research Agent, Factor Agent, Backtest Agent, Risk Agent, Report Agent)

### Out of Scope (P0-P2)

- Real-money trading — architecture reserves extension points for future automatic trading
- Broker integration / order routing — P6+
- HFT / market making — different engineering domain
- Full web UI — CLI/file-first for now
- Cloud backend / multi-tenant SaaS — local-first development
- RAG / vector database — not needed until P3
- Distributed execution — single-machine research is sufficient
- Production compliance workflow — not in scope

## Context

- **Market domain**: China A-Shares (ADR-005, ADR-006)
- **Research focus**: Event-driven + Sentiment-aware Research
- **Positioning**: AI-native Personal Investment Research System (not a quant platform)
- **User profile**: AI-native Individual Researcher (individual investors, programmers, semi-professional investors, quantitative enthusiasts)
- **Multi-end**: Windows/Mac desktop + Feishu/WeChat Bot mobile
- **User mode**: Natural language first (AI-assisted), technical users can fork and modify
- Reference projects (inspiration only, NOT dependencies): Qlib, OpenBB, FinRobot, PnLClaw
- All documents follow L0-L6 layering: Vision → Product → Architecture → Contracts → Governance → Delivery → Evolution

## Constraints

- **Research-first**: System starts from research methodology, not generic agents (ADR-001)
- **Governance first-class**: Time-aware validation, factor audit, experiment lineage, risk review are core, not plugins (ADR-004)
- **Cognitive freezing**: Research Memory = freeze cognitive state, not a trading log
- **Thesis-driven**: All research objects connect through Thesis
- **Anti-同花顺化**: No red/green centering, no hot lists, no AI authority, no dopamine economy
- **Reproducible by default**: Every experiment must record data version, factor version, parameters, date range, split method, cost assumptions
- **Failed experiments preserved**: Best-result-only reporting is forbidden; failed runs must not be deleted
- **Assumptions explicit**: Transaction cost, date range, split method cannot be silently omitted
- **Agent traceable**: AI-generated changes must be marked with `created_by: ai | mixed`
- **Source attribution**: Every AI-generated field must declare `source_type: ai_generated | human_written | imported | market_data`
- **Thesis append-only**: Thesis never overwrite, always create new revision with `revision` + `previous_revision`
- **MarketClock**: Research time ≠ market time; every time-aware object must declare market_context
- **Agent boundary**: Agents may draft plans and suggest transitions; agents must not execute trades, modify records silently, hide failures, or bypass validation
- **Data time-awareness**: Every dataset must declare `available_at`, `as_of_date`, `revision_timestamp`
- **External references only**: Qlib/OpenBB/FinRobot/PnLClaw are design references, not architecture owners
- **Platform vs Methodology separation**: Platform handles storage/artifacts; methodology handles factor validity/split/risk — do not mix
- **A-share specific**: T+1 settlement, price limits, suspension handling, stamp duty (sell-side only), northbound flow (ADR-005)
- **Extensibility**: Phase 划分是交付节奏，不是架构边界。自动交易后续会做，前期不做。架构必须为所有功能预留扩展点。
- **Runtime serves Research**: SYNAPSE's Runtime should serve Research Lifecycle. Runtime itself must not become the product.

## Research Object Model

9 objects: WatchlistEntry, Thesis, Decision, Review, Position, Signal, Risk, Event, ResearchTopic.

Key relationships: WatchlistEntry → Decision → Thesis → Review. Position maintains Thesis. Event generates Signal and triggers WatchlistEntry.

Thesis evolution: append-only with `parent_thesis_id` + `revision`.

**完整 schema 定义**: `docs/04_contracts/01_Research_Object_Schema.md`

## Tech Stack

- **Language**: Python 3.11+
- **Data**: pandas, numpy (PyData ecosystem)
- **Storage**: Local filesystem (YAML metadata + Parquet/CSV data)
- **Config**: YAML
- **Reports**: Markdown
- **Testing**: pytest
- **Packaging**: pyproject.toml

## Frontend Stack（已确认 2026-05-18）

| Layer | Tech | Responsibility |
|-------|------|---------------|
| Core | Tauri + React + TailwindCSS + shadcn/ui + Radix UI | Design System, Layout, Workspace, Theming, AI-native feeling |
| Data (selective) | Ant Design Table + TanStack Table + react-virtualized | High-density data display (Table, Tree, DatePicker) |
| Charts | Recharts (P1) + Apache ECharts (P2+) | Factor visualization, Thesis evolution, Review lineage |

**Philosophy**: "AI-native Research Workspace", not enterprise admin panel. High information density ≠ backend style. shadcn/ui owns the visual language; Ant Design is only a data component provider.

## GenericAgent Integration（已确认 2026-05-18）

| Decision | Choice |
|----------|--------|
| Runtime mode | Tauri Sidecar (independent process, crash isolation) |
| Communication | HTTP/REST |
| Task model | Long-running Session (support continuous research tasks) |
| Lifecycle | P1 complete SidecarLifecycleManager (spawn/heartbeat/restart/kill/crash recovery/orphan cleanup) |
| Store isolation | GenericAgent never accesses Thesis/Memory/Position Store directly; all through Research Runtime Contract |
| Naming | Research Runtime Provider (not GenericAgent Integration) |

```txt
Runtime Topology:
React UI → Tauri Core (Rust) → Research Runtime Provider → GenericAgent Sidecar
```

**Core boundary**: GenericAgent = Research Execution Engine, NOT system brain. Core Domain Ownership stays in SYNAPSE Core.

## Storage Architecture（已确认 2026-05-18）

**Workspace + Global Vault hybrid model**:

| Layer | Path | Content |
|-------|------|---------|
| System Layer | `~/.synapse/` | runtime, cache, logs, sessions, config — NO research assets |
| Workspace Layer | `~/SYNAPSE-Workspaces/` | Research assets (first-class), user-configurable path |

```txt
workspace/
├── synapse.yaml        ← workspace config
├── thesis/
├── decisions/
├── watchlists/
├── positions/
├── events/
├── reports/
├── artifacts/
├── attachments/
├── snapshots/
└── .index/workspace.db ← SQLite index
```

**Philosophy**: Markdown/YAML are canonical. SQLite is acceleration. Workspace is first-class.

## Config Architecture（已确认 2026-05-18）

| Layer | Format | Path | Semantic |
|-------|--------|------|----------|
| Global Runtime Config | TOML | `~/.synapse/config.toml` | Machine runtime params (sidecar, logging, cache, ports) |
| Workspace Semantic Config | YAML | `workspace/synapse.yaml` | Research semantics (preferences, signals, AI behavior) |

**Philosophy**: TOML for runtime, YAML for research semantics — clear semantic boundary.

## Entry Points（已确认 2026-05-18）

| Entry | Role | P1 Status |
|-------|------|-----------|
| Tauri GUI | Main product, first-class | ✅ |
| synapse CLI | Headless Runtime Entry Point (independent binary) | ✅ |
| Feishu/WeChat Bot | Future adapter | P2+ deferred |

**Architecture**: GUI / CLI / Bot share Core Runtime (not 3 separate implementations). CLI = thin wrapper over Core Runtime API. Core Runtime is GUI-independent. CLI = Task Invocation Layer.

## File Naming（已确认 2026-05-18）

**D: Human-readable Alias + Stable Internal ID**

| Object | Naming Pattern | Example |
|--------|---------------|---------|
| Thesis | `ths_<id>_<slug>/` | `ths_7f8c91_consumer-recovery/` |
| Decision | `dec_<date>_<action>_<symbol>/` | `dec_20260518_buy_600519/` |
| Watchlist | `wl_<symbol>_<reason>.yaml` | `wl_600519_attention-spike.yaml` |
| Position | `pos_<market>_<symbol>.yaml` | `pos_CN_A_600519.yaml` |

**5 Principles**:
1. Human-readable ≠ Identity
2. IDs are immutable, aliases are mutable
3. File paths are for navigation, metadata is for semantics
4. Ticker is not a stable identity
5. Revisions are append-only (`rev-001.md` → `rev-002.md`)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| ADR-001: Research-first instead of Agent-first | Generic agents produce impressive demos but weak research reliability | Accepted |
| ADR-002: Initial Alpha Domain = Cross-sectional Equity Factors | Clear workflow, tabular data, IC/RankIC validation, avoids real-time complexity | Accepted |
| ADR-003: Build From Scratch vs Fork PnLClaw | Different long-term target, need custom methodology layer, avoid inherited constraints | Accepted |
| ADR-004: Research Governance Is First-class | Quant research vulnerable to false positives; governance must not be a later plugin | Accepted |
| ADR-005: Initial Market Domain = China A-Shares | A-shares have unstructured market semantics ideal for LLM; US equities too mature for differentiation | Accepted |
| ADR-006: Why China A-Shares + Event-driven | A-shares event-driven research is more AI-native than standard factor platforms; different research paradigm | Accepted |
| ADR-007: Security Identity | Composite Security Identity format (cn.sse.600519) for stable cross-market identity | Accepted |
| ADR-008: Temporal Semantics | event time / processing time / market effective time distinction for all time-aware objects | Accepted |
| ADR-009: Projection Rebuild Rules | Position: event-triggered, Watchlist: daily, Timeline: append-only | Accepted |
| ADR-010: Activity Taxonomy | activity.jsonl: research activities logged, runtime optional, debug/LLM forbidden | Accepted |
| ADR-011: AI Mutation Boundaries | AI generates suggestions, human confirms; AI never overwrites canonical artifacts | Accepted |

## Stakeholders

- AI-native Individual Researcher (individual investors)
- Programmers interested in quant research
- Semi-professional investors
- Quantitative enthusiasts
- Research-oriented retail investors

---

## Milestone History

### M1: P0 Minimum Research Loop — COMPLETED (2026-05-17)

Complete factor research pipeline: data → factor → audit → experiment → backtest → report. 124 tests passing, governance-first design validated. All ADR constraints respected. 6 learnings extracted (setuptools, index alignment, Sharpe edge case, Windows pytest, factor groupby, error code reuse).

### M2: P1 Daily Research Loop — COMPLETED (2026-05-18)

Transformed from factor research tool to daily investment research system. 9 research object schemas, projection engine, market semantics, research workflow, CLI entry point. 369 tests (249 new). 28 new source files across core/schemas/projection/market/workflow/cli. 8 learnings extracted (dataclass over Pydantic, weak schema, projection rebuild, parameter injection, Windows Python stub, pytest-asyncio conflict, CLI thin wrapper, composite identity).

---
*Last updated: 2026-05-18 — M2 milestone complete, P1 scope delivered*
