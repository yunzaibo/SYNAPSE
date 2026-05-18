# Research Object Schema (P1)

> 9 个研究对象的完整 YAML schema 定义。
> 单一真相源：本文件。代码中的类型定义以此为准。

## 公共字段

所有研究对象共享以下字段：

```yaml
# --- Identity ---
id: string              # 全局唯一 ID，格式: <prefix>_<短hash>
schema_version: "1.0"   # schema 版本号

# --- Lifecycle ---
status: active | inactive | archived | abandoned | superseded
created_at: datetime    # ISO 8601
updated_at: datetime    # ISO 8601

# --- Source Attribution ---
source_type: ai_generated | human_written | imported | market_data
created_by: ai | human | mixed

# --- Market Context ---
market_context:         # 研究时间 ≠ 市场时间
  research_date: date   # 研究发生日期
  market_date: date     # 对应市场日期（可能不同）
  trading_session: normal | half_day | holiday | suspended
```

## 对象命名规则

| 对象 | 目录 | 命名模式 | 示例 |
|------|------|---------|------|
| Thesis | `thesis/` | `ths_<id>_<slug>/` | `ths_7f8c91_consumer-recovery/` |
| Decision | `decisions/` | `dec_<date>_<action>_<symbol>/` | `dec_20260518_buy_600519/` |
| WatchlistEntry | `watchlists/<date>/` | `wl_<symbol>_<reason>.yaml` | `wl_600519_attention-spike.yaml` |
| Position | `positions/current/` | `pos_<market>_<symbol>.yaml` | `pos_CN_A_600519.yaml` |
| Review | 嵌入 Decision 或独立 | `rev_<decision_id>.yaml` | — |
| Signal | `signals/` | `sig_<id>.yaml` | `sig_a1b2c3.yaml` |
| Risk | `risks/` | `rsk_<id>.yaml` | `rsk_d4e5f6.yaml` |
| Event | `events/` | `evt_<date>_<type>.yaml` | `evt_20260518_earnings.yaml` |
| ResearchTopic | `topics/` | `top_<id>_<slug>.yaml` | `top_g7h8i9_consume.yaml` |

**5 Naming Principles**:
1. Human-readable ≠ Identity
2. IDs are immutable, aliases are mutable
3. File paths are for navigation, metadata is for semantics
4. Ticker is not a stable identity
5. Revisions are append-only

---

## Layer 1: Functionally Complete (P1)

### 1. WatchlistEntry

每日研究队列项。一个 WatchlistEntry = "今天值得研究的一件事"。

```yaml
# watchlists/2026-05-18/wl_600519_attention-spike.yaml
id: wl_a1b2c3
schema_version: "1.0"

# --- Core ---
ticker: "600519"
symbol: "贵州茅台"
market: "CN_A"
headline: "茅台新品发布引发白酒板块关注"
why_now: "社交讨论度过去24小时上升240%，白酒板块出现联动放量"

# --- Signals ---
signals:
  - type: attention_spike
    strength: weak | medium | strong
    description: "社交讨论度上升240%"
  - type: sector_resonance
    strength: medium
    description: "白酒板块联动放量"
  - type: historical_pattern_match
    strength: weak
    description: "历史上新品发布后30天关注度变化模式"

# --- Research Angle ---
research_angle: "观察新品是否影响高端白酒估值逻辑"
action: "值得关注"  # 只输出"值得关注"，不输出"建议买入"

# --- Risk Hint ---
risk_hint: "高波动 / 事件驱动可能快速衰减"

# --- Trigger Type ---
trigger_type: event_attention | factor_signal | portfolio_review | sector_rotation

# --- Links ---
linked_thesis_id: null | "ths_xxx"
linked_event_id: null | "evt_xxx"

# --- Lifecycle ---
status: active
created_at: "2026-05-18T08:00:00+08:00"
updated_at: "2026-05-18T08:00:00+08:00"

# --- Source ---
source_type: ai_generated
created_by: ai

# --- Market Context ---
market_context:
  research_date: "2026-05-18"
  market_date: "2026-05-18"
  trading_session: normal
```

**字段说明**:
- `signals[]`: P1 记录信号，不独立追踪衰减（P2 做）
- `trigger_type`: 4 种触发类型（event/factor/portfolio/sector）
- `action`: 固定输出"值得关注"，不做买入建议

---

### 2. Thesis

