# SYNAPSE

SYNAPSE is an AI-native Personal Investment Research System.

This document package is intended for developers and AI coding agents to understand the project before implementation.

Created: 2026-05-17 | Updated: 2026-05-18

## Documentation Structure

```
.workflow/              — 操作文件（单一真相源）
├── project.md          — 项目定义
├── roadmap.md          — 路线图
├── state.json          — 工作流状态
└── config.json         — 配置

docs/                   — 详细参考文档（不重复 .workflow/ 内容）
├── 01_vision/          — 愿景与哲学
├── 02_product/         — PRD 与用例
├── 03_architecture/    — 架构与语义
├── 04_contracts/       — 数据与实验契约
├── 05_governance/      — ADR 与审查清单
├── 06_delivery/        — 计划与任务
└── 07_evolution/       — 路线图引用指针 → .workflow/roadmap.md
```

## Recommended Reading Order

1. `.workflow/project.md` — 项目定义（单一真相源）
2. `.workflow/roadmap.md` — 路线图（单一真相源）
3. `docs/01_vision/01_Vision_And_What_Not.md`
4. `docs/01_vision/02_Research_Philosophy.md`
5. `docs/02_product/01_PRD_SYNAPSE_AI_Quant_Research_OS.md`
6. `docs/03_architecture/01_Architecture_Overview.md`
7. `docs/05_governance/ADR/ADR-001-Research-First-Instead-of-Agent-First.md`

## Core Positioning

SYNAPSE is not an auto-trading bot. It is not a stock recommendation feed. It is a Research Memory Infrastructure that helps individual investors build, track, and evolve their investment research over time.

4 core features: Daily Watchlist, Position Monitor, Factor Research, Research Memory.
