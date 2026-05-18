# P0 Test Plan

## Test Scope

P0 tests focus on reproducibility and boundary protection.

## Unit Tests

- Data metadata validation
- Factor spec validation
- Experiment record creation
- Backtest config validation

## Integration Tests

- Sample data → factor audit
- Factor audit → backtest
- Backtest → report

## Governance Tests

- Missing data timestamp warning
- Missing transaction cost warning
- Invalid date range error
- Agent forbidden action simulation

## Manual Acceptance Test

Run a full sample research loop:

```txt
Load sample data
→ Define sample factor
→ Audit factor
→ Run simple backtest
→ Generate report
```
