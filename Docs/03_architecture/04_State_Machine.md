# Research Task State Machine

## Research Task States

```txt
draft
→ planned
→ data_ready
→ factor_defined
→ audited
→ backtested
→ risk_reviewed
→ reported
→ archived
```

## Terminal States

```txt
archived
failed
cancelled
```

## State Definitions

- draft: research idea exists but is not structured.
- planned: research plan is created.
- data_ready: required data spec and sample data are available.
- factor_defined: factor spec is available.
- audited: factor audit has run or been recorded.
- backtested: backtest has run or been recorded.
- risk_reviewed: risk checklist has been completed.
- reported: research report has been generated.
- archived: task is closed and stored as research memory.

## Failure Rules

A task can move to `failed` if data is missing, factor cannot be computed, backtest cannot run, governance check fails, or required assumptions are absent.

## Agent Rule

Agents may suggest state transitions, but the system must record who or what triggered the transition.
