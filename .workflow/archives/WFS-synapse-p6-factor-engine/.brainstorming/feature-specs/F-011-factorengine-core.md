# F-011: FactorEngine Core

**Priority**: P0
**Status**: Draft
**Session**: WFS-synapse-p6-factor-engine

---

## Summary

因子计算引擎核心，支持批量计算和单因子计算，集成 DataSource 和 Event 系统。

## Motivation

需要一个统一的计算引擎来调度所有因子的计算，处理数据获取、转换、计算、存储。

## Design

### FactorEngine

```python
class FactorEngine:
    def __init__(self, registry: FactorRegistry, data_source: DataSource): ...

    def compute_factor(self, factor_id: str, tickers: list[str], date: date) -> pd.Series:
        """计算单个因子值。"""

    def compute_batch(self, factor_ids: list[str], tickers: list[str], date: date) -> pd.DataFrame:
        """批量计算多个因子。"""

    def compute_all(self, tickers: list[str], date: date) -> pd.DataFrame:
        """计算所有已注册因子。"""
```

### Data Flow

```
DataSource.fetch(tickers) -> MarketData[]
    -> _to_dataframe(MarketData[]) -> pd.DataFrame
    -> enrich_with_events(df, events) -> pd.DataFrame
    -> factor.compute(df) -> pd.Series
    -> FactorResult (存 Parquet)
```

### Point-in-Time 校验

- Event 信号 MUST 使用 `event_date <= compute_date` 过滤
- `publication_lag` 字段控制数据可用延迟

## Acceptance Criteria

- [ ] FactorEngine 支持 compute_factor / compute_batch / compute_all
- [ ] 数据流: DataSource -> DataFrame -> Factor -> Series 正确
- [ ] Point-in-time 校验防止 look-ahead bias
- [ ] 单因子失败不阻塞其他因子 (PartialResult)
- [ ] 单元测试覆盖正常/异常场景

## Dependencies

- F-010 (FactorSpec & Registry)
- P5 DataSource
