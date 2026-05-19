# Subject-Matter-Expert Analysis: P6 Factor Research Engine

> Domain: Quantitative Factor Research for A-share Cross-sectional Equity
> Perspective: 量化因子研究领域专家

---

## 1. Recommended Factor Categories for A-share Market

A-share 市场的因子体系需要兼顾国际通用框架和本土市场特征。以下按优先级排列。

### 1.1 Momentum (动量) -- HIGH PRIORITY

A-share 动量因子与美股有显著差异。学术研究表明 A股存在**短期反转效应**（1-4周）和**中期动量**（3-6月），但长期动量（12月）在 A股表现不稳定。

| 子因子 | 公式逻辑 | A-share 特征 |
|--------|---------|-------------|
| 1M Reversal | `-(close / close_20d_ago - 1)` | 有效，散户交易驱动 |
| 3M Momentum | `close / close_60d_ago - 1` | 较稳健的中期信号 |
| 6M Momentum | `close / close_120d_ago - 1` | 需跳过最近 1 月（Jegadeesh-Titman 范式） |
| 12M-1M | `close_250d_ago / close_20d_ago - 1` | 长期反转成分，需谨慎使用 |

**关键建议**: 6M-1M 是 A股最经典的动量因子变体。compute 层必须支持 rolling window + skip-month 逻辑。现有 `compute.py` 的 `_compute_timeseries_formula` 已支持 per-ticker groupby + shift/rolling，但需要验证 skip-month 的实现正确性。

### 1.2 Value (价值) -- HIGH PRIORITY

A股价值因子在 2016-2020 大盘蓝筹行情中表现极佳，但 2021 后有所回撤。多维度价值因子比单一 PE 更稳健。

| 子因子 | 输入数据 | 注意事项 |
|--------|---------|---------|
| EP (1/PE) | 净利润 TTM / 市值 | 必须用 TTM 而非年度报告值 |
| BP (1/PB) | 净资产 / 市值 | 需处理负净资产（银行、ST 股） |
| SP (1/PS) | 营收 TTM / 市值 | 适用于亏损公司 |
| DP | 股息率 | A股分红率偏低，信号弱 |

**关键建议**: FactorSpec 的 `inputs` 字段必须明确声明数据源是 TTM 还是年度报告值。这是 look-ahead bias 的高发区。

### 1.3 Quality (质量) -- HIGH PRIORITY

A股质量因子近年受到越来越多关注，尤其在"高质量发展"政策导向下。

| 子因子 | 公式 | 备注 |
|--------|------|------|
| ROE | 净利润 / 净资产 | 核心质量指标 |
| GrossMargin | 毛利润 / 营收 | 稳定性好 |
| DebtToAsset | 总负债 / 总资产 | 低值为优 |
| Accruals | (净利润 - 经营现金流) / 总资产 | 盈余质量信号 |

### 1.4 Volatility (波动率) -- MEDIUM PRIORITY

A股散户占比高导致波动率因子有独特的 alpha。低波动异象在 A股存在但弱于美股。

| 子因子 | 计算方式 |
|--------|---------|
| RealizedVol | 20 日收益率标准差 |
| IdiosyncraticVol | 残差波动率（回归剔除市场因子后） |
| DownsideVol | 仅计算负收益的标准差 |

### 1.5 Liquidity (流动性) -- MEDIUM PRIORITY

A股流动性因子对小盘股尤其重要。

| 子因子 | 计算方式 | A-share 特征 |
|--------|---------|-------------|
| Turnover | 成交量 / 流通股本 | 换手率是 A股核心指标 |
| AmihudIlliquidity | `|ret| / volume` | 适用于日频 |
| LnMarketCap | ln(流通市值) | 流动性代理变量 |

### 1.6 Sentiment / Event (情绪/事件) -- MEDIUM PRIORITY，P6 可选

A股散户主导的特性使情绪因子有独特价值，但数据获取难度大。