研究观点/假设。核心对象，所有研究通过 Thesis 连接。

```yaml
# thesis/ths_7f8c91_consumer-recovery/meta.yaml
id: ths_7f8c91
slug: "consumer-recovery"
schema_version: "1.0"

# --- Core ---
title: "中国消费恢复 Thesis"
summary: "消费恢复预期 + 新品发布可能带动高端白酒关注度提升"
thesis_statement: "中国消费市场在2026年Q2出现结构性恢复信号，高端消费品将首先受益"

# --- Related Securities ---
related_securities:
  - ticker: "600519"
    symbol: "贵州茅台"
    market: "CN_A"
    relevance: primary  # primary | secondary | contextual
  - ticker: "000858"
    symbol: "五粮液"
    market: "CN_A"
    relevance: secondary

# --- Research Topic ---
topic_id: "top_g7h8i9_consume"

# --- Evidence ---
evidence:
  - type: market_data
    description: "白酒板块过去20日涨幅12%"
    source_type: market_data
    linked_data_id: null
  - type: event
    description: "茅台新品发布会"
    source_type: imported
    linked_event_id: "evt_xxx"

# --- Confidence ---
confidence: low | medium | high  # 不用百分比，避免 AI 权威感

# --- Thesis Evolution (append-only) ---
parent_thesis_id: null  # 初始版本为 null
revision: 1
previous_revision: null  # 初始版本为 null

# --- Lifecycle ---
status: active
created_at: "2026-05-18T10:00:00+08:00"
updated_at: "2026-05-18T10:00:00+08:00"

# --- Source ---
source_type: human_written
created_by: human

# --- Market Context ---
market_context:
  research_date: "2026-05-18"
  market_date: "2026-05-18"
  trading_session: normal
```

**Thesis Evolution 规则**:
- 永远不覆盖，总是创建新 revision
- 新版本：`parent_thesis_id` 指向上一版本，`revision` +1
- 历史版本保存在 `thesis/<id>/rev-001.md`, `rev-002.md`...
- `meta.yaml` 始终指向最新版本

---

### 3. Decision

买入/卖出决策。天然 security-bound。

```yaml
# decisions/dec_20260518_buy_600519/meta.yaml
id: dec_b4c5d6
schema_version: "1.0"

# --- Core ---
ticker: "600519"
symbol: "贵州茅台"
market: "CN_A"
decision_type: buy | sell  # P1 只有 buy/sell，不做 hold

# --- Thesis ---
thesis: "消费恢复预期 + 新品发布可能带动高端白酒关注度提升"
linked_thesis_id: "ths_7f8c91"

# --- Risk ---
key_risk: "白酒板块整体估值偏高，消费恢复速度可能低于预期"

# --- Time Horizon ---
time_horizon: short_term | medium_term | long_term

# --- Attention Origin ---
attention_origin: event_attention | factor_signal | portfolio_review

# --- Position Link ---
linked_position_id: "pos_CN_A_600519"

# --- Signals ---
signals:
  - linked_signal_id: "sig_xxx"
    role: primary | supporting

# --- Lifecycle ---
status: active
created_at: "2026-05-18T14:00:00+08:00"
updated_at: "2026-05-18T14:00:00+08:00"

# --- Source ---
source_type: human_written
created_by: human

# --- Market Context ---
market_context:
  research_date: "2026-05-18"
  market_date: "2026-05-18"
  trading_session: normal
```

**字段说明**:
- `decision_type`: P1 只有 buy/sell，不做 hold
- `thesis`: 冻结当时的认知状态（用 thesis 不用 reason）
- `key_risk`: "这个 thesis 最可能错在哪里"
- `attention_origin`: 决策的触发来源

---

### 4. Review

Decision 事后回顾。optional，系统建议但不强制。

```yaml
# decisions/dec_20260518_buy_600519/review.yaml（嵌入 Decision）
# 或独立文件
id: rev_e7f8g9
schema_version: "1.0"

# --- Link ---
linked_decision_id: "dec_b4c5d6"
linked_thesis_id: "ths_7f8c91"

# --- Outcome ---
review_outcome: thesis_confirmed | partially_confirmed | thesis_invalidated
# 用 outcome: thesis_confirmed 不用 profit/loss → 盈亏 ≠ thesis 正确

# --- Note ---
review_note: "新品确实带动了短期关注度，但消费恢复速度低于预期"

# --- Signal Evaluation ---
signal_evaluations:
  - linked_signal_id: "sig_xxx"
    was_accurate: true
    note: "注意力信号准确，但衰减比预期快"

# --- Risk Evaluation ---
risk_evaluations:
  - description: "估值偏高"
    materialized: false
    note: "估值维持高位，风险未兑现"

# --- Lifecycle ---
status: active
created_at: "2026-08-18T10:00:00+08:00"
updated_at: "2026-08-18T10:00:00+08:00"

# --- Source ---
source_type: human_written
created_by: human
```

