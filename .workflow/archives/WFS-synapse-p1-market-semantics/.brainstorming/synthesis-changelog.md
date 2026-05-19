# Synthesis Changelog: P1 Market Semantics Foundation

## Synthesis Decisions

| Decision | Source | Rationale |
|----------|--------|-----------|
| 4 features, all parallel Wave 1 | Cross-role | No inter-feature dependencies; each module is independent |
| Frozen dataclasses over mutable | System Architect | Immutability matches existing `BaseSchema` pattern |
| Parquet over SQLite for storage | Data Architect | Integrates with existing `pd.read_parquet()` and `data_loader.py` |
| `adj_type: str` not `Enum` for AdjustmentRecord | Data Architect | Matches `SymbolType` pattern, keeps serialization simple |
| `factor: float` not `Decimal` in AdjustmentRecord | Data Architect | Consistent with `FactorEngine` which works in `pd.Series(float)` |
| `ROUND_HALF_UP` for price limits | Subject Matter Expert | Chinese exchanges use 四舍五入, not banker's rounding |
| `CHINA_TRADING_DAYS` override set | Subject Matter Expert | Handles holiday-shifted weekdays correctly |
| Signal producers for watchlist integration | System Architect + Data Architect | Plugs into existing `watchlist_generator.py` without changes |
| Monthly northbound Parquet files | Data Architect | ~22 rows/month, small files, range query pattern |
| Filename-based index snapshots | Data Architect | Simpler than SQLite for ~4 rebalances/year |

## Conflicts Resolved

| Conflict | Resolution |
|----------|------------|
| System Architect: `Decimal` for adjustment factors vs Data Architect: `float` | Resolved: `float` for bulk computation (FactorEngine compatibility), `Decimal` for price limit exact boundaries |
| System Architect: `frozen=True, slots=True` vs existing `@dataclass` without frozen | Resolved: New modules use frozen; existing modules unchanged |
| Data Architect: `schemas.py` centralization vs System Architect: per-module `models.py` | Resolved: System Architect approach — `models.py` for shared types, per-module for domain-specific |

## Feature Coverage

| Feature | System Architect | Data Architect | Subject Matter Expert |
|---------|-----------------|----------------|----------------------|
| F-017 TradingCalendar | TradingCalendar, add_trading_days | YAML overrides | Holiday-shifted weekdays |
| F-018 Ex-Right Adjustment | adjustment.py, adjust_prices | Parquet storage, load_adjusted_daily | Forward/backward rules, ROUND_HALF_UP |
| F-019 Northbound Flow | northbound.py, NorthChannel | Monthly Parquet, signal_producers | 净流入 vs 成交额, quota rules |
| F-020 Index Constituent | constituent.py, IndexCode | Snapshot files, query pattern | Rebalance schedule, ST removal |
