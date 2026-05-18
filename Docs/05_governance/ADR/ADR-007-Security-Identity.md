# ADR-007: Security Identity

## Status

Accepted (2026-05-18)

## Context

SYNAPSE 当前用 `ticker: "600519"` 做 identity，但 ticker 不稳定（改名/ST/退市/多市场/ADR）。所有 `linked_*_id` 引用需要一个稳定的 identity 机制。

## Decision

采用 **Composite Security Identity** 格式：

```
{market}.{exchange}.{ticker}
```

示例：
- `cn.sse.600519` — 贵州茅台（上海）
- `cn.szse.000858` — 五粮液（深圳）
- `hk.hkex.0700` — 腾讯（港股）(P2+)
- `us.nasdaq.aapl` — 苹果（美股）(P2+)

## Rules

- 所有 `linked_*_id` 引用用 `security_id`，不用 `ticker`
- 文件命名可用 ticker（人类可读），但 YAML 内必须有 `security_id`
- 未来 ticker 变更时，`security_id` 不变，只更新 `ticker` 字段

## Consequences

- 长期 identity 稳定
- 支持多市场扩展
- 文件名保持人类可读

## Related

- ADR-005: Initial Market Domain
- ADR-006: China A-Shares + Event-driven
