# MVP Scope

## MVP Name

SYNAPSE P0

## MVP Goal

Build the smallest useful research loop for cross-sectional equity factor research.

## Status: DELIVERED (2026-05-17)

All P0 scope items implemented and verified (124 tests passing).

## In Scope

### Research Workspace

- [x] Basic project folder (`init_workspace()`)
- [x] Experiment folder (`experiments/`)
- [x] Artifact folder (`artifacts/`)
- [x] Markdown reports (`reports/`)

### Data Plane

- [x] Local sample data loading (`load_dataset()`)
- [x] Data specification file (YAML metadata)
- [x] Data metadata (`DatasetMetadata` dataclass)
- [x] Time columns and availability assumptions (`available_at_policy`, `as_of_date`)

### Factor Plane

- [x] Factor definition (`FactorSpec` dataclass)
- [x] Factor metadata (YAML serialization)
- [x] Factor audit result (`FactorAuditResult` dataclass)
- [x] IC / RankIC implementation (scipy spearmanr)

### Experiment Plane

- [x] Experiment config (`ExperimentRecord` dataclass)
- [x] Experiment run record (YAML persistence)
- [x] Parameters (dict field, versioned)
- [x] Result manifest (artifacts list)
- [x] State machine (9 states: draft → archived)

### Backtest Plane

- [x] Simple backtest interface (`BacktestEngine`)
- [x] Cost assumptions (`transaction_cost_bps`, `slippage_bps` — required)
- [x] Benchmark placeholder (equal-weight)
- [x] Basic performance metrics (8 metrics: annual_return, volatility, sharpe, max_drawdown, turnover, win_rate, excess_return, information_ratio)

### Agent Plane

- [x] AI assistant prompt templates (`synapse/agent/prompts.py`)
- [x] Research plan generation (`draft_research_plan()`)
- [x] Report generation (`draft_report()`)
- [x] Risk checklist generation (`generate_risk_checklist()`)

## Out of Scope

- Real-time market data
- Production vendor data
- Broker trading
- HFT
- Sophisticated portfolio optimizer
- Full web UI
- Distributed execution
- Fine-tuned models
- Deep RAG system
- Multi-tenant SaaS

## P0 Deliverable

A developer can run:

```
sample_data → sample_factor → factor_audit → simple_backtest → report.md
```

with reproducible artifacts. **DELIVERED.**