**Review 原则**:
- Review optional → 降低门槛，"持续记录"比"记录专业"更重要
- `review_outcome` 评估 thesis 是否正确，不评估盈亏
- `signal_evaluations` 和 `risk_evaluations` 评估预测准确性

---

### 5. Position

当前持仓。研究状态优先，不是红涨绿跌。

```yaml
# positions/current/pos_CN_A_600519.yaml
id: pos_h1i2j3
schema_version: "1.0"

# --- Core ---
ticker: "600519"
symbol: "贵州茅台"
market: "CN_A"

# --- Thesis ---
linked_thesis_id: "ths_7f8c91"
thesis_at_entry: "消费恢复预期 + 新品发布可能带动高端白酒关注度提升"

# --- Position State ---
entry_date: "2026-05-18"
entry_price: 1800.00
current_shares: 100

# --- Research State (非 P&L 优先) ---
research_state:
  thesis_status: active | weakened | invalidated
  attention_state: stable | rising | fading
  last_review_date: "2026-06-18"

# --- Linked Records ---
linked_decision_id: "dec_b4c5d6"
linked_watchlist_ids:
  - "wl_a1b2c3"

# --- Lifecycle ---
status: active
created_at: "2026-05-18T14:30:00+08:00"
updated_at: "2026-05-18T14:30:00+08:00"

# --- Source ---
source_type: human_written
created_by: human

# --- Market Context ---
market_context:
  research_date: "2026-05-18"
  market_date: "2026-05-18"
  trading_session: normal
```

**Position 原则**:
- `research_state` 优先于 P&L 数据
- `thesis_at_entry`: 冻结建仓时的认知
- `thesis_status`: thesis 是否仍然成立（不是盈亏）

---

## Layer 2: Schema Defined, Simplified Entry (P1)

### 6. Signal

独立信号记录。P1 只在 Watchlist/Decision 中记录，不独立追踪衰减。

```yaml
# signals/sig_a1b2c3.yaml
id: sig_a1b2c3
schema_version: "1.0"

# --- Core ---
signal_type: attention_spike | sector_resonance | historical_pattern_match | factor_anomaly | earnings_surprise | policy_impact
strength: weak | medium | strong
description: "社交讨论度过去24小时上升240%"

# --- Related ---
related_tickers:
  - "600519"
  - "000858"
linked_event_id: null | "evt_xxx"

# --- Decay (P2 做，P1 只记录不追踪) ---
decay_tracking: false

# --- Lifecycle ---
status: active
created_at: "2026-05-18T08:00:00+08:00"
updated_at: "2026-05-18T08:00:00+08:00"

# --- Source ---
source_type: ai_generated
created_by: ai
```

### 7. Risk

独立风险假设。P1 只在 Decision 的 key_risk 中记录，不独立追踪变化。

```yaml
# risks/rsk_d4e5f6.yaml
id: rsk_d4e5f6
schema_version: "1.0"

# --- Core ---
risk_type: valuation | liquidity | regulatory | event_decay | macro | sector
description: "白酒板块整体估值偏高，消费恢复速度可能低于预期"
severity: low | medium | high

# --- Related ---
related_tickers:
  - "600519"
linked_decision_id: "dec_b4c5d6"

# --- Tracking (P2 做，P1 只记录不追踪) ---
materialization_tracking: false

# --- Lifecycle ---
status: active
created_at: "2026-05-18T14:00:00+08:00"
updated_at: "2026-05-18T14:00:00+08:00"

# --- Source ---
source_type: human_written
created_by: human
```

### 8. Event

关注的市场事件。P1 只在 Watchlist 的 why_now 中记录，不独立建模。

