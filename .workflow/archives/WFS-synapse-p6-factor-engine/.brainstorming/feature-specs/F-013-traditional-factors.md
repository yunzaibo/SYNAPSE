# F-013: Traditional Factors

**Priority**: P1
**Status**: Draft
**Session**: WFS-synapse-p6-factor-engine

---

## Summary

5 种传统因子实现：动量、价值、质量、波动率、流动性。

## Motivation

P6 MVP 需要内置一组经过验证的传统因子，作为因子引擎的验证和参考。

## Factor Categories

### Momentum (动量)

| Factor | Formula | A-share 特征 |
|--------|---------|-------------|
| momentum_1m | `-(close / close_20d_ago - 1)` | 短期反转，散户驱动 |
| momentum_3m | `close / close_60d_ago - 1` | 中期动量 |
| momentum_6m_1m | `close_120d_ago / close_20d_ago - 1` | 经典 Jegadeesh-Titman |

### Value (价值)

| Factor | Formula | Notes |
|--------|---------|-------|
| ep | `net_profit_ttm / market_cap` | 市盈率倒数，必须用 TTM |
| bp | `net_asset / market_cap` | 市净率倒数 |
| sp | `revenue_ttm / market_cap` | 市销率倒数 |

### Quality (质量)

| Factor | Formula | Notes |
|--------|---------|-------|
| roe | `net_profit / net_asset` | 核心质量指标 |
| gross_margin | `gross_profit / revenue` | 稳定性好 |
| debt_to_asset | `total_debt / total_asset` | 低值为优 |

### Volatility (波动率)

| Factor | Formula | Notes |
|--------|---------|-------|
| realized_vol_20d | `std(daily_returns, 20d)` | 20 日已实现波动率 |
| idiosyncratic_vol | `std(residuals, 60d)` | 特质波动率 |

### Liquidity (流动性)

| Factor | Formula | Notes |
|--------|---------|-------|
| turnover_20d | `mean(volume / float_shares, 20d)` | 20 日平均换手率 |
| amihud_illiquidity | `mean(abs(return) / volume, 20d)` | Amihud 非流动性 |

## Acceptance Criteria

- [ ] 5 种因子类别，每类至少 2 个因子
- [ ] 所有因子继承 BaseFactor
- [ ] FactorSpec 定义完整
- [ ] 单元测试验证计算逻辑
- [ ] A-share 特殊处理（涨跌停、停牌）

## Dependencies

- F-010 (FactorSpec & Registry)
- F-011 (FactorEngine Core)
