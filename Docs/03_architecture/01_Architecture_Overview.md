# Architecture Overview

## System Positioning

SYNAPSE is an AI-native Personal Investment Research System (ADR-005, ADR-006).

It is not an auto-trading bot. It is not a stock recommendation feed. It is a research memory infrastructure that helps individual investors build, track, and evolve their investment research over time.

Core positioning: **Research Memory Infrastructure** / **Personal Cognitive Infrastructure for investing**.

## High-level Layers

```txt
SYNAPSE
├─ Infra / Platform Layer
├─ China Market Semantics Layer (P1)
├─ Research Methodology Layer
├─ Research Memory Layer (P1 minimal, P2 advanced)
├─ Event-driven Research Layer (P2-P3)
├─ Chinese Financial NLP Layer (P3)
├─ Portfolio / Risk Layer
├─ Execution / Trading Layer (future, not now)
├─ Agent Plane (P4-P5)
└─ Research Computation Layer (reference only)
```

## Runtime Topology（已确认 2026-05-18）

```txt
GUI Layer (Tauri)
CLI Layer (synapse binary)
Bot Layer (future)

        ↓

Research Runtime Core

        ↓

Workspace + Memory + Artifacts
```

**Three runtimes**:
1. **UI Runtime**: React + Tauri WebView
2. **App Runtime**: Rust/Tauri Core (filesystem, lifecycle, IPC, permissions, local infra)
3. **Research Runtime**: GenericAgent sidecar (task execution, MCP tools, reasoning, context, orchestration)

```txt
React UI → Tauri Core (Rust) → Research Runtime Provider → GenericAgent Sidecar
```

**Core boundary**: GenericAgent = Research Execution Engine, NOT system brain. Core Domain Ownership (Thesis/Memory/Position Store) stays in SYNAPSE Core. GenericAgent never accesses stores directly — all through Research Runtime Contract.

## External Tool Relationships

```txt
SYNAPSE Core（研究工作流）
  ↕
GenericAgent（直接运行时依赖，不加限制，保留拓展性）
  ↕
UZI-Skill（可插拔分析引擎，不进 Core）
  ↕
AKShare + SmartSearch（数据 + 信息采集）
  ↕
Research Computation Layer（Qlib/OpenBB/FinRobot/PnLClaw 参考设计思路）
```

Key principles:
- **GenericAgent = direct runtime dependency** (agent loop, tool abstraction, memory layer). Current focus on Research Task Runtime; architecture supports Autonomous Agent growth in later phases.
- **UZI-Skill = pluggable analysis engine** (individual stock deep analysis, not in Core).
- **SmartSearch = information collection layer** (P2/P3 integration).
- **Research Computation Layer = reference only** (Qlib/OpenBB/FinRobot/PnLClaw design ideas, not core dependencies).

## Extensibility Principle

Phase 划分是交付节奏，不是架构边界。自动交易后续会做，前期不做。架构必须为策略优化、执行引擎、风险管理预留扩展点。P0-P2 不实现交易功能，但不能限制拓展性。

## Frontend Stack（已确认 2026-05-18）

| Layer | Tech | Responsibility |
|-------|------|---------------|
| Core | Tauri + React + TailwindCSS + shadcn/ui + Radix UI | Design System, Layout, Workspace, Theming, AI-native feeling |
| Data (selective) | Ant Design Table + TanStack Table + react-virtualized | High-density data display (Table, Tree, DatePicker) |
| Charts | Recharts (P1) + Apache ECharts (P2+) | Factor visualization, Thesis evolution, Review lineage |

**Philosophy**: "AI-native Research Workspace", not enterprise admin panel. High information density ≠ backend style. shadcn/ui owns the visual language; Ant Design is only a data component provider.

## P0 Implemented Modules

```
synapse/
├── core/           — Error registry, config loader, workspace init
├── data/           — DatasetMetadata, CSV/Parquet loader, validator
├── factor/         — FactorSpec, compute engine, audit (IC/RankIC)
├── experiment/     — ExperimentRecord, tracker, state machine (9 states)
├── backtest/       — BacktestConfig, engine (long-short quintile), 8 metrics
├── report/         — Markdown generator (10 sections, artifact links)
└── agent/          — AI prompt templates (boundary-respecting)
```

## Layer 1: Infra / Platform

This layer provides the system foundation.

Responsibilities:

