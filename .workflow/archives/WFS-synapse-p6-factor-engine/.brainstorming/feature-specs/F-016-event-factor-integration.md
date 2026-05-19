# F-016: Event Factor Integration

**Priority**: P2
**Status**: Draft
**Session**: WFS-synapse-p6-factor-engine

---

## Summary

事件信号 → 因子值转换，将 P3/P4 事件系统输出转化为可计算的因子。

## Motivation

P6 的核心差异化是 event-augmented factor。事件信号需要转换为标准化的因子值。

## Design

### EventFactor Base

```python
class EventFactor(BaseFactor):
    """从事件信号派生因子的基类。"""

    def compute(self, data: pd.DataFrame) -> pd.Series:
        """从事件 DataFrame 中提取信号并转换为因子值。"""
```

### Event-to-Factor Conversion

| Event Type | Factor | Conversion |
|------------|--------|------------|
| SOCIAL_SENTIMENT | sentiment_score | 加权平均情绪分数 |
| CAPITAL_FLOW | capital_flow_signal | 机构/散户资金流差值 |
| EARNINGS | earnings_surprise | 盈利超预期程度 |
| POLICY | policy_impact | 政策影响强度评分 |

### Data Enrichment

```python
def enrich_with_events(df: pd.DataFrame, events: list[Event]) -> pd.DataFrame:
    """将事件信号注入 DataFrame，添加 EventType 列。"""
```

## Acceptance Criteria

- [ ] EventFactor 基类定义
- [ ] 至少 3 种事件因子实现
- [ ] enrich_with_events 桥接函数
- [ ] Point-in-time 校验
- [ ] 单元测试覆盖

## Dependencies

- F-010 (FactorSpec & Registry)
- P3 Event System
- P4 Social Sentiment