| 子因子 | 数据源 | 可行性 |
|--------|-------|--------|
| MoneyFlow | 主力资金净流入 | 需 Level-2 数据 |
| MarginRatio | 融资余额 / 融券余额 | 公开数据 |
| AnalystSentiment | 一致预期调整方向 | Wind/Choice 接口 |

**P6 建议**: 优先实现 Momentum/Value/Quality 三大类作为内置因子库，Volatility 和 Liquidity 作为二级优先，Sentiment 标记为扩展接口但不在 P6 核心中实现。

---

## 2. IC/RankIC Evaluation Framework

现有 `audit.py` 已实现基础 IC 和 RankIC 计算。P6 需要在此基础上构建完整的因子评估框架。

### 2.1 IC 计算最佳实践

**Pearson IC vs Spearman RankIC**:

- RankIC（Spearman）是 A股因子评估的**首选指标**。原因：因子值和收益率分布通常非正态，Spearman 对异常值更鲁棒
- Pearson IC 作为辅助参考，用于检测因子与收益之间是否存在非线性关系（Pearson IC 显著低于 RankIC 时可能存在非线性）
- 现有 `audit.py` 同时计算两者，这是正确的设计选择

**Forward Return 定义**:

- 标准做法: `fwd_ret = close_t+20 / close_t - 1`（20 个交易日，约 1 个月）
- A-share 特殊: 需处理停牌日（forward return 不应包含停牌天数）
- P6 应支持 configurable forward period（5d/10d/20d/60d）

### 2.2 IC Decay Analysis

IC decay 是判断因子 alpha 衰减速度的核心工具：

```
IC(lag) = corr(factor_t, return_t+lag),  lag = 1, 2, ..., 60
```

- **快衰减因子** (IC 在 5 日内降至 0.02 以下): 适合高频调仓，需低交易成本环境
- **慢衰减因子** (IC 在 20 日仍 > 0.03): 适合月频调仓，容错空间大
- **建议阈值**: IC decay half-life > 10 个交易日的因子才值得纳入月频组合

P6 应实现 `compute_ic_decay(factor_values, returns, max_lag=60)` 函数，返回 IC 衰减曲线数据。

### 2.3 ICIR Thresholds for Factor Quality Rating

ICIR（IC Information Ratio）= mean(IC) / std(IC)，是因子稳定性的核心指标。

| Rating | ICIR Range | 含义 | 行动 |
|--------|-----------|------|------|
| A | > 0.5 | 高质量，IC 稳定 | 优先纳入组合 |
| B | 0.3 - 0.5 | 中等质量，IC 波动较大 | 可用但需风险控制 |
| C | 0.1 - 0.3 | 弱信号，噪声大 | 谨慎使用或与其他因子组合 |
| D | < 0.1 | 无效因子 | 淘汰 |

**A-share 特殊考虑**:
- 单因子 ICIR > 0.5 在 A股已属优秀（市场噪音大）
- 需要至少 2 年（约 500 个交易日）的数据计算才有统计意义
- 应使用 Newey-West 调整 t-stat 来处理 IC 的序列相关性

### 2.4 Coverage 与 Missing Rate

现有 `audit.py` 的 coverage 计算基于非 NaN 比例，这是正确的。P6 应增加：

- **最低 Coverage 阈值**: factor_values 非 NaN 比例 < 0.3 时应标记 WARNING
- **Missing Rate by Date**: 检查是否存在某一天大面积缺失（可能暗示数据质量问题）
- **Universe Consistency**: 确保因子计算的股票池在时间维度上一致

---

## 3. Factor Combination Methodology

多因子组合是 P6 的核心能力之一。

### 3.1 Weighting Schemes

| 方法 | 公式 | 优点 | 缺点 | A-share 适用性 |
|------|------|------|------|---------------|
| Equal Weight | `w_i = 1/N` | 简单，无估计误差 | 忽略因子质量差异 | 适合初学者 |
| IC-weighted | `w_i = IC_i / sum(IC)` | 质量越高权重越大 | IC 估计噪声大 | 需 rolling IC |
| ICIR-weighted | `w_i = ICIR_i / sum(ICIR)` | 兼顾质量和稳定性 | 计算窗口选择敏感 | 推荐方法 |
| Risk Parity | 各因子对组合风险贡献相等 | 分散化好 | 需要协方差矩阵估计 | 适合稳定期 |

