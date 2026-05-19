# Planning Notes

**Session**: WFS-synapse-p1-market-semantics
**Created**: 2026-05-19T20:00:00Z

## User Intent (Phase 1)

- **GOAL**: P1 Market Semantics Foundation — 中国 A 股市场语义层
- **SCOPE**: TradingCalendar enhancement (F-017), Ex-Right Adjustment (F-018), Northbound Flow (F-019), Index Constituent (F-020)
- **KEY_CONSTRAINTS**: All additive to existing code, zero breaking changes. 4 independent modules in `synapse/core/market/`

---

## Context Findings (Phase 2)

- **CRITICAL_FILES**: synapse/core/market/calendar.py, data_loader.py, semantics.py
- **ARCHITECTURE**: Frozen dataclass, Enum, ABC, Parquet/CSV, DataSource adapter
- **CONFLICT_RISK**: low (all additive, no breaking changes)
- **CONSTRAINTS**: Existing API unchanged, ROUND_HALF_UP for price limits, source field provenance

## Conflict Decisions (Phase 3)
(To be filled if conflicts detected)

## Consolidated Constraints (Phase 4 Input)
1. All additive to existing code, zero breaking changes
2. 4 independent modules with no inter-dependencies
3. Follow existing project conventions: `@dataclass`, `to_dict()`/`from_dict()`, `__future__.annotations`
4. Parquet-based storage for adjustment factors, northbound flow, index constituents
5. Existing `is_trading_day` / `next_trading_day` / `trading_days_between` API unchanged
6. `data_loader.py` gains optional `adj_type` parameter with default `NONE`

---

## Task Generation (Phase 4)
(To be filled by action-planning-agent)

## N+1 Context
### Decisions
| Decision | Rationale | Revisit? |
|----------|-----------|----------|

### Deferred
- [ ] (For N+1)
