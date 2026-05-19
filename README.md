# SYNAPSE

AI-native Quant Research OS for cross-sectional equity factor research.

## Status

**P3: Event-Driven Extensions — COMPLETED** (2026-05-19)

607 tests passing. Event detection (8 types), propagation graph, settlement lifecycle, sentiment propagation (R0), capital flow divergence, cross-event correlation.

## Installation

```bash
git clone <repo-url>
cd SYNAPSE
pip install -e ".[dev]"
```

## Quick Start

Run the sample research pipeline:

```bash
py examples/run_sample_research.py
```

This executes the full P0 loop:
1. Load sample price data (100 rows, 3 tickers)
2. Compute 20-day momentum factor
3. Audit factor (IC, RankIC, coverage, leakage risk)
4. Create experiment record
5. Run backtest with explicit costs (10 bps transaction, 5 bps slippage)
6. Generate markdown report

Output: `reports/sample-research-report.md`

## Run Tests

```bash
py -m pytest tests/ -v -p no:asyncio
```

## Project Structure

```
synapse/
  core/          — Error registry, config loader, workspace init
  data/          — Dataset metadata, CSV/Parquet loader, validator
  event/         — Event detection (8 types), propagation graph, settlement, sentiment/divergence/correlation
  factor/        — Factor spec, compute engine, audit (IC/RankIC)
  experiment/    — Experiment records, tracker, state machine
  backtest/      — Config, engine (long-short quintile), 8 metrics
  report/        — Markdown report generator (10 sections)
  agent/         — AI prompt templates (boundary-respecting)

data/sample/     — Sample price data + YAML metadata
factors/         — Factor spec YAMLs
experiments/     — Experiment record YAMLs
reports/         — Generated reports
configs/         — Default configuration
tests/           — Unit + integration tests (124 total)
```

## Architecture

5-layer research platform (not a single agent):

1. **Infra/Platform** — workspace, storage, config, logging
2. **Research Methodology** — factor definition, validation, audit
3. **Portfolio/Risk** — backtest, metrics, cost assumptions
4. **Execution/Trading** — P0: none (research-only system)
5. **Agent Plane** — prompt templates, no autonomous execution

## Governance

- Failed experiments cannot be deleted
- Transaction costs must be explicit (no silent defaults)
- AI-generated content marked with `created_by: ai`
- Agents must not execute trades or bypass validation

## License

TBD
