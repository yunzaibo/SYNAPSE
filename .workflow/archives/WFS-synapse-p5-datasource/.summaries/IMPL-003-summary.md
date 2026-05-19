# Task: IMPL-003 akshare adapter（龙虎榜 + 资金面）

## Implementation Summary

### Files Created
- `synapse/event/adapters/__init__.py`: adapters 包初始化
- `synapse/event/adapters/akshare_adapter.py`: AkshareAdapter 实现
- `tests/unit/test_akshare_adapter.py`: 26 个单元测试

### Content Added

**AkshareAdapter** (`synapse/event/adapters/akshare_adapter.py`):
- `source_name` -> `"akshare"`
- `fetch(tickers)`: 统一入口，合并龙虎榜 + 资金面数据
- `fetch_lhb(ticker)`: 调用 `ak.stock_lhb_detail_em()` 获取龙虎榜明细
- `fetch_capital_flow(ticker)`: 调用 `ak.stock_individual_fund_flow()` 获取个股资金流向
- 市场判断: 6 开头 -> sh，其余 -> sz

**Helpers**:
- `_safe_float(value, default)`: 安全类型转换
- `_parse_lhb_rows(df, ticker)`: DataFrame -> MarketData 列表 (data_type="lhb")
- `_parse_capital_flow_rows(df, ticker)`: DataFrame -> MarketData 列表 (data_type="capital_flow")

**Graceful Degradation**:
- `try: import akshare as ak` / `except ImportError: ak = None`
- akshare 未安装时 `fetch()` 返回空列表 + warning 日志

### Test Coverage (26 tests)
- `_safe_float`: 5 tests (类型转换/边界)
- `_parse_lhb_rows`: 4 tests (空/None/单行/多行)
- `_parse_capital_flow_rows`: 3 tests (空/None/多行)
- `fetch_lhb`: 3 tests (成功/API 异常/None 响应)
- `fetch_capital_flow`: 3 tests (沪市/深市/API 异常)
- `fetch` (combined): 3 tests (组合/空列表/多 ticker)
- `GracefulDegradation`: 4 tests (ak=None 场景下各方法)

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.event.adapters.akshare_adapter import AkshareAdapter

adapter = AkshareAdapter()
results = adapter.fetch(["600519", "000001"])
# Returns: list[MarketData] with data_type="lhb" or "capital_flow"
```

### Integration Points
- **AkshareAdapter**: `from synapse.event.adapters.akshare_adapter import AkshareAdapter`
- **DataSource protocol**: implements `DataSource` ABC from `synapse.event.datasource`
- **MarketData schema**: returns `MarketData` with `source="akshare"`, `data_type="lhb"` or `"capital_flow"`

## Status: Complete