```yaml
# events/evt_20260518_earnings.yaml
id: evt_k1l2m3
schema_version: "1.0"

# --- Core ---
event_type: earnings | policy | product_launch | management_change | sector_rotation | macro_data
title: "茅台新品发布会"
description: "贵州茅台发布新品，引发白酒板块关注"
event_date: "2026-05-18"

# --- Related ---
related_tickers:
  - "600519"
  - "000858"

# --- Impact Assessment (P1 简化) ---
impact_level: low | medium | high | unknown

# --- Lifecycle ---
status: active
created_at: "2026-05-18T09:00:00+08:00"
updated_at: "2026-05-18T09:00:00+08:00"

# --- Source ---
source_type: imported
created_by: ai
```

### 9. ResearchTopic

聚类标签。P1 用 tags 字段代替，不独立管理。

```yaml
# topics/top_g7h8i9_consume.yaml
id: top_g7h8i9
slug: "consume"
schema_version: "1.0"

# --- Core ---
name: "中国消费"
description: "中国消费市场恢复、消费升级、消费降级相关研究"
parent_topic_id: null  # 支持 topic 层级

# --- Related Theses ---
thesis_ids:
  - "ths_7f8c91"

# --- Lifecycle ---
status: active
created_at: "2026-05-18T10:00:00+08:00"
updated_at: "2026-05-18T10:00:00+08:00"
```

---

## 关系图

```txt
WatchlistEntry ──triggers──> Decision
Decision       ──embodies──> Thesis
Decision       ──has many──> Signal
Decision       ──has many──> Risk
Review         ──validates──> Thesis
Review         ──evaluates──> Signal
Review         ──evaluates──> Risk
Position       ──maintains──> Thesis
Thesis         ──belongs to──> ResearchTopic
Event          ──generates──> Signal
Event          ──triggers──> WatchlistEntry
```

**关系通过 `linked_*_id` 字段在 YAML 里自然表达，不需要图数据库。**

---

## Schema Validation

### TOML (Global Config)

```rust
// serde + strongly typed structs
#[derive(Deserialize)]
struct GlobalConfig {
    sidecar: SidecarConfig,
    logging: LoggingConfig,
    workspace: WorkspaceDefaultConfig,
}
```

### YAML (Workspace + Research Objects)

```yaml
# 每个 schema 必须声明 schema_version
schema_version: "1.0"

# JSON Schema 用于验证（代码中加载时校验）
```

**约束**: Workspace YAML 禁止 execution graph / runtime orchestration / deep inheritance。

---

## Refinement 1: Canonical Storage Rules

明确区分 immutable 文件和 mutable projection：

### Immutable（不可变，append-only）

```txt
rev-001.md              ← Thesis revision
rev-002.md              ← Thesis revision
activity.jsonl          ← 操作日志
events/*.yaml           ← Event 记录
decisions/*/meta.yaml   ← Decision 快照
```

### Mutable Projection（可变投影，可覆盖）

```txt
meta.yaml               ← Thesis 当前状态（指向最新 revision）
workspace.db            ← SQLite 索引（可从 artifacts 重建）
positions/current/*.yaml ← Position 当前状态（projection）
watchlists/<date>/*.yaml ← 当日 watchlist（可更新）
```

**原则**: append-only 哲学必须贯穿文件系统。rev 文件永远不覆盖，meta.yaml 是可变投影。

---

## Refinement 2: Projection Philosophy

明确区分 Canonical Artifact 和 Projection：

### Canonical Artifacts（真相源，不可变）

| Object | 为什么是 Canonical |
|--------|-------------------|
| Thesis | 研究观点的 truth lineage，append-only revision chain |
| Decision | 决策快照，冻结当时认知状态 |
| Review | 评估记录，不可篡改 |
| Event | 市场事件记录，事实性数据 |

### Projections（从 canonical 计算，可变）

| Object | 为什么是 Projection |
|--------|-------------------|
| Position | 从 Decision + 市场数据计算，不是独立真相 |
| Watchlist Queue | 从 Signal + Event + Portfolio 计算，每日重建 |
| Research Timeline | 从所有 canonical artifacts 渲染的视图 |

**原则**: 不允许双写。Position 不手工更新 — 从 Decision replay 计算。

---

## Refinement 3: Object Ownership

明确每个字段的"owner"，防止状态漂移：

### Thesis owns

```txt
truth lineage        ← thesis 是否成立
revision chain       ← append-only 历史
confidence level     ← 研究置信度
related securities   ← 关联标的
```

### Review owns

