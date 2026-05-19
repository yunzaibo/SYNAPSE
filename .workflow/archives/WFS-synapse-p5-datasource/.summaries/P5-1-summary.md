# P5-1 真实数据源接入 — Summary

## Overview

替换了 mock 数据，接入东方财富 + akshare 真实 A 股数据源 API。可插拔 adapter 架构，支持后续扩展其他数据源。

## Files Created

| File | Description |
|------|-------------|
| `synapse/event/datasource.py` | DataSource ABC + MarketData schema |
| `synapse/event/adapters/__init__.py` | Adapters package + adapter_fetch_fn 工厂 |
| `synapse/event/adapters/eastmoney.py` | 东方财富 API adapter（行情 + 资金流向） |
| `synapse/event/adapters/akshare_adapter.py` | akshare adapter（龙虎榜 + 资金面） |
| `tests/unit/test_datasource.py` | DataSource ABC 测试（11 tests） |
| `tests/unit/test_eastmoney_adapter.py` | 东方财富 adapter 测试（30 tests） |
| `tests/unit/test_akshare_adapter.py` | akshare adapter 测试（26 tests） |
| `tests/integration/test_datasource_pipeline.py` | 集成测试（9 tests） |
| `examples/datasource_pipeline.py` | 使用示例 |

## Files Modified

| File | Changes |
|------|---------|
| `synapse/event/__init__.py` | 导出 DataSource, MarketData, adapter_fetch_fn |

## Test Results

- **P5-1 测试**: 76/76 passed
- **P4 回归**: 38/38 passed
- **总计**: 114 tests, 0 failures

## Key Design Decisions

1. **可插拔架构**: DataSource ABC 定义统一接口，适配器独立实现
2. **可选依赖**: akshare 通过 `try/except ImportError` 优雅降级
3. **频率控制**: EastMoneyAdapter 内置 `min_interval_sec=1` 节流
4. **Pipeline 集成**: `adapter_fetch_fn()` 工厂将 DataSource 适配为 StreamingIngestion fetch_fn

## Adapter Capabilities

| Adapter | 数据源 | API | 认证 |
|---------|--------|-----|------|
| EastMoneyAdapter | 东方财富 | 股票行情 + 资金流向 | 无需 |
| AkshareAdapter | akshare | 龙虎榜 + 资金面 | 无需 |
