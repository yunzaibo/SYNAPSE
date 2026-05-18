# Roadmap

> **Single source of truth**: `.workflow/roadmap.md`
>
> This file is a reference pointer. The canonical roadmap is maintained at `.workflow/roadmap.md` and is read directly by maestro tools (maestro-plan, maestro-execute, maestro-verify).

## Quick Reference

| Phase | Status | Description |
|-------|--------|------------|
| P0 | ✅ COMPLETED | Minimum Research Loop (124 tests, factor research pipeline) |
| P1 | 📋 PLANNED | Daily Research Loop + Market Semantics + Research Memory |
| P2 | 📋 PLANNED | Advanced Research Memory Layer |
| P3 | 📋 PLANNED | Event-driven Research Contracts |
| P4 | 📋 PLANNED | Chinese Financial NLP Layer |
| P5 | 📋 PLANNED | Agentic Research Workflow |
| P6+ | 📋 DEFERRED | Automatic Trading (future, not now) |

## Documentation Structure

```
.workflow/
├── project.md          — Project definition (single source of truth)
├── roadmap.md          — Roadmap (single source of truth)
├── state.json          — Workflow state
└── config.json         — Configuration

docs/
├── 01_vision/          — Vision & Philosophy
├── 02_product/         — PRD & Use Cases
├── 03_architecture/    — Architecture & Semantics
├── 04_contracts/       — Data & Experiment Contracts
├── 05_governance/      — ADRs & Review Checklists
├── 06_delivery/        — Plans & Tasks
└── 07_evolution/       — This file (reference pointer)
```