```txt
evaluation           ← thesis 是否被验证
evidence shift       ← 证据是否变化
signal accuracy      ← 信号预测准确性
risk materialization ← 风险是否兑现
```

### Position does NOT own

```txt
thesis_status        ← 引用 Thesis 的当前状态，不自己维护
research_state       ← 从 Thesis + Review projection 计算
```

**原则**: Position 只"引用当前状态 projection"，不拥有 thesis truth。防止 Thesis/Position/Review 三方状态漂移。

---

## Refinement 4: Schema Evolution Strategy

### P1 策略: Weak Schema + Lazy Upcast

```txt
读取时: schema 1.0 → runtime model 1.2 (自动 upcast)
写入时: schema 1.2 → 文件 (始终最新 schema)
不要: 全局 migration / rewrite 全仓库
```

### Upcast 规则

```yaml
# 例: confidence 拆分
# schema 1.0
confidence: medium

# schema 1.2
confidence:
  overall: medium
  evidence: high
  market: low

# Upcast: 1.0 → 1.2
# runtime 自动将 confidence: medium 转为 confidence.overall: medium
```

### Migration Philosophy

- **不做**: 全局 migration script
- **做**: runtime read-time upcast + write-time latest schema
- **原因**: Research Workspace 必须保持脆弱性低，用户可直接操作文件

---

## Execution Wave Structure（GPT 建议）

P1 Execution 按以下 wave 顺序：

```txt
Wave 1: Canonical Storage Layer
        ↓
Wave 2: Object Loader + Validation
        ↓
Wave 3: Projection Engine
        ↓
Wave 4: Workspace Runtime
        ↓
Wave 5: Watchlist / Decision Flow
```

**关键原则**: 不要 GUI-first。核心是 Research Object Runtime，不是 React 页面。

---

## Refinement 5: Security Identity ADR (P1)

### 问题

当前 schema 用 `ticker: "600519"` 做 identity，但 ticker 不稳定（改名/ST/退市/多市场）。

### 方案: Composite Security Identity

```yaml
# 完整身份
security_id: "cn.sse.600519"   # 全局唯一，稳定
ticker: "600519"               # 人类可读，可变
symbol: "贵州茅台"              # 人类可读，可变
exchange: "SH"                 # 交易所代码
market: "CN_A"                 # 市场分类
```

### 格式规范

```
{market}.{exchange}.{ticker}

示例:
  cn.sse.600519    ← 贵州茅台（上海）
  cn.szse.000858   ← 五粮液（深圳）
  hk.hkex.0700     ← 腾讯（港股）(P2+)
  us.nasdaq.aapl   ← 苹果（美股）(P2+)
```

### 使用规则

- **所有 `linked_*_id` 引用**: 用 `security_id`，不用 `ticker`
- **文件命名**: 可用 ticker（人类可读），但 YAML 内必须有 `security_id`
- **Migration**: 未来 ticker 变更时，`security_id` 不变，只更新 `ticker` 字段

---

## Refinement 6: Temporal Semantics (P1)

### 问题

当前 `market_context` 只有 research_date / market_date / trading_session，不够 runtime-grade。

### 完整时间语义

```yaml
# --- Core Timestamps ---
created_at: datetime          # 记录创建时间（processing time）

# --- Event Time ---
event_time: datetime          # 事件实际发生时间
event_timezone: "Asia/Shanghai"

# --- Market Effective Time ---
market_date: date             # 市场生效日期
market_session: normal | half_day | holiday | suspended

# --- Availability ---
available_at: datetime        # 数据可用时间（盘后数据可能延迟）
as_of_date: date              # 数据截至日期

# --- Observation ---
observed_at: datetime         # 系统观察到的时间
ingested_at: datetime         # 数据入库时间
```

### 三种时间的区分

| 时间类型 | 含义 | 示例 |
|----------|------|------|
| event time | 事件实际发生 | 财报发布: 2026-05-18 23:00 |
| processing time | 系统处理时间 | 2026-05-19 08:00 (次日早上) |
| market effective time | 市场生效时间 | 2026-05-19 (次日开盘) |

### 使用规则

- 财报 23:00 发布 → event_time = 当天, market_date = 次日
- 所有时间-aware 对象必须声明 `event_timezone`
- Review 的 `reviewed_at` 用 processing time

---

## Refinement 7: Activity Taxonomy ADR (P1)

### 问题

`activity.jsonl` 谁写、写什么、不写什么，需要冻结。

