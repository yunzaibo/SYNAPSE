# Guidance Specification: P6 因子研究引擎

**Session**: WFS-synapse-p6-factor-engine
**Date**: 2026-05-19
**Mode**: Auto (brainstorm + workflow-plan)

---

## 1. Concepts & Terminology

| Term | Definition | Aliases | Category |
|------|------------|---------|----------|
| Factor (因子) | 从市场数据中提取的 alpha 信号，用于预测股票收益 | Alpha Factor | Core |
| IC (Information Coefficient) | 因子值与未来收益的 Pearson 相关系数 | 信息系数 | Metric |
| RankIC | 因子值与未来收益的 Spearman 秩相关系数 | 秩信息系数 | Metric |
| Factor Engine (因子引擎) | 计算因子值的核心组件，支持自定义因子注册 | Alpha Engine | Component |
| Factor Audit (因子审计) | 评估因子质量的完整流程（IC/RankIC/衰减/换手率） | 因子评估 | Process |
| Factor Portfolio (因子组合) | 多因子加权组合，优化风险收益比 | 因子组合 | Component |
| DataSource (数据源) | P5 已实现的统一数据接口，提供行情/资金流/龙虎榜数据 | 数据适配器 | Infrastructure |
| Event Signal (事件信号) | P3/P4 已实现的事件系统信号（情绪/资金流/跨事件关联） | 事件因子 | Input |
| Factor Rating (因子评级) | 因子质量分级（A/B/C/D），基于 IC 稳定性和衰减特性 | 因子分级 | Output |
| Cross-sectional (截面) | A 股截面因子研究，同一时间点跨股票比较 | 截面研究 | Methodology |
| ICIR (IC Information Ratio) | IC 均值与 IC 标准差的比值，衡量因子稳定性 | IC 信息比率 | Metric |
| Turnover (换手率) | 因子组合持仓变化频率，影响交易成本 | 换手率 | Metric |

## 2. Non-Goals (明确排除)

- **不做高频交易**: 不处理 tick 级别数据，最低频率为日频
- **不做实盘交易执行**: 因子引擎只输出信号和建议，不执行交易
- **不做深度学习因子**: 先实现传统因子（动量/价值/质量/波动），深度学习留后续
- **不做实时因子计算**: MVP 阶段为日频批量计算，不做分钟级实时因子
- **不做多资产类别**: 仅覆盖 A 股股票，不做期货/债券/商品

## 3. Architecture Constraints

- **可插拔因子注册**: 新因子必须通过注册机制添加，不修改引擎核心
- **依赖 P5 DataSource**: 因子计算必须通过 DataSource ABC 获取数据
- **依赖 P3/P4 Event Signal**: 事件因子必须通过事件系统获取信号
- **类型安全**: 所有因子输入/输出必须有类型提示
- **测试覆盖 > 80%**: 核心引擎和每个因子必须有单元测试

## 4. RFC 2119 Constraints

- **MUST** 实现 FactorSpec 数据模型（定义因子的元数据）
- **MUST** 实现 FactorEngine.register() 注册机制
- **MUST** 实现 IC/RankIC 计算和审计报告
- **MUST** 支持至少 5 种传统因子（动量/价值/质量/波动/流动性）
- **SHOULD** 实现因子组合优化（等权/IC 加权/风险平价）
- **SHOULD** 实现因子衰减分析（IC 随时间变化）
- **MAY** 实现因子正交化（去相关性处理）

## 5. Data Model (Draft)

```
FactorSpec {
  name: str
  description: str
  category: str  # "momentum" | "value" | "quality" | "volatility" | "liquidity" | "event"
  inputs: list[str]  # 依赖的数据字段
  lookback_days: int  # 回看窗口
  compute_fn: Callable  # 计算函数
}

FactorResult {
  factor_name: str
  ticker: str
  date: date
  value: float
  zscore: float  # 标准化后的值
}

FactorAuditReport {
  factor_name: str
  ic_mean: float
  ic_std: float
  icir: float
  rank_ic_mean: float
  turnover: float
  decay_half_life: int  # IC 衰减半衰期（天）
  rating: str  # "A" | "B" | "C" | "D"
}

FactorPortfolio {
  name: str
  weights: dict[str, float]  # ticker -> weight
  expected_ic: float
  expected_risk: float
  rebalance_freq: str  # "daily" | "weekly" | "monthly"
}
```

## 6. Selected Roles (Auto)

| Role | Focus |
|------|-------|
| system-architect | 因子引擎架构、扩展性、性能 |
| data-architect | 数据模型、存储策略、数据流 |
| subject-matter-expert | 量化因子领域知识、IC/RankIC 方法论 |

## 7. Feature Decomposition (Draft)

| Feature | Description | Priority |
|---------|-------------|----------|
| F-010 FactorSpec & Registry | 因子元数据模型 + 注册机制 | P0 |
| F-011 FactorEngine Core | 因子计算引擎核心（compute, batch） | P0 |
| F-012 IC/RankIC Auditor | IC/RankIC 计算 + 审计报告 | P0 |
| F-013 Traditional Factors | 5 种传统因子实现 | P1 |
| F-014 Factor Portfolio Optimizer | 因子组合优化（等权/IC加权） | P1 |
| F-015 Factor Decay Analysis | IC 衰减分析 + 半衰期计算 | P2 |
| F-016 Event Factor Integration | 事件信号 → 因子值转换 | P2 |
