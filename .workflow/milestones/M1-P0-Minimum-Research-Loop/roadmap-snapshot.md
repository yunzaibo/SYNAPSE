# Roadmap: SYNAPSE

## Overview

SYNAPSE P0 delivers a complete factor research loop for cross-sectional equity factors. Starting from project foundation, through data loading, factor definition and audit, experiment tracking, backtesting, and report generation — all with governance-first design. AI assistant templates are included as a Should priority.

## Phases

**Minimum-phase principle:** All epics form a linear pipeline. No hard dependency boundary justifies splitting into multiple phases. Wave DAG handles task ordering within the phase.

- [ ] **Phase 1: P0 Minimum Research Loop** - Complete factor research pipeline from data to report

## Phase Details

### Phase 1: P0 Minimum Research Loop
**Goal**: Enable a developer to run `sample_data → sample_factor → factor_audit → simple_backtest → report.md` with reproducible artifacts
**Depends on**: Nothing (first phase)
**Requirements**: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, NFR-REP-001, NFR-GOV-001, NFR-DATA-001, NFR-LOCAL-001
**Success Criteria** (what must be TRUE):
  1. A developer can initialize a project, load sample data, define a factor, audit it, run a backtest, and generate a report
  2. Every experiment record contains data version, factor version, parameters, date range, and cost assumptions
  3. Failed experiments are preserved and visible
  4. AI-generated content is marked with created_by metadata
  5. All artifacts are file-based and reproducible

## Scope Decisions

- **In scope**: Cross-sectional equity factor research, local sample data, factor audit (IC/RankIC/coverage/leakage), simple backtest with explicit costs, markdown reports, AI prompt templates
- **Deferred**: Purging/embarkment (P1), walk-forward validation (P1), mutual information (P1), SHAP consistency (P1), factor library (P1), research memory (P1), multi-agent (P2), web UI (P2), data connectors (P3)
- **Out of scope**: Real trading, broker integration, HFT, cloud backend, multi-tenant SaaS, production compliance

## Progress

| Phase | Status | Completed |
|-------|--------|-----------|
| 1. P0 Minimum Research Loop | Not started | - |