**P6 建议**: 默认实现 ICIR-weighted，提供 equal weight 作为 baseline 对比。risk parity 可作为高级选项。

### 3.2 Factor Orthogonalization (去相关性)

A股因子之间存在显著相关性（如 Value 和 Quality 的 BP 与 ROE 高度相关）。去相关方法：

1. **Residual Orthogonalization**: 用其他因子对目标因子做截面回归，取残差。最常用
2. **Gram-Schmidt Orthogonalization**: 有序正交化，适合有明确优先级的因子体系
3. **PCA-based**: 主成分降维，适合因子数量多时

**P6 建议**: 实现 Residual Orthogonalization 作为标准方法。输入参数为 factor_matrix 和 factor_order（决定正交化顺序）。

### 3.3 Rebalancing Frequency

| 频率 | 适用因子类型 | 交易成本影响 | A-share 约束 |
|------|------------|-------------|-------------|
| Daily | 高频动量、反转 | 高 | T+1 限制日内多次调仓 |
| Weekly | 短期动量 | 中 | 可行 |
| Monthly | 大多数因子 | 低 | 推荐默认频率 |
| Quarterly | 价值、质量 | 极低 | 适合低频策略 |

**T+1 约束**: A股 T+1 交割制度意味着当天买入的股票次日才能卖出。调仓频率如果高于日频，需要在 backtest 中显式处理这个约束。

---

## 4. A-share Specific Considerations

### 4.1 Price Limits (涨跌停板)

A股主板 ±10%、创业板/科创板 ±20% 涨跌停限制。对因子研究的影响：

- 涨停/跌停日的成交量极端萎缩，流动性因子失真
- 连续涨停的股票因子值可能异常（如 momentum 因子饱和）
- **处理建议**: 涨停/跌停日标记 `is_limit = True`，因子计算时可选排除或特殊处理

### 4.2 Suspension (停牌)

A股停牌频率远高于其他市场。影响：

- 因子计算时停牌股票缺少最新价，forward return 无法计算
- 停牌期间的复牌补跌/补涨对回测收益有重大影响
- **处理建议**: 停牌日 factor_values 设为 NaN，forward return 使用复牌后首个交易日价格

### 4.3 ST/退市风险股

ST 股票和退市风险股的因子值可能严重偏离正常范围：

