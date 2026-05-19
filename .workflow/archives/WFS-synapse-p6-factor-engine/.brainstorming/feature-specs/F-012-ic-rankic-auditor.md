# F-012: IC/RankIC Auditor

**Priority**: P0
**Status**: Draft
**Session**: WFS-synapse-p6-factor-engine

---

## Summary

IC/RankIC 计算 + 审计报告生成。评估因子质量的核心组件。

## Motivation

因子计算出来后需要评估其预测能力和稳定性。IC/RankIC 是量化因子评估的标准方法。

## Design

### IC 计算

```python
def compute_ic(factor_values: pd.Series, forward_returns: pd.Series) -> float:
    """Pearson IC: 因子值与未来收益的线性相关性。"""

def compute_rank_ic(factor_values: pd.Series, forward_returns: pd.Series) -> float:
    """Spearman RankIC: 因子值与未来收益的秩相关性 (更稳健)。"""

def compute_rolling_ic(factor_series: pd.DataFrame, window: int = 60) -> pd.Series:
    """滚动窗口 IC，评估因子稳定性。"""
```

### FactorAuditReport

```python
@dataclass
class FactorAuditReport:
    factor_name: str
    ic_mean: float              # IC 均值
    ic_std: float               # IC 标准差
    icir: float                 # ICIR = ic_mean / ic_std
    rank_ic_mean: float         # RankIC 均值
    turnover: float             # 因子换手率
    decay_half_life: int        # IC 衰减半衰期（天）
    coverage: float             # 行业覆盖率
    rating: str                 # "A" | "B" | "C" | "D"
```

### 评级标准 (ICIR-based)

| Rating | ICIR Threshold | Description |
|--------|---------------|-------------|
| A | >= 0.5 | 优秀因子，IC 稳定且显著 |
| B | >= 0.3 | 良好因子，有一定预测能力 |
| C | >= 0.1 | 一般因子，需谨慎使用 |
| D | < 0.1 | 弱因子，不建议使用 |

## Acceptance Criteria

- [ ] IC/RankIC 计算正确 (对比 pandas corr 验证)
- [ ] 滚动 IC 计算支持自定义窗口
- [ ] ICIR 评级标准实现
- [ ] 审计报告生成完整
- [ ] 单元测试覆盖

## Dependencies

- F-010 (FactorSpec)
