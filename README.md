<p align="center">
  <h1 align="center">SYNAPSE</h1>
  <p align="center">
    <strong>AI-native Quant Research Operating System</strong><br>
    <em>The first event-driven research platform designed from the ground up for Chinese A-share markets</em>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/tests-1806+-brightgreen?logo=pytest&logoColor=white" alt="Tests">
    <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
    <img src="https://img.shields.io/badge/status-P4_NLP_Complete-purple" alt="Status">
  </p>
</p>

---

## Why SYNAPSE?

Existing quant frameworks (backtrader, zipline, vnpy, rqalpha) treat Chinese A-share markets as an afterthought -- a generic backtester with a China adapter bolted on. **SYNAPSE is the opposite**: it's an operating system for quantitative research, built from day one with A-share semantics, event-driven market intelligence, and AI-assisted analysis as first-class citizens.

**The numbers**: 148 source modules, 75 test files, 1806 passing tests, 48K+ lines of Python.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Agent Plane (AI-Native)                        │
│   Prompt Templates · Research Planning · Report Generation          │
│   Governance: AI outputs tagged, human_review required              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │  NLP Layer   │  │ Factor Engine│  │  Event Engine │               │
│  │  (P4)        │  │ (P6)         │  │  (P3)         │               │
│  │              │  │              │  │               │               │
│  │ · NER        │  │ · 13 Factors │  │ · 8 Detector  │               │
│  │ · Sentiment  │  │ · IC/RankIC  │  │ · DAG Graph   │               │
│  │ · Events     │  │ · Portfolio  │  │ · Lifecycle   │               │
│  │ · Policy     │  │ · Decay      │  │ · Impact      │               │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘               │
│         │                 │                   │                       │
│         └────────┬────────┴───────────┬───────┘                       │
│                  │                    │                               │
│  ┌───────────────▼────────────────────▼──────────────────┐           │
│  │              Projection Layer (P1-2)                   │           │
│  │   Scoring Engine · Watchlist Generator · Position Mgr │           │
│  └───────────────────────────┬───────────────────────────┘           │
│                              │                                       │
│  ┌───────────────────────────▼───────────────────────────┐           │
│  │              Backtest Engine (P2)                       │           │
│  │   Quintile Sort · 8 Metrics · IC Analysis · Attribution│           │
│  └───────────────────────────┬───────────────────────────┘           │
│                              │                                       │
│  ┌───────────────────────────▼───────────────────────────┐           │
│  │              Foundation (P1 / P5)                       │           │
│  │   Trading Calendar · Ex-Right Adj · Northbound Flow   │           │
│  │   DataSource ABC · EastMoney/Akshare Adapters          │           │
│  └───────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Differentiators

### Event Propagation as a First-Class DAG

Not just event queues. SYNAPSE models how market events actually spread through sectors and concepts:

```python
# Events live in a PropagationGraph with Tarjan cycle detection
# and Kahn topological sort -- not a simple event bus
graph.add_event(earnings_event)          # DETECTED
graph.propagate()                        # PROPAGATING → SETTLED
# Category-specific decay: earnings τ=6.5d, policy τ=1.5d, social τ=0.5d
```

- **4-state lifecycle**: `DETECTED → PROPAGATING → SETTLED / EXPIRED`
- **Automatic pruning** of weak edges below confidence threshold
- **Impact scoring** that propagates through the graph to affected sectors

### Deep Chinese A-Share Native

Not a generic framework with China support. Built-in:

| Feature | Implementation |
|---------|---------------|
| **Trading Calendar** | State Council holiday schedules 2024-2026, compensation workdays, bisect-based O(log n) T+N arithmetic |
| **Ex-Right Adjustment** | Forward/backward with `Decimal(ROUND_HALF_UP)`, handles dividends, splits, bonus shares |
| **Northbound Flow** | Stock Connect momentum signals, flow divergence detection |
| **Index Constituent** | Point-in-time tracking, change signals |
| **NLP** | 515+ financial sentiment terms, 5 entity types with ticker linking, policy document understanding (PBOC/CSRC/State Council) |

### AI-Native with Governance Boundaries

SYNAPSE uses AI as a **constrained research assistant**, not an autonomous trader:

- Every AI output tagged `created_by: ai` with `human_review: true`
- Agents cannot execute trades or modify experiment records
- Failed experiments **cannot be deleted** -- full audit trail
- Transaction costs are **mandatory** (no silent defaults)

### Multi-Dimensional Scoring Pipeline

A pluggable `ScoringEngine` aggregates 4 dimensions into actionable watchlist scores:

```python
score = (
    signal_strength   * 0.35 +  # Factor signals
    event_decay       * 0.30 +  # Event-driven attention
    portfolio_thesis  * 0.20 +  # Thesis alignment
    market_context    * 0.15    # Market semantics
)
```

Full component breakdown for every score -- no black boxes.

## Quick Start

```bash
# Clone and install
git clone https://github.com/your-org/SYNAPSE.git
cd SYNAPSE
pip install -e ".[dev]"

# Run the sample research pipeline
py examples/run_sample_research.py

# Output: reports/sample-research-report.md
```

This executes the full loop: load data → compute factor → audit (IC/RankIC) → experiment → backtest → report.

## Run Tests