### Activity Types

```txt
# Research Activities（必须记录）
thesis.created
thesis.revised
decision.recorded
review.completed
watchlist.generated
position.opened
position.closed

# Runtime Activities（可选记录）
projection.rebuilt
workspace.indexed
sidecar.restarted

# Explicitly Forbidden（禁止记录）
token.stream              ← LLM 原始输出
llm.raw.reasoning         ← AI 推理过程
debug.spam                ← 调试日志
file.watcher.event        ← 文件系统事件
```

### Activity Entry Format

```jsonl
{"ts":"2026-05-18T10:00:00+08:00","type":"thesis.created","obj_id":"ths_7f8c91","actor":"human","summary":"创建消费恢复 thesis"}
{"ts":"2026-05-18T14:00:00+08:00","type":"decision.recorded","obj_id":"dec_b4c5d6","actor":"human","summary":"记录买入 600519 决策"}
```

### 写入者

- **Human actions**: 由 UI/CLI 直接写入
- **AI suggestions**: AI 生成建议，human 确认后写入（AI 不直接写 activity）
- **Runtime events**: 由 Core Runtime 写入（仅 projection.rebuilt / workspace.indexed 等）

---

## Refinement 8: Projection Rebuild Rules (P1)

### 问题

Projection 什么时候 rebuild？需要明确语义。

### P1 Projection Rules

| Projection | Rebuild Trigger | Strategy |
|-----------|----------------|----------|
| Position | Decision/Review change | Event-triggered rebuild |
| Watchlist | 每日定时 | Daily regeneration |
| Timeline | 所有 canonical artifact 变化 | Append-only rendering |
| SQLite index | 文件变化 | FileWatcher + lazy rebuild |

### Position Rebuild Logic

```txt
输入: Decision + Position 状态
逻辑: Decision.recorded → 创建 Position / 更新 Position
      Decision.sold → 关闭 Position
      Review.completed → 更新 Position.research_state
输出: positions/current/<security_id>.yaml
```

### Watchlist Regeneration Logic

```txt
输入: Signal + Event + Portfolio + Market Data
逻辑: 每日早上重新生成（不增量更新）
输出: watchlists/<date>/wl_*.yaml
```

### 约束

- Projection 永远从 canonical artifacts 计算，不手工编辑
- Projection 可以被删除和重建（它是 cache，不是 truth）
- 如果 projection 与 canonical 不一致，以 canonical 为准

---

## Refinement 9: AI Mutation Boundaries (P1)

### 问题

AI 可以修改什么？需要明确边界，防止 "AI silently mutates truth"。

### AI Allowed（可生成/建议）

```txt
generate suggestion          ← 生成研究建议
draft thesis                 ← 起草 thesis（human 确认后写入）
propose review               ← 建议 review（human 确认后写入）
generate watchlist           ← 生成 watchlist
suggest signal               ← 建议信号
```

### AI Forbidden（禁止直接修改）

```txt
overwrite canonical artifact ← 禁止覆盖 Thesis/Decision/Review/Event
auto-confirm thesis          ← 禁止自动确认 thesis
auto-close position          ← 禁止自动关闭 position
rewrite historical review    ← 禁止重写历史 review
modify activity log          ← 禁止修改 activity.jsonl
```

### AI Workflow

```txt
AI 生成 draft → human 审阅 → human 确认 → 写入 canonical artifact
                ↓
        human 拒绝 → 丢弃 draft，不写入任何东西
```

### 原则

- AI 是 research assistant，不是 research authority
- 所有 AI 生成内容必须有 `source_type: ai_generated`
- Human-in-the-loop 是必须的（P1 阶段）
- Anti-AI-authority: 不输出"建议买入"，输出"值得关注"

---

## P1 Final ADR Freeze Summary

进入 maestro-plan 前，以下 5 个 ADR 必须冻结：

| # | ADR | 状态 |
|---|-----|------|
| ADR-007 | Security Identity (Composite Security Identity) | ✅ 已定义 |
| ADR-008 | Temporal Semantics (event/processing/market time) | ✅ 已定义 |
| ADR-009 | Projection Rebuild Rules (event-triggered/daily/append-only) | ✅ 已定义 |
| ADR-010 | Activity Taxonomy (what to log, what not to log) | ✅ 已定义 |
| ADR-011 | AI Mutation Boundaries (allowed vs forbidden) | ✅ 已定义 |