- Workspace (`init_workspace()`, `check_workspace()`)
- Data management (`load_dataset()`, `validate_metadata()`)
- Experiment tracking (`ExperimentTracker`)
- Artifact storage (file-based YAML)
- Report generation (`generate_report()`)
- Configuration (`load_config()`, `validate_config()`)
- Error registry (`SynapseError` base + 10 error codes)

## Layer 1.5: China Market Semantics (P1)

This layer models A-share specific market semantics.

See `docs/03_architecture/06_China_Market_Semantics.md` for full definitions.

Responsibilities:

- Trading calendar (SSE/SZSE holidays, half-day sessions)
- T+1 settlement constraint
- Price limit modeling (±10% main board, ±5% ST, ±20% STAR/ChiNext)
- Suspension handling (detect, exclude, model frozen positions)
- Corporate action adjustment (前复权 default)
- Northbound flow data loading
- Index constituent data loading
- MarketClock (research time ≠ market time)
- Event timestamp schema (definition only)
- Announcement availability schema (definition only)

## Layer 2: Research Methodology

This is the core layer.

Initial domain: cross-sectional equity factor research.

Responsibilities:

- Factor definition (`FactorSpec` — formula, direction, universe)
- Factor computation (`compute_factor()` — groupby per ticker)
- Factor validation (`audit_factor()` — IC, RankIC, coverage, leakage risk)
- Research lineage (experiment records with full parameter tracking)

P0 implemented: IC, RankIC, coverage, leakage risk.
P1 deferred: mutual information, SHAP consistency, purging/embargo, walk-forward.

## Layer 2.5: Research Memory Layer (P1-P2)

This is a first-class architecture layer.

### P1: Minimal Decision Memory

Storage strategy:
1. **Markdown files** (source of truth): decision thesis, review notes, post-mortem, research reflections
2. **YAML metadata**: ticker, date, decision_type, confidence, linked_experiment_id, linked_report_id, linked_position_id, tags, created_by, source_type
3. **SQLite index** (rebuildable): searchable memory index, ticker/date/tag queries, relationship mapping

Key principles:
- SQLite is index, not source of truth. Markdown/YAML are portable research assets.
- Thesis must be append-only (revision + previous_revision).
- Every AI-generated field must have source_type annotation.

### P2: Advanced Research Memory

- Error pattern recognition
- Behavioral statistics
- Research evolution tracking
- Decision bias detection

## Layer 3: Event-driven Research (P2-P3)

This layer extends research methodology for event-driven and sentiment-aware factors.

Responsibilities:

- Announcement ingestion and structured extraction
- Policy event modeling
- Market sentiment data structures
- Theme/concept propagation modeling
- 龙虎榜 analysis
- Capital flow analysis (margin, block trade, main force)

## Layer 4: Portfolio / Risk

Responsibilities:

- Portfolio construction (long-short quintile)
- Rebalancing assumptions (monthly)
- Transaction cost assumptions (explicit, required)
- Turnover tracking
- Drawdown analysis
- Risk report (8 metrics)

P0 includes simple single-pass backtest with explicit costs.

## Layer 5: Execution / Trading (future, not now)

Architecture reserves extension points for:

- Paper trading
- Order simulation
- Broker gateway
- Execution risk
- Compliance gates

P0-P2 does not include real trading. Architecture must not limit this capability.

## Agent Plane

GenericAgent is a direct runtime dependency, running as a **Tauri sidecar process**.

**Runtime integration**:
- P1-P2: Local Sidecar Runtime (Tauri sidecar process)
- P3+: Remote/Service Provider support (protocol unchanged)
- Communication: HTTP/REST
- Task model: Long-running Session (P1+)
- Lifecycle: SidecarLifecycleManager (spawn/heartbeat/restart/kill/crash recovery/orphan cleanup)

**Critical boundaries**:
- GenericAgent = Research Execution Engine, NOT system brain
- Core Domain Ownership (Thesis/Memory/Position Store) stays in SYNAPSE Core
- GenericAgent never accesses stores directly — all through Research Runtime Contract
- P1 only task-oriented runtime, no persistent autonomous agent

**P4-P5 will add**: Research Agent, Factor Agent, Backtest Agent, Risk Agent, Report Agent, autonomous capabilities.

**Critical principle**: SYNAPSE's Runtime should serve Research Lifecycle. Runtime itself must not become the product.