- 负净资产导致 BP 异常
- 亏损导致 EP/ROE 为负
- **处理建议**: 默认排除 ST/*ST/退市整理期股票，但保留可配置选项

### 4.4 Sector Neutralization

A股行业轮动明显，不做行业中性的因子在某些年份可能严重跑输：

- 一级行业分类（申万一级 31 个行业）是标准做法
- 行业中性 = 因子值在行业内标准化后再 cross-sectional 排序
- **P6 建议**: sector neutralization 作为可选前处理步骤，不强制

### 4.5 Data Quality

A股财务数据的特殊问题：

- 季报/年报发布有时间差（look-ahead bias 高发区）
- 财务数据修订（更正公告）
- 数据供应商之间的口径差异（净利润 TTM 计算方式不同）
- **P6 建议**: FactorSpec 的 `inputs` 必须声明数据口径和发布日期假设

---

## 5. Quality Control Checklist

P6 Factor Research Engine 的质量控制清单，分为系统级和因子级。

### 5.1 System-level QC

| 检查项 | 验证方法 | 严重级别 |
|--------|---------|---------|
| No look-ahead bias | 因子公式中使用的数据日期 <= 计算日期 | BLOCKER |
| No survivorship bias | 股票池包含已退市股票（使用全量快照） | BLOCKER |
| Forward return 不含未来信息 | fwd_ret 计算仅使用 close_t+1...close_t+n | BLOCKER |
| 停牌处理正确性 | 停牌日不参与 IC 计算 | HIGH |
| 涨跌停处理 | 涨停日卖出/跌停日买入不可执行 | HIGH |
| 数据对齐 | factor_values 和 forward_returns 的 date+ticker 严格对齐 | BLOCKER |

### 5.2 Factor-level QC

| 检查项 | 阈值 | 说明 |
|--------|------|------|
| ICIR | >= 0.3 | 低于此值视为无效因子 |
| IC t-stat | >= 2.0 | Newey-West 调整后 |
| Coverage | >= 70% | 因子值非 NaN 比例 |
| Turnover | 记录但不淘汰 | 过高 turnover 消耗 alpha |
| Drawdown of cumulative IC | < 30% | IC 累积曲线的最大回撤 |
| Factor correlation | < 0.7 | 与已有因子的相关性 |
| Leakage risk | == low | 现有 audit.py 已实现 |

### 5.3 Overfitting Prevention

- **Multiple Testing Correction**: 测试 100 个因子时，Bonferroni 校正后的显著性阈值为 0.05/100 = 0.0005
- **Out-of-sample Validation**: 因子至少在独立样本期间（如最近 6 个月）验证 IC > 0
- **Purged Cross-validation**: 时间序列数据的交叉验证必须 purge 训练集和测试集的重叠窗口
- **Complexity Penalty**: 公式越复杂的因子，要求的 ICIR 阈值越高

---

## 6. Gap Analysis: P0 vs P6

| Capability | P0 Status | P6 Gap |
|-----------|-----------|--------|
| FactorSpec model | Implemented | 需扩展: add `sector`, `data_source`, `publication_lag` fields |
| compute_factor | Implemented | 需扩展: support skip-month, sector neutralization, winsorization |
| audit_factor | Implemented (IC, RankIC) | 需扩展: IC decay, ICIR, Newey-West t-stat, coverage-by-date |
| Multi-factor combination | Not implemented | FULL GAP: weighting, orthogonalization, rebalancing |
| Factor library | Not implemented | FULL GAP: built-in factor catalog, factor search |
| Walk-forward validation | Deferred to P1 | FULL GAP: rolling window, purged CV |
| Factor correlation matrix | Placeholder | 需实现: correlation cluster, VIF calculation |

---

## 7. Key Recommendations

1. **FactorSpec schema 扩展**: 添加 `data_source`（TTM/annual）、`publication_lag`（财报发布延迟天数）、`sector` 字段，从源头防止 look-ahead bias
2. **ICIR-first 评估体系**: 以 ICIR 为核心质量指标，IC 作为辅助。现有 audit.py 的 leakage heuristic（IC > 0.95 判断为 high risk）过于粗糙，应改为基于 Newey-West t-stat 的统计检验
3. **A-share 数据前处理管线**: 建立标准化的 pre-processing pipeline（停牌过滤 → 涨跌停标记 → ST 排除 → 行业中性 → winsorization），作为因子计算的前置步骤
4. **Factor Orthogonalization 作为默认行为**: 多因子组合时，默认执行 residual orthogonalization，避免因子间高度相关导致的权重虚高
5. **Built-in Factor Library**: P6 应提供 15-20 个经典 A-share 因子的 YAML 定义，作为用户快速上手的 baseline，同时作为内置因子质量的 regression test

---

## 8. Cross-Feature Dependencies

| 依赖方向 | Feature | 说明 |
|---------|---------|------|
| Factor Engine -> Data Plane | REQ-002 | 因子计算依赖数据层提供 clean OHLCV + financials |
| Factor Engine -> Backtest | REQ-006 | 因子评估结果驱动回测参数配置 |
| Factor Engine -> Experiment | REQ-005 | 每次因子实验需记录完整 lineage |
| Factor Engine <- AI Assistant | REQ-008 | AI 可辅助生成因子公式，但需 traceability |
| Multi-factor -> Factor Audit | REQ-004 | 组合因子也需要独立 audit |
