# ADR-010: Activity Taxonomy

## Status

Accepted (2026-05-18)

## Context

`activity.jsonl` 是 immutable 操作日志，需要明确谁写、写什么、不写什么，防止 runtime dump trashcan。

## Decision

### Activity Types (Must Log)

```txt
thesis.created / thesis.revised
decision.recorded
review.completed
watchlist.generated
position.opened / position.closed
```

### Runtime Activities (Optional)

```txt
projection.rebuilt
workspace.indexed
sidecar.restarted
```

### Explicitly Forbidden

```txt
token.stream / llm.raw.reasoning / debug.spam / file.watcher.event
```

## Activity Entry Format

```jsonl
{"ts":"2026-05-18T10:00:00+08:00","type":"thesis.created","obj_id":"ths_7f8c91","actor":"human","summary":"创建消费恢复 thesis"}
```

## Rules

- Human actions: 由 UI/CLI 直接写入
- AI suggestions: AI 生成建议，human 确认后写入（AI 不直接写 activity）
- Runtime events: 由 Core Runtime 写入（仅 projection.rebuilt / workspace.indexed）

## Consequences

- activity.jsonl 保持可维护
- 避免 log pollution
- 支持 event replay

## Related

- ADR-011: AI Mutation Boundaries
