# Research Philosophy

## Core Philosophy

SYNAPSE follows these principles:

```txt
Research-first
Agent-enhanced
Evidence-based
Experiment-driven
Governance-oriented
Human-reviewed
Reproducible by default
Cognitive-freezing
Thesis-driven
Anti-同花顺化
```

## Research-first

The system starts from a clear research methodology.

Do not build a generic agent first and then ask it to discover alpha.

Correct order:

```txt
Alpha domain
→ Research workflow
→ Governance rules
→ Experiment contracts
→ Agent assistance
```

## Agent-enhanced

GenericAgent is a direct runtime dependency (not an optional plugin).

Agents can:

- Draft research plans
- Generate factor definitions
- Suggest validation methods
- Execute permitted tools
- Summarize experiment results
- Detect common research risks
- Generate reports

Agents must not:

- Secretly change research assumptions
- Hide failed experiments
- Select only the best result
- Bypass governance checks
- Execute real trades (P0-P2)
- Present outputs as investment advice

**Extensibility**: GenericAgent will gain autonomous capabilities in later phases. Do not restrict its potential — P0-P2 focuses on Research Task Runtime, but architecture must support Autonomous Agent growth.

## Cognitive-freezing

Research Memory = 冻结认知状态，不是交易日志.

Record:

- Why the thesis was formed (not just what was bought)
- What the key risk was (not just the P&L)
- How the thesis evolved over time
- Which signals were observed and which were confirmed

Do not record as the primary output:

- Profit / loss numbers
- Win rate
- Portfolio value

## Thesis-driven

All research objects connect through Thesis:

```txt
WatchlistEntry ──triggers──> Decision
Decision       ──embodies──> Thesis
Review         ──validates──> Thesis
Position       ──maintains──> Thesis
Thesis         ──belongs to──> ResearchTopic
```

Use `thesis` not `reason` → 引导研究观点，不是交易冲动.
Use `key_risk` not `risk` → "这个 thesis 最可能错在哪里".
Use `thesis_confirmed` not `profit/loss` → 盈亏 ≠ thesis 正确.

## Anti-同花顺化

SYNAPSE must actively avoid:

- Red/green color centering
- Hot lists / leaderboards
- AI authority感 (signal_strength uses weak/medium/strong, not percentages)
- Dopamine economy (fast stimulation)
- Social sentiment platforms

SYNAPSE emphasizes:

- Thesis continuity
- Review lineage
- Memory evolution
- Research quality

Every feature should ask: **"Does this strengthen research, or stimulate trading?"**

## Evidence-based

Every conclusion should be backed by data, experiment records, and generated artifacts.

## Experiment-driven

Each experiment should record:

- Data version
- Factor version
- Model version
- Parameters
- Date range
- Split method
- Cost assumptions
- Backtest assumptions
- Generated artifacts
- Review status

## Governance-oriented

Minimum governance topics:

- Look-ahead bias
- Survivorship bias
- Purging / embargoing
- Walk-forward validation
- CPCV when applicable
- IC / RankIC stability
- Mutual information
- SHAP consistency
- Transaction cost assumptions
- Turnover
- Regime stability

## Source Attribution

Every piece of content must declare its origin:

```yaml
source_type: ai_generated | human_written | imported | market_data
```

This prevents "semantic pollution" — users must be able to distinguish AI-generated analysis from their own reasoning.

## Research Lifecycle

All research objects have lifecycle states:

```txt
active → inactive → archived → abandoned → superseded
```

This prevents "Obsidian Vault 化" — the system must stay navigable over years of use.