```bash
# Full suite
py -m pytest tests/ -p no:asyncio -q

# By module
py -m pytest tests/unit/test_ner_engine.py -p no:asyncio        # NLP: NER
py -m pytest tests/unit/test_sentiment_lexicon.py -p no:asyncio # NLP: Lexicon
py -m pytest tests/unit/test_factor_engine.py -p no:asyncio     # Factor Engine
py -m pytest tests/unit/test_event_detection.py -p no:asyncio   # Event Engine
```

## Technical Deep Dive

### NLP Layer (P4)

8 modules for Chinese financial text understanding:

| Module | Capability | Tests |
|--------|-----------|-------|
| `NEREngine` | 5 entity types + fuzzy ticker linking | 39 |
| `SentimentLexicon` | 515+ terms, negation/degree handling | 44 |
| `AnnouncementParser` | 24 regex patterns, 5+ metric extraction | 33 |
| `SentimentClassifier` | Bullish/bearish/neutral + aspect-level | 36 |
| `EventExtractor` | 5 event types, P3 EventType mapping | 33 |
| `ReportSummarizer` | 5 rating types, target price extraction | 33 |
| `PolicyUnderstander` | 3 issuing bodies, 8 sector mapping | 30 |
| `NLP-P3 Integration` | 6 BaseDetector implementations | 81 |

### Event Engine (P3)

8 detector types with graph-based propagation:

- **BaseDetector ABC** -- pluggable detection interface
- **PropagationGraph** -- Tarjan SCC, Kahn topological sort, BFS traversal
- **Lifecycle Manager** -- DETECTED → PROPAGATING → SETTLED/EXPIRED
- **Impact Analyzer** -- cascading impact through sector relationships

### Factor Engine (P6)

13 traditional factors with full audit pipeline:

- **Value**: PE, PB, PS, Dividend Yield
- **Momentum**: 20d/60d returns, price relative to high
- **Quality**: ROE, ROA, gross margin stability
- **Volatility**: realized vol, max drawdown
- **Liquidity**: turnover ratio, Amihud illiquidity
- **IC/RankIC Auditor** -- with A/B/C/D quality ratings
- **Portfolio Optimizer** -- equal/IC-weighted/risk-parity

### Backtest Engine (P2)

Long-short quintile backtest with institutional-grade metrics:

- Quintile sorting with transaction cost modeling
- 8 performance metrics (Sharpe, Sortino, Calmar, max drawdown, etc.)
- Barra-style factor attribution via OLS regression
- Parquet persistence with schema versioning

## Project Structure

```
synapse/
├── core/           # Foundation: schemas, market semantics, projection
│   ├── market/     # Trading calendar, ex-right adjustment, northbound flow
│   ├── projection/ # Scoring engine, watchlist generation
│   └── schemas/    # 9 research object data models
├── event/          # Event-driven intelligence layer
│   ├── detectors/  # 8 concrete detectors (BaseDetector ABC)
│   ├── graph.py    # PropagationGraph (DAG with lifecycle)
│   └── nlp_detectors.py  # 6 NLP-P3 integration detectors
├── nlp/            # Chinese financial NLP (P4)
│   ├── ner_engine.py      # Named entity recognition
│   ├── lexicon/           # 515+ term sentiment dictionary
│   ├── sentiment_classifier.py  # Aspect-level sentiment
│   └── event_extractor.py # Structured event extraction
├── factor/         # Factor research engine (P6)
│   ├── engine.py   # FactorEngine with batch/PIT validation
│   ├── factors/    # 13 traditional factors
│   └── audit.py    # IC/RankIC auditor
├── backtest/       # Backtest engine (P2)
│   ├── engine.py   # BacktestEngine with DI components
│   └── metrics.py  # 8 performance metrics (single-pass)
├── experiment/     # Experiment lifecycle management
├── report/         # Markdown report generator
└── agent/          # AI prompt templates with governance

tests/              # 1806 tests across unit + integration
```

## Roadmap

- [x] **P0**: Core research loop (factor → audit → experiment → backtest → report)
- [x] **P1**: Market semantics (trading calendar, ex-right, northbound, constituents)
- [x] **P1-2**: Daily watchlist generator (4-dimension scoring)
- [x] **P2**: Long-short quintile backtest engine
- [x] **P3**: Event-driven extensions (propagation graph, sentiment R0, capital flow)
- [x] **P4**: Chinese financial NLP layer (NER, sentiment, events, policy)
- [x] **P5**: Real data source integration (EastMoney, Akshare adapters)
- [x] **P6**: Factor research engine (13 factors, IC audit, portfolio optimization)
- [ ] **P7**: Real-time streaming pipeline
- [ ] **P8**: Multi-agent research collaboration
- [ ] **P9**: Web dashboard & visualization

## Contributing

SYNAPSE is designed for contributions. The modular architecture means you can work on any layer independently:

- **NLP Layer**: Add new entity types, sentiment terms, or document parsers
- **Event Engine**: Create new detectors, propagation rules, or impact analyzers
- **Factor Engine**: Implement new factors, audit methods, or optimization strategies
- **Data Sources**: Add new adapter implementations following the `DataSource` ABC

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT

---

<p align="center">
  <sub>Built with obsessive attention to A-share market semantics.</sub>
</p>
