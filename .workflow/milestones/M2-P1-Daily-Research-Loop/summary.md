# Milestone: M2-P1-Daily-Research-Loop — P1 Daily Research Loop

**Completed**: 2026-05-18
**Artifacts**: 3 (plan: 1, execute: 1, verify: 1)

## Key Outcomes

### From Factor Research Tool → Daily Investment Research System

P1 transformed SYNAPSE from a cross-sectional factor research tool (P0) into a daily investment research system with:

1. **9 Research Object Schemas** — Thesis, Decision, Review, Position, WatchlistEntry, Signal, Risk, Event, ResearchTopic — all as Python dataclasses with YAML round-trip
2. **Projection Engine** — Position rebuild from Decisions, daily Watchlist generation, append-only Timeline rendering, SQLite index
3. **Market Semantics** — China A-share trading calendar (2024-2026), T+1 settlement, price limits (main 10%, GEM/STAR 20%, ST 5%), suspension detection
4. **Research Workflow** — Daily research orchestration, decision recording with position rebuild, review submission with signal evaluation
5. **CLI Entry Point** — 5 subcommands (init/research/decision/review/workspace) as thin wrappers over core modules

### Architecture Decisions Validated

- **ADR-007**: Composite Security Identity (`cn.sh.600519`) — used across all modules
- **ADR-008**: Three time dimensions (event/market/processing) — TemporalContext validated
- **ADR-009**: Projection Rebuild Rules — canonical vs projection separation working correctly
- **ADR-010**: Activity Taxonomy — JSONL logging with forbidden type enforcement
- **ADR-011**: AI Mutation Boundaries — AI generates suggestions, human confirms

### Test Coverage

- **Total tests**: 369 (249 new in P1 + 120 from P0)
- **P1 new tests**: 19 + 41 + 65 + 31 + 23 + 39 + 13 + 18 = 249
- **All tests passing**: 369/369

### Files Created

- **28 new source files** across `synapse/core/`, `synapse/core/schemas/`, `synapse/core/projection/`, `synapse/core/market/`, `synapse/core/workflow/`, `synapse/cli/`
- **8 new test files** in `tests/unit/`
- **0 files modified** (only pyproject.toml updated for console_scripts)

## Learnings

### Patterns Discovered

1. **Dataclasses over Pydantic** — matched project style, avoided heavy dependency, sufficient with `from_dict()`/`to_dict()` round-trip
2. **Weak Schema + Lazy Upcast** — `schema_version` field, no global migration, upcast on load
3. **Projection Rebuild** — canonical objects immutable, projections computed by replaying in time order
4. **Parameter Injection** — `activity_log=None` makes workflows testable without filesystem side effects
5. **CLI as Thin Wrapper** — 40-70 lines per command, all logic in core modules

### Pitfalls Encountered

1. **Windows Python stub** — `WindowsApps\python` returns exit code 49; use `D:\python\python.exe`
2. **pytest-asyncio conflict** — `-p no:asyncio` flag required when plugin installed but unused
3. **GBK encoding** — Windows Python can't encode emoji in stdout; avoid in script output

### Strategy Adjustments

1. **Wave-based parallel execution** — W1+W2 parallel, W3+W4 parallel, W5 serial; reduced total execution time
2. **Delegate to Claude** — All 8 tasks executed via `maestro delegate --to claude --mode write`; consistent quality
3. **TASK-006 summary not written** — Market semantics task completed but summary file missing; verified via test count (39 tests)

## What's Next

P1 provides the data model and workflow foundation. The next milestone should build on this:

- **P2: Advanced Research Memory Layer** — Error pattern recognition, behavioral statistics, thesis drift detection
- **P3: Event-driven Research Contracts** — Announcement ingestion, policy events, sentiment artifacts
- **UI Design** — User needs to complete UI design flow before any frontend tasks (Tauri + React + Tailwind + shadcn/ui)
