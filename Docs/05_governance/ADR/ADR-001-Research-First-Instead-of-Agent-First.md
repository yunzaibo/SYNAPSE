# ADR-001 Research-first Instead of Agent-first

## Status

Accepted

## Context

Many AI quant projects start by building a generic multi-agent system and then asking it to discover profitable strategies.

This often produces impressive demos but weak research reliability.

## Decision

SYNAPSE will be research-first.

The system starts from:

```txt
Alpha domain
→ Research workflow
→ Governance
→ Experiment contracts
→ Agent assistance
```

not from generic autonomous agents.

## Consequences

Positive:

- Better research discipline
- Lower overfitting risk
- Clearer development boundary
- Easier to evaluate

Negative:

- Slower than making a simple demo
- Requires more upfront methodology design

## Alternatives

- Build a generic multi-agent trading bot
- Build a ChatGPT-like quant assistant
- Fork an existing agent project and customize it
