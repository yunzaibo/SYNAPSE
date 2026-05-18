# Boundary

## Core Boundary

SYNAPSE is a research system, not an execution-first trading system.

## Agent Boundary

Agents may:

- Draft research plans
- Propose factor definitions
- Generate code drafts
- Summarize results
- Call approved tools
- Generate reports
- Flag risks

Agents must not:

- Execute real trades
- Modify experiment records silently
- Hide failed experiments
- Bypass validation
- Change data ranges without recording
- Select only favorable results

## Research vs Trading Boundary

P0 supports research, factor validation, backtest, and report.

P0 does not support broker connection, real order placement, live trading, HFT execution, or regulatory reporting.

## Platform vs Methodology Boundary

Platform layer handles storage, artifacts, configuration, experiment records, and tool execution.

Research methodology layer handles factor validity, split strategy, leakage checks, backtest assumptions, and risk interpretation.

Do not mix these responsibilities.

## External Project Boundary

Qlib, OpenBB, FinRobot, and PnLClaw are references.

They must not become uncontrolled architecture owners.

If a dependency is introduced, it must be recorded in ADR or RFC.

## Data Boundary

Every dataset must describe:

- Source
- Time range
- Frequency
- Available-at timestamp if applicable
- Adjustments
- Survivorship assumptions
- Missing value policy

## P0 Development Boundary

P0 should not introduce cloud account system, payment system, real trading, deep multi-agent framework, complex UI, or strategy marketplace.
