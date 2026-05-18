# Analytics Object Taxonomy

> P2 新增 Analytics 对象的分类体系。
> 统一命名、语义、生命周期，避免 P3/P4 出现 object system 失控。

## Status

Proposed (2026-05-18)

---

## 1. Taxonomy Overview

```
Analytics Objects
├── Report (分析报告)
│   ├── ErrorPatternReport
│   └── BehavioralReport
├── Profile (用户画像)
│   ├── BehavioralProfile
│   └── BiasProfile
├── Alert (告警/提示)
│   ├── DriftAlert
│   └── StaleAlert
├── Insight (洞察)
│   ├── CorrelationInsight
│   └── TrendInsight
├── Evolution (演化)
│   ├── ThesisEvolution
│   └── ResearchEvolution
└── Summary (摘要)
    ├── DailySummary
    └── WeeklySummary
```

---

## 2. Object Definitions

### 2.1 Report

**定义**: 基于数据的结构化分析结果。

| Object | Description | Input | Output |
|--------|-------------|-------|--------|
| ErrorPatternReport | 错误模式分析报告 | Reviews | 错误类型、频率、关联 |
| BehavioralReport | 决策行为分析报告 | Decisions | 行为模式、偏好、一致性 |

**Lifecycle**: `append-only`（新报告追加，不修改旧报告）

**Storage**: `analytics/reports/<type>/<date>.yaml`

```yaml
# Example: ErrorPatternReport
id: epr_20260518_001
type: error_pattern_report
computed_at: "2026-05-18T14:00:00+08:00"
input_snapshot:
  reviews_analyzed: 15
  date_range: ["2026-05-01", "2026-05-18"]
output:
  error_patterns:
    - type: overconfidence
      frequency: 0.35
      examples: ["rev_001", "rev_005"]
    - type: anchoring
      frequency: 0.20
      examples: ["rev_003"]
```

---

### 2.2 Profile

**定义**: 基于历史数据的用户/标的画像。

| Object | Description | Input | Output |
|--------|-------------|-------|--------|
| BehavioralProfile | 用户决策行为画像 | Decisions + Reviews | 风格、偏好、一致性 |
| BiasProfile | 用户偏差画像 | Decisions + Reviews | 偏差类型、程度、趋势 |

**Lifecycle**: `snapshot`（定期快照，保留历史版本）

**Storage**: `analytics/profiles/<type>/<ticker_or_user>/<date>.yaml`

```yaml
# Example: BehavioralProfile
id: bp_600519_20260518
type: behavioral_profile
ticker: "600519"
computed_at: "2026-05-18T14:00:00+08:00"
snapshot_date: "2026-05-18"
data:
  decision_style: cautious
  time_horizon_preference: medium_term
  attention_origin偏好: event_attention
  consistency_score: 0.75
  sample_size: 8
```

---

### 2.3 Alert

**定义**: 需要用户关注的提示/告警。

| Object | Description | Input | Output |
|--------|-------------|-------|--------|
| DriftAlert | Thesis 漂移告警 | Thesis + Reviews | 漂移程度、建议 |
| StaleAlert | 数据过期告警 | Analytics metadata | 过期组件、重建建议 |

**Lifecycle**: `ephemeral`（用户确认后归档）

**Storage**: `analytics/alerts/<type>/<date>.yaml`

```yaml
# Example: DriftAlert
id: da_20260518_001
type: drift_alert
thesis_id: "ths_7f8c91"
computed_at: "2026-05-18T14:00:00+08:00"
severity: medium  # low | medium | high | critical
drift_type: partial_invalidated
evidence:
  supporting_reviews: 2
  contradicting_reviews: 1
  drift_velocity: 0.15
recommendation: "考虑更新 thesis 或标记为 partially_confirmed"
status: active  # active | acknowledged | resolved | archived
```

---

### 2.4 Insight

**定义**: 从数据中发现的模式/关联。

| Object | Description | Input | Output |
|--------|-------------|-------|--------|
| CorrelationInsight | 事件→结果关联洞察 | Events + Reviews | 关联强度、置信度 |
| TrendInsight | 趋势洞察 | Multiple objects | 趋势方向、强度 |

**Lifecycle**: `recomputable`（可删除、可重建）

**Storage**: `analytics/insights/<type>/<date>.yaml`

```yaml
# Example: CorrelationInsight
id: ci_20260518_001
type: correlation_insight
computed_at: "2026-05-18T14:00:00+08:00"
correlation_type: event_outcome
event_type: earnings_announcement
outcome_metric: thesis_confirmation_rate
data:
  sample_size: 12
  correlation_strength: 0.65
  confidence_interval: [0.45, 0.80]
  pattern: "earnings_announcement 后 30 天内 thesis 确认率较高"
```

---

### 2.5 Evolution

**定义**: 研究/观点的演化追踪。

