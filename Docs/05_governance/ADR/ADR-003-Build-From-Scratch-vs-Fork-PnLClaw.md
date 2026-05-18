# ADR-003 Build From Scratch vs Fork PnLClaw

## Status

Accepted

## Context

PnLClaw is a useful reference project for AI-native quant workflows.

It demonstrates ideas such as:

- Chat-first quant interaction
- Local-first workflow
- Skill-style task execution
- Agent-assisted strategy lifecycle

However, SYNAPSE aims to become a long-term research system with strong research governance.

## Decision

SYNAPSE will not fork PnLClaw as its long-term core.

It may reference selected design ideas.

## References to Keep

- Chat-first interaction
- Local-first development style
- Skill/task-style workflow
- Tool permission awareness

## Reasons Not to Fork

- Different long-term target
- Need for custom research methodology layer
- Need for strict experiment governance
- Avoid inherited architectural constraints
- Avoid dependency on a domain-specific implementation

## Consequences

Positive:

- Cleaner architecture
- More freedom for research governance
- Better long-term control

Negative:

- Slower initial development
- Need to build more foundation code
