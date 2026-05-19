# F-014: Factor Portfolio Optimizer

**Priority**: P1
**Status**: Draft
**Session**: WFS-synapse-p6-factor-engine

---

## Summary

因子组合优化，支持等权、IC 加权、风险平价三种方法。

## Motivation

单个因子预测能力有限，多因子组合可以提高稳定性和收益风险比。

## Design

### Portfolio Optimization Methods

```python
class FactorPortfolioOptimizer:
    def equal_weight(self, factor_values: pd.DataFrame) -> dict[str, float]:
        """等权组合：所有因子权重相同。"""

    def ic_weighted(self, factor_values: pd.DataFrame, ic_history: pd.DataFrame) -> dict[str, float]:
        """IC 加权：按历史 IC 均值加权。"""

    def risk_parity(self, factor_values: pd.DataFrame) -> dict[str, float]:
        """风险平价：按因子波动率倒数加权。"""
```

### FactorPortfolio

```python
@dataclass
class FactorPortfolio:
    name: str
    weights: dict[str, float]      # factor_id -> weight
    method: str                     # "equal" | "ic_weighted" | "risk_parity"
    expected_ic: float
    expected_risk: float
    rebalance_freq: str             # "daily" | "weekly" | "monthly"
    created_at: datetime
```

### Constraints

- T+1 结算约束：调仓频率不超过 daily
- 换手率控制：单次调仓换手率 < 30%
- 行业暴露控制：单行业权重 < 30%

## Acceptance Criteria

- [ ] 三种优化方法实现
- [ ] 权重总和为 1
- [ ] 换手率计算正确
- [ ] 约束条件检查
- [ ] 单元测试覆盖

## Dependencies

- F-012 (IC/RankIC Auditor)