| Object | Description | Input | Output |
|--------|-------------|-------|--------|
| ThesisEvolution | Thesis 演化追踪 | Thesis revisions | 演化路径、关键转折点 |
| ResearchEvolution | 研究能力演化 | All objects | 能力提升、模式变化 |

**Lifecycle**: `append-only`（只追加，不修改）

**Storage**: `analytics/evolution/<type>/<thesis_id>.yaml`

```yaml
# Example: ThesisEvolution
id: te_7f8c91
type: thesis_evolution
thesis_id: "ths_7f8c91"
computed_at: "2026-05-18T14:00:00+08:00"
evolution_path:
  - version: 1
    date: "2026-05-01"
    status: "proposed"
    confidence: 0.6
  - version: 2
    date: "2026-05-10"
    status: "partially_confirmed"
    confidence: 0.7
  - version: 3
    date: "2026-05-18"
    status: "confirmed"
    confidence: 0.85
key_turning_points:
  - date: "2026-05-10"
    event: "earnings_report"
    impact: "部分验证 thesis"
```

---

### 2.6 Summary

**定义**: 定期汇总/摘要。

| Object | Description | Input | Output |
|--------|-------------|-------|--------|
| DailySummary | 每日研究摘要 | All daily objects | 关键事件、决策、洞察 |
| WeeklySummary | 每周研究摘要 | Daily summaries | 趋势、模式、建议 |

**Lifecycle**: `snapshot`（定期快照）

**Storage**: `analytics/summaries/<type>/<date>.yaml`

```yaml
# Example: DailySummary
id: ds_20260518
type: daily_summary
date: "2026-05-18"
computed_at: "2026-05-18T20:00:00+08:00"
data:
  decisions_made: 2
  reviews_completed: 3
  alerts_generated: 1
  insights_discovered: 2
  key_themes: ["消费恢复", "白酒板块"]
  recommended_focus: ["600519 新品影响"]
```

---

## 3. Lifecycle Classification

| Lifecycle | Description | Invalidation | Storage |
|-----------|-------------|--------------|---------|
| **append-only** | 只追加，不修改 | 不自动失效 | 按日期归档 |
| **snapshot** | 定期快照，保留历史 | 新快照替代旧快照 | 按日期归档 |
| **ephemeral** | 临时，用户确认后归档 | 用户确认/超时 | 待处理目录 |
| **recomputable** | 可删除、可重建 | Stale 时自动失效 | 临时/缓存目录 |

---

## 4. Naming Convention

```
analytics/
├── reports/           # append-only
│   ├── error_pattern/
│   │   └── 2026-05-18.yaml
│   └── behavioral/
│       └── 2026-05-18.yaml
├── profiles/          # snapshot
│   ├── behavioral/
│   │   └── 600519/
│   │       └── 2026-05-18.yaml
│   └── bias/
│       └── 600519/
│           └── 2026-05-18.yaml
├── alerts/            # ephemeral
│   ├── drift/
│   │   └── 2026-05-18.yaml
│   └── stale/
│       └── 2026-05-18.yaml
├── insights/          # recomputable
│   ├── correlation/
│   │   └── 2026-05-18.yaml
│   └── trend/
│       └── 2026-05-18.yaml
├── evolution/         # append-only
│   ├── thesis/
│   │   └── ths_7f8c91.yaml
│   └── research/
│       └── 2026-05-18.yaml
└── summaries/         # snapshot
    ├── daily/
    │   └── 2026-05-18.yaml
    └── weekly/
        └── 2026-W20.yaml
```

---

## 5. Object Relationships

```
Canonical Objects                 Analytics Objects
─────────────────                 ─────────────────
Decision ───────────────────────▶ BehavioralProfile
       │                              │
       │                              ▼
       └──────────────────────────▶ BiasProfile

Review ─────────────────────────▶ ErrorPatternReport
       │                              │
       │                              ▼
       └──────────────────────────▶ DriftAlert

Thesis ─────────────────────────▶ ThesisEvolution
       │                              │
       │                              ▼
       └──────────────────────────▶ DriftAlert

Event ──────────────────────────▶ CorrelationInsight
       │                              │
       │                              ▼
       └──────────────────────────▶ TrendInsight
```

---

## 6. Governance

| Rule | Description |
|------|-------------|
| **No write-back** | Analytics objects 永远不写入 canonical objects |
| **Source attribution** | AI 生成的 analytics 标记 `source_type: ai_generated` |
| **Deterministic** | 相同输入必须产生相同输出 |
| **Auditable** | 所有 analytics 计算记录到 activity log |
| **User confirmation** | Alert 类型需要用户确认后才归档 |

---

## Related

- Analytics_Runtime_Philosophy.md
- Projection_Rebuild_Contract.md
- ADR-009: Projection Rebuild Rules
- ADR-011: AI Mutation Boundaries
