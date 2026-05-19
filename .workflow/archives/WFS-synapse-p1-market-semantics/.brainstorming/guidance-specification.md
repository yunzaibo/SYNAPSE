# Guidance Specification: P1 Market Semantics Foundation

## Concepts & Terminology

| Term | Definition | Aliases | Category |
|------|-----------|---------|----------|
| TradingCalendar | A股交易日历，周末+法定节假日检测 | 交易日历 | market |
| T+1 Settlement | T日买入，T+1日方可卖出 | T+1 结算 | market |
| PriceLimit | 涨跌停板，按板块不同 ±5%/10%/20%/30% | 涨跌停 | market |
| Suspension | 停牌处理，记录停牌日期集合 | 停牌 | market |
| ExRight | 复权处理：前复权/后复权/不复权 | 复权 | market |
| NorthboundFlow | 北向资金净流入（沪股通/深股通） | 北向资金 | flow |
| IndexConstituent | 指数成分股列表（沪深300、中证500等） | 成分股 | index |
| SymbolType | A股标的类型：主板/创业板/科创板/ST/北交所 | 板块类型 | market |

## Non-Goals

1. **不做实时行情推送** — P5 DataSource 适配器已覆盖数据获取
2. **不做自动交易执行** — SYNAPSE 是研究工具，不是交易平台
3. **不做完整回测框架** — 已有 synapse/backtest
4. **不做国际市场语义** — 仅覆盖 A 股

## Constraints

- RFC 2119: 所有交易日判断 MUST 使用 TradingCalendar，禁止手动判断周末
- RFC 2119: 涨跌停计算 MUST 考虑 SymbolType，禁止硬编码 ±10%
- RFC 2119: T+1 验证 MUST 使用 next_trading_day，禁止简单日期加减
- 所有日期计算 MUST 使用 `datetime.date`，禁止字符串比较
- 复权因子 MUST 从数据源获取，禁止自行估算
- 北向资金数据 MUST 标注数据来源和时间戳