## Research Object Model (9 Objects)

### Layer 1: P1 functionally complete

| Object | Description |
|--------|------------|
| WatchlistEntry | Daily research queue item |
| Thesis | Research hypothesis |
| Decision | Buy/sell decision |
| Review | Decision post-mortem (optional) |
| Position | Current holding |

### Layer 2: P1 schema defined, simplified entry

| Object | Description |
|--------|------------|
| Signal | Independent signal record |
| Risk | Independent risk hypothesis |
| Event | Market event of interest |
| ResearchTopic | Clustering tag for theses |

### Key Relationships

```txt
WatchlistEntry ──triggers──> Decision
Decision       ──embodies──> Thesis
Decision       ──has many──> Signal
Decision       ──has many──> Risk
Review         ──validates──> Thesis
Review         ──evaluates──> Signal
Review         ──evaluates──> Risk
Position       ──maintains──> Thesis
Thesis         ──belongs to──> ResearchTopic
Event          ──generates──> Signal
Event          ──triggers──> WatchlistEntry
```

### Thesis Evolution

```yaml
parent_thesis_id: "thesis-20260518-600519"
revision: 4
previous_revision: "thesis-20260518-600519-v3"
```

Thesis is append-only. Never overwrite — always create new revision.

### Source Attribution

Every AI-generated field must declare:

```yaml
source_type: ai_generated | human_written | imported | market_data
```

### Lifecycle States

All research objects:

```txt
active → inactive → archived → abandoned → superseded
```

## Reference Architecture Rule

Do not write:

```txt
SYNAPSE uses Qlib/OpenBB/FinRobot/PnLClaw as core dependencies.
```

Correct wording:

```txt
SYNAPSE references selected design ideas from Qlib, OpenBB, FinRobot, and PnLClaw.
```

### Absorbed Design Patterns

| Pattern | Source | SYNAPSE Usage |
|---------|--------|--------------|
| Config-as-pipeline | Qlib | YAML-driven factor research |
| Experiment/Recorder | Qlib | Research Memory experiment logging |
| Provider abstraction | OpenBB | AKShare + SmartSearch data switching |
| Priority-layered skill registry | PnLClaw | GenericAgent skill system |
| Protocol-based components | PnLClaw | SYNAPSE Core plugin architecture |
| Declarative agent config | FinRobot | GenericAgent role configuration |
| Security Gateway | PnLClaw | Agent execution safety |
| Tool-loop detection | PnLClaw | Agent automation guardrail |

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

**Philosophy**:
- Markdown/YAML are canonical. SQLite is acceleration.
- Workspace is first-class (multi-workspace support: China-AShare, US-Tech, Macro, etc.)
- File naming uses Human-readable Alias + Stable Internal ID (not ticker-based)
- Workspace is Git-friendly (no binary db blobs)
- FileWatcher Strategy: filesystem is source of truth

## Config Architecture（已确认 2026-05-18）

| Layer | Format | Path | Semantic |
|-------|--------|------|----------|
| Global Runtime Config | TOML | `~/.synapse/config.toml` | Machine runtime params (sidecar, logging, cache, ports) |
| Workspace Semantic Config | YAML | `workspace/synapse.yaml` | Research semantics (preferences, signals, AI behavior) |

**Philosophy**: TOML for runtime, YAML for research semantics — clear semantic boundary.

Constraints:
- TOML: serde + strongly typed structs
- YAML: JSON Schema validation + `schema_version` field
- Workspace YAML: research-oriented semantics allowed; execution graphs / runtime orchestration forbidden

## Entry Points（已确认 2026-05-18）

| Entry | Role | P1 Status |
|-------|------|-----------|
| Tauri GUI | Main product, first-class | ✅ |
| synapse CLI | Headless Runtime Entry Point (independent binary) | ✅ |
| Feishu/WeChat Bot | Future adapter | P2+ deferred |

**Architecture**: GUI / CLI / Bot share Core Runtime (not 3 separate implementations). CLI = thin wrapper over Core Runtime API. Core Runtime is GUI-independent. CLI = Task Invocation Layer.

CLI commands (P1):
- `synapse task run watchlist.generate`
- `synapse workspace index`
- `synapse export`
- `synapse doctor`

## File Naming（已确认 2026-05-18）

**Human-readable Alias + Stable Internal ID**

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
