# F-015: Factor Decay Analysis

**Priority**: P2
**Status**: Draft
**Session**: WFS-synapse-p6-factor-engine

---

## Summary

IC 衰减分析 + 半衰期计算，评估因子预测能力的时间特性。

## Motivation

不同因子的预测衰减速度不同。了解衰减特性有助于确定最优调仓频率。

## Design

### Decay Analysis

```python
def compute_ic_decay(factor_values: pd.DataFrame, forward_returns: pd.DataFrame, max_lag: int = 60) -> pd.Series:
    """计算 IC 随 lag 增加的变化。"""

def compute_decay_half_life(ic_decay: pd.Series) -> int:
    """计算 IC 衰减半衰期（IC 降至峰值一半的 lag 天数）。"""
```

### Decay Categories

| Half-Life | Category | 调仓建议 |
|-----------|----------|---------|
| < 5 days | Fast decay | 日频或不使用 |
| 5-20 days | Medium decay | 周频调仓 |
| 20-60 days | Slow decay | 月频调仓 |
| > 60 days | Very slow | 季频调仓 |

## Acceptance Criteria

- [ ] IC 衰减曲线计算正确
- [ ] 半衰期计算正确
- [ ] 衰减分类逻辑实现
- [ ] 单元测试覆盖

## Dependencies

- F-012 (IC/RankIC Auditor)
