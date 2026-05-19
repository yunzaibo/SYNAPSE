# IMPL_PLAN: P5-1 真实数据源接入

## Goal

替换 P4 mock 数据，接入真实 A 股数据源 API，建立可插拔的 DataSource 适配器架构。

## Scope

- DataSource 适配器协议（ABC）
- 东方财富 API adapter（行情 + 资金流向）
- akshare adapter（UZI-Skill 模式，龙虎榜/资金面/K线）
- StreamingIngestion 集成
- 单元测试 + 集成测试

## Architecture

```
DataSource (ABC)
  ├── EastMoneyAdapter     # 东方财富 API（无需认证）
  └── AkshareAdapter       # akshare 库（UZI-Skill 模式）

PollingSource.config → DataSource.fetch() → StreamBuffer → StreamingIngestion
```

## Task Breakdown

| ID | Title | Wave | Depends | Est |
|----|-------|------|---------|-----|
| IMPL-001 | DataSource adapter protocol | 1 | — | S |
| IMPL-002 | 东方财富 adapter（行情 + 资金流向） | 2 | IMPL-001 | M |
| IMPL-003 | akshare adapter（龙虎榜 + 资金面） | 2 | IMPL-001 | M |
| IMPL-004 | StreamingIngestion 集成 + 示例 | 3 | IMPL-002, IMPL-003 | S |
| IMPL-005 | 单元测试 + 集成测试 | 4 | IMPL-004 | M |

## Waves

- **Wave 1**: IMPL-001（协议定义）
- **Wave 2**: IMPL-002 + IMPL-003（并行，两个 adapter 独立）
- **Wave 3**: IMPL-004（集成）
- **Wave 4**: IMPL-005（测试）

## Key Decisions

1. **DataSource ABC**: 统一 `fetch(tickers) -> list[dict]` 接口，返回标准化字典
2. **东方财富优先**: 无需认证、接口丰富、响应快
3. **akshare 可选**: 作为 fallback，不强制安装
4. **频率控制**: 内置 `min_interval_sec` 防止 IP 被封

## Test Command

```bash
py -m pytest -p no:asyncio
```
