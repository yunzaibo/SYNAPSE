# ADR-008: Temporal Semantics

## Status

Accepted (2026-05-18)

## Context

SYNAPSE 的时间语义需要区分 event time / processing time / market effective time。量化系统和研究系统中时间语义不完整会导致 replay、backtest、review、event reconstruction 污染。

## Decision

所有时间-aware 对象必须声明三种时间：

| 时间类型 | 含义 | 字段 |
|----------|------|------|
| event time | 事件实际发生 | `event_time`, `event_timezone` |
| processing time | 系统处理时间 | `created_at`, `updated_at` |
| market effective time | 市场生效时间 | `market_date`, `market_session` |

## Rules

- 财报 23:00 发布 → `event_time` = 当天, `market_date` = 次日
- 所有时间-aware 对象必须声明 `event_timezone`
- Review 的 `reviewed_at` 用 processing time
- `available_at`: 数据可用时间（盘后数据可能延迟）
- `as_of_date`: 数据截至日期

## Consequences

- 支持 event replay 和 backtest
- 避免时间语义污染
- 长期研究历史可信

## Related

- ADR-007: Security Identity
