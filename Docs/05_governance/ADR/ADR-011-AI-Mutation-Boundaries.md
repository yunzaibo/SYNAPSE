# ADR-011: AI Mutation Boundaries

## Status

Accepted (2026-05-18)

## Context

SYNAPSE 是 AI-native 系统，但 AI 可以修改什么需要明确边界，防止 "AI silently mutates truth"。与 Anti-AI-authority 哲学一致。

## Decision

### AI Allowed (可生成/建议)

```txt
generate suggestion          ← 生成研究建议
draft thesis                 ← 起草 thesis（human 确认后写入）
propose review               ← 建议 review（human 确认后写入）
generate watchlist           ← 生成 watchlist
suggest signal               ← 建议信号
```

### AI Forbidden (禁止直接修改)

```txt
overwrite canonical artifact ← 禁止覆盖 Thesis/Decision/Review/Event
auto-confirm thesis          ← 禁止自动确认 thesis
auto-close position          ← 禁止自动关闭 position
rewrite historical review    ← 禁止重写历史 review
modify activity log          ← 禁止修改 activity.jsonl
```

## AI Workflow

```txt
AI 生成 draft → human 审阅 → human 确认 → 写入 canonical artifact
                ↓
        human 拒绝 → 丢弃 draft，不写入任何东西
```

## Rules

- AI 是 research assistant，不是 research authority
- 所有 AI 生成内容必须有 `source_type: ai_generated`
- Human-in-the-loop 是必须的（P1 阶段）
- Anti-AI-authority: 不输出"建议买入"，输出"值得关注"

## Consequences

- 研究历史长期可信
- AI 辅助但不主导
- 与 Anti-同花顺化哲学一致

## Related

- ADR-001: Research-First Instead of Agent-First
- ADR-010: Activity Taxonomy
