---
title: "Learnings"
readMode: optional
priority: medium
category: learning
keywords:
  - bug
  - lesson
  - gotcha
  - learning
---

# Learnings

Add entries with: `/spec-add learning <description>`

## Entries

<spec-entry category="learning" keywords="setuptools,build-backend,flat-layout,pyproject" date="2026-05-17">

### setuptools.build_meta required for flat-layout

`setuptools.backends._legacy:_Backend` is not available in current setuptools. Use `setuptools.build_meta` with explicit `[tool.setuptools.packages.find]` for flat-layout projects. Fixed during TASK-001.

</spec-entry>

<spec-entry category="learning" keywords="backtest,index-alignment,MultiIndex,RangeIndex,pandas" date="2026-05-17">

### Backtest engine index alignment

When factor_values and forward_returns have different index types (MultiIndex vs RangeIndex), alignment must use `.iloc[mask]` with numpy boolean arrays, not direct index-based masking.

</spec-entry>

<spec-entry category="learning" keywords="sharpe,floating-point,numpy,std,edge-case" date="2026-05-17">

### Sharpe ratio floating-point edge case

`np.std()` on constant data returns ~1e-17 instead of zero, causing Sharpe ratio to explode. Fixed with tolerance threshold `> 1e-10` before dividing. Found during TASK-007 backtest metrics computation.

</spec-entry>

<spec-entry category="learning" keywords="pytest,windows,asyncio,py-launcher,environment" date="2026-05-17">

### Windows pytest environment quirks

On Windows, use `py -m pytest` instead of `python -m pytest`. Also need `-p no:asyncio` to avoid pytest-asyncio plugin conflict when the plugin is installed but not used. Found during TASK-008 test verification.

</spec-entry>

<spec-entry category="learning" keywords="factor-compute,groupby,ticker,pandas,data-alignment" date="2026-05-17">

### Factor compute on interleaved ticker data

When computing cross-sectional factors on interleaved multi-ticker data, always `groupby("ticker")` before applying time-series operations. Direct `.pct_change()` on interleaved data produces incorrect cross-ticker contamination. Found during TASK-003 factor compute implementation.

</spec-entry>

<spec-entry category="learning" keywords="experiment,deletion,governance,audit-trail,no-delete" date="2026-05-17">

### Experiment deletion governance

ADR-004 mandates no-delete experiments. `ExperimentTracker.delete_experiment()` raises `AGENT_ACTION_NOT_ALLOWED` unconditionally. Audit trail integrity requires immutable experiment records. Found during TASK-005 experiment tracker implementation.

</spec-entry>

<spec-entry category="learning" keywords="dataclass,pydantic,type-safety,yaml,project-style" date="2026-05-18" source="milestone-complete">

### Dataclasses over Pydantic for schema design

P1 chose Python dataclasses over Pydantic for all 9 research object schemas. Reason: matched existing project style (GlobalConfig already used dataclass), avoided heavy dependency, and provided sufficient type safety with `from_dict()`/`to_dict()` round-trip. String enums (`class X(str, Enum)`) provide YAML-friendly serialization without external libs. Found across TASK-003 schema implementation.

</spec-entry>

<spec-entry category="learning" keywords="weak-schema,lazy-upcast,migration,schema-version" date="2026-05-18" source="milestone-complete">

### Weak Schema + Lazy Upcast pattern

Each schema has a `schema_version` field. No global migration system — instead, upcast on load when version mismatch. This avoids brittle migration scripts and allows incremental schema evolution. Pattern: `from_dict()` checks `schema_version` and applies transforms as needed. Found during TASK-003 schema design.

</spec-entry>

<spec-entry category="learning" keywords="projection,rebuild,append-only,canonical,snapshot" date="2026-05-18" source="milestone-complete">

### Projection Rebuild pattern (ADR-009)

Canonical objects (Thesis/Decision/Review/Event) are immutable source of truth. Projections (Position/Watchlist/Timeline) are computed by replaying canonical objects in time order. Position rebuilds from Decision changes; Watchlist regenerates daily (not incremental); Timeline renders all artifacts sorted by time. Key: projections are always derivable, never stored as primary data. Found across TASK-005 projection engine.

</spec-entry>

<spec-entry category="learning" keywords="parameter-injection,activity-log,optional-dependency,testing" date="2026-05-18" source="milestone-complete">

### Activity logging via parameter injection

Workflow functions accept `activity_log=None` parameter. When None, file operations are skipped. This makes workflows testable without filesystem side effects, while still supporting full activity logging in production. Pattern: `if self.activity_log: self.activity_log.append(...)`. Found in TASK-007 workflow implementation.

</spec-entry>

<spec-entry category="learning" keywords="python,exit-code-49,windows,stub,microsoft-store" date="2026-05-18" source="milestone-complete">

### Windows Python stub returns exit code 49

`C:\Users\youngth\AppData\Local\Microsoft\WindowsApps\python` is a Microsoft Store stub, not real Python. Always returns exit code 49. Use explicit path `D:\python\python.exe` (Python 3.11.5) for all pytest and script execution on this machine. Found during P1 execution.

</spec-entry>

<spec-entry category="learning" keywords="pytest,asyncio,plugin-conflict,-p-no-asyncio" date="2026-05-18" source="milestone-complete">

### pytest-asyncio plugin conflict on Windows

Running `python -m pytest` raises `AttributeError: 'Package' object has no attribute 'obj'` when pytest-asyncio is installed but not used. Fix: add `-p no:asyncio` flag to all pytest commands. Consistent across all P1 task executions.

</spec-entry>

<spec-entry category="learning" keywords="workflow,thin-wrapper,cli,command-pattern" date="2026-05-18" source="milestone-complete">

### CLI as thin wrapper pattern

CLI layer (argparse) does minimal work — parses args, instantiates core classes, calls workflow functions. All business logic lives in `core/workflow/`. CLI commands are 40-70 lines each, purely wiring. This separation enables both CLI and future web UI to share the same core logic. Found in TASK-008 CLI implementation.

</spec-entry>

<spec-entry category="learning" keywords="identity,composite-key,cn-exchange-ticker,security-id" date="2026-05-18" source="milestone-complete">

### Composite Security Identity format (ADR-007)

SecurityIdentity uses `cn.{exchange}.{ticker}` format (e.g., `cn.sh.600519`). Frozen dataclass ensures immutability. Market field parsed via `split("_")[0].lower()` from enum value (CN_A → cn). This format is used as directory names, file prefixes, and index keys throughout the system. Found in TASK-002.

</spec-entry>
