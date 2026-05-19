# Tasks: F-007/F-008/F-009 Event-Driven Extensions

## Wave 5: F-007 + F-008 (Parallel)

- [x] **IMPL-001**: F-007 Sentiment Propagation -- schema + viral coefficient algorithm -> [./.task/IMPL-001.json](./.task/IMPL-001.json)
- [x] **IMPL-002**: F-008 Capital Flow Divergence -- schema + divergence scoring -> [./.task/IMPL-002.json](./.task/IMPL-002.json)

## Wave 5+6: Tests + Correlation

- [x] **IMPL-003**: F-007/F-008 Sentiment + Divergence tests (14 tests) -> [./.task/IMPL-003.json](./.task/IMPL-003.json)
- [x] **IMPL-004**: F-009 Cross-Event Correlation -- schema + affinity matrix + engine -> [./.task/IMPL-004.json](./.task/IMPL-004.json)
- [x] **IMPL-005**: F-009 Cross-Event Correlation tests (10 tests) -> [./.task/IMPL-005.json](./.task/IMPL-005.json)

## Dependencies

```
IMPL-001 (F-007) ──┐
                    ├──> IMPL-003 (Tests 14) ──> IMPL-004 (F-009) ──> IMPL-005 (Tests 10)
IMPL-002 (F-008) ──┘
```

## Status Legend

- `- [ ]` = Pending task
- `- [x]` = Completed task

## Test Counts

| Task | Feature | Tests | Command |
|------|---------|-------|---------|
| IMPL-001 | F-007 Sentiment | -- (impl) | -- |
| IMPL-002 | F-008 Divergence | -- (impl) | -- |
| IMPL-003 | F-007+F-008 | 8+6=14 | `py -m pytest tests/unit/test_sentiment_propagation.py tests/unit/test_capital_flow_divergence.py -p no:asyncio -q` |
| IMPL-004 | F-009 Correlation | -- (impl) | -- |
| IMPL-005 | F-009 | 10 | `py -m pytest tests/unit/test_cross_event_correlation.py -p no:asyncio -q` |
| **Total** | | **24** | |
