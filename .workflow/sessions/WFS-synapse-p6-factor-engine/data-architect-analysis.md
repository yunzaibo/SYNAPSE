# P6 Factor Research Engine — Data Architect Analysis

**Session**: WFS-synapse-p6-factor-engine
**Date**: 2026-05-19
**Perspective**: Data Architecture

---

## 1. 现状评估

### 1.1 已有代码

`synapse/factor/` 目前包含三个文件：

| 模块 | 现状 | 问题 |
|------|------|------|
| `spec.py` — FactorSpec | 10 字段 dataclass，YAML 序列化 | **未继承 BaseSchema**，缺少 id/status/schema_version/market_context |
| `compute.py` — compute_factor | pandas eval + groupby ticker | 无 DataFrame schema 校验，无 point-in-time 保护 |
| `audit.py` — FactorAuditResult | IC/RankIC/coverage | 未继承 BaseSchema，无 to_dict/from_dict |

### 1.2 关键缺失

FactorSpec 与系统其他 9 个核心对象（Event, Thesis, Decision, Review, Position 等）**完全脱节**：
- 没有 `BaseSchema` 的 `id`, `schema_version`, `status`, `created_at`, `market_context` 字段
- 没有 `to_dict()` / `from_dict()` 模式，无法与 YAML 存储层统一
- 没有 `source_type` / `created_by` 追溯因子来源（人工 vs AI 生成）

---

## 2. 数据模型设计

### 2.1 FactorSpec（因子定义）— 重构

```python
@dataclass
class FactorSpec(BaseSchema):
    """Factor definition — inherits all BaseSchema fields."""

    schema_version: str = "1.0"

    # --- Core ---
    slug: str = ""                    # unique key, e.g. "momentum_20d"
    title: str = ""
    description: str = ""
    domain: str = "cross_sectional_equity"  # ADR-002
    formula: str = ""                 # pandas eval expression
    inputs: list[str] = field(default_factory=list)  # required columns
    direction: str = "unknown"        # positive | negative | unknown
    frequency: str = "daily"          # daily | intraday
    universe: str = ""                # stock pool filter

    # --- Event Integration ---
    event_signal_types: list[str] = field(default_factory=list)  # EventType values this factor consumes
    event_weight: float = 0.0         # how much event signals influence this factor

    # --- Audit Reference ---
    last_audit_id: Optional[str] = None
    audit_status: str = "unaudited"   # unaudited | passed | failed | warning
```

**设计决策**：
- 继承 `BaseSchema` 获得 `id`（UUID）、`status`（ObjectStatus）、`market_context`、`source_type`（SourceType.MARKET_DATA）、`created_by`（CreatorType.AI/HUMAN/MIXED）
- `slug` 作为业务主键（human-readable），`id` 作为系统主键（UUID）
- `formula` 字段存储 pandas eval 表达式，`inputs` 声明依赖列，引擎可在计算前校验
- `event_signal_types` 建立与 P3/P4 event 系统的桥接

### 2.2 FactorResult（因子计算结果）— 新增

```python
@dataclass
class FactorResult(BaseSchema):
    """Computed factor values for a specific factor + date range."""

    schema_version: str = "1.0"

    # --- Linkage ---
    factor_id: str = ""               # references FactorSpec.id
    factor_slug: str = ""             # denormalized for readability
    factor_version: str = "1.0"       # snapshot of spec version at compute time

    # --- Compute Metadata ---
    compute_date: date = field(default_factory=date.today)
    data_start_date: Optional[date] = None
    data_end_date: Optional[date] = None
    ticker_count: int = 0
    value_count: int = 0              # non-NaN rows
    missing_rate: float = 0.0

    # --- Values (not stored in dataclass, stored separately) ---
    # values_path: str = ""           # path to Parquet file on disk
```

**设计决策**：
- 因子值本身存储为 Parquet 文件（DataFrame），FactorResult 只存元数据和文件路径
- 原因：因子值是 ticker x date 的矩阵，可能有数万行，不适合序列化到 YAML
- `factor_version` 记录计算时使用的 spec 版本，确保可复现

### 2.3 FactorAuditReport（审计报告）— 重构

```python
@dataclass
class FactorAuditReport(BaseSchema):
    """Audit report for a factor computation run."""

    schema_version: str = "1.0"

    # --- Linkage ---
    factor_id: str = ""
    factor_slug: str = ""
    factor_version: str = ""
    result_id: Optional[str] = None   # links to FactorResult.id

    # --- Quality Metrics ---
    coverage: float = 0.0             # % non-NaN
    missing_rate: float = 0.0
    ic: float = 0.0                   # Pearson IC
    rank_ic: float = 0.0              # Spearman RankIC
    ic_ir: float = 0.0                # IC Information Ratio (IC mean / IC std)
    turnover: float = 0.0             # factor turnover rate

    # --- Risk Assessment ---
    leakage_risk: str = "unknown"     # low | medium | high | unknown
    anomaly_flags: list[str] = field(default_factory=list)

    # --- Audit Trail ---
    forward_return_period: int = 5    # days
    universe_size: int = 0
    date_range: Optional[tuple[date, date]] = None
```

### 2.4 实体关系

```
FactorSpec (1) ──────compute──────> (N) FactorResult
    │                                    │
    │                              audit  │
    │                                    v
    └──────────────────────────(1) FactorAuditReport

FactorSpec ──event_signal_types──> EventType (P3/P4)
FactorResult ──factor_id──> FactorSpec.id
FactorAuditReport ──factor_id + result_id──> FactorSpec.id + FactorResult.id
```

---

## 3. 数据流设计

```
┌─────────────────────────────────────────────────────────┐
│                    Data Flow Pipeline                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  DataSource ABC ──> MarketData[] ──> DataFrame           │
│  (P5 adapters)        │               (raw)              │
│                       │                                   │
│  SocialMediaSignal ──>│──> Event Pipeline (P3/P4)        │
│  (P4 social.py)       │        │                         │
│                       │        v                         │
│                       │   Event[].impact_score            │
│                       │   Event[].decay_factor            │
│                       │        │                         │
│                       v        v                         │
│  ┌──────────────────────────────────────┐                │
│  │         FactorEngine.compute()        │                │
│  │                                       │                │
│  │  1. Load DataFrame (CSV/Parquet)      │                │
│  │  2. Enrich with Event signals         │                │
│  │     (event_impact_score column)       │                │
│  │  3. Apply FactorSpec.formula          │                │
│  │     via pandas eval (groupby ticker)  │                │
│  │  4. Output FactorResult               │                │
│  │     (metadata in YAML, values in      │                │
│  │      Parquet)                         │                │
│  └───────────────────────┬──────────────┘                │
│                          │                                │
│                          v                                │
│  ┌──────────────────────────────────────┐                │
│  │        FactorEngine.audit()           │                │
│  │                                       │                │
│  │  1. Compute coverage, IC, RankIC     │                │
│  │  2. Leakage detection                │                │
│  │  3. Generate FactorAuditReport        │                │
│  │     (saved to YAML)                   │                │
│  └──────────────────────────────────────┘                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 3.1 Event Signal -> Factor Input 桥接

Event 信号转化为因子输入的具体模式：

| Event Type | 转化方式 | Factor Input |
|-----------|---------|--------------|
| SOCIAL_SENTIMENT | 聚合 ticker 的 sentiment_score 均值 | `event_sentiment_score` 列 |
| CAPITAL_FLOW | 聚合净流入金额 | `event_capital_flow` 列 |
| POLICY_CHANGE | 二值化（受影响/不受影响） | `event_policy_impact` 列 |
| SECTOR_ROTATION | sector 级别强度 | `event_sector_strength` 列 |

实现方式：在 `compute_factor()` 前，`FactorEngine` 应提供 `enrich_with_events(df, events, date_range)` 方法，将 Event 列表 pivot 为 DataFrame 的附加列。

---

## 4. 存储策略

### 4.1 分层存储

| 层级 | 格式 | 用途 | 路径模式 |
|------|------|------|---------|
| 定义层 | YAML | FactorSpec, FactorAuditReport | `artifacts/factors/{slug}/spec.yaml` |
| 计算层 | Parquet | FactorResult 值 | `artifacts/factors/{slug}/values/v{version}.parquet` |
| 审计层 | YAML | FactorAuditReport | `artifacts/factors/{slug}/audit/v{version}.yaml` |
| 缓存层 | 内存 DataFrame | 运行时计算 | 不持久化 |

### 4.2 为什么不全用 Parquet

- FactorSpec 字段少（< 15），YAML 可读性好，适合 diff 和人工审查
- 因子值是 ticker x date 矩阵，行数 = tickers x trading_days，Parquet 列式存储更高效
- FactorAuditReport 包含自由文本 notes，YAML 更合适

### 4.3 为什么不全用 YAML

- 因子值可能有 5000 tickers x 250 days = 1.25M 行，YAML 序列化慢且文件大
- Parquet 天然支持列式切片（只读单个因子的值）

---

## 5. 时间序列处理

### 5.1 Point-in-Time 正确性

当前 `compute_factor()` 的 `_compute_timeseries_formula()` 按 ticker groupby + sort by date 处理 shift/rolling，但**没有 point-in-time 保护**。

**必须增加的约束**：
- DataFrame 的 date 列 MUST NOT 包含未来数据（相对于计算日期）
- `enrich_with_events()` 中的 Event 信号 MUST 使用 `event_date <= compute_date` 过滤
- rolling window 的 lookback MUST 基于实际交易日（非自然日）

### 5.2 Lookback Window 设计

```python
@dataclass
class FactorSpec(BaseSchema):
    # ... existing fields ...
    lookback_days: int = 20           # rolling window in trading days
    min_data_points: int = 15         # minimum required data points
```

- `compute_factor()` MUST 校验每个 ticker group 的数据点 >= `min_data_points`
- 数据不足的 ticker SHOULD 返回 NaN（而非抛异常）

---

## 6. Schema Evolution 策略

### 6.1 复用 Weak Schema + Lazy Upcast

现有系统（ADR-005）的策略完全适用于 FactorSpec：
- 读取时：旧版本 dict 通过 `from_dict()` 的默认值自动 upcast
- 写入时：始终写最新 schema_version
- 无全局 migration 脚本

### 6.2 FactorSpec 版本管理

当前 `FactorSpec.next_version()` 只做 minor version +1。建议扩展：

```python
def next_version(self, bump: str = "minor") -> "FactorSpec":
    """Create next version. bump='major'|'minor'|'patch'."""
    major, minor, patch = self.version.split(".")
    if bump == "major":
        return self._with_version(f"{int(major)+1}.0.0")
    elif bump == "minor":
        return self._with_version(f"{major}.{int(minor)+1}.0")
    else:
        return self._with_version(f"{major}.{minor}.{int(patch)+1}")
```

**何时 bump major**：formula 语义变更（如从 20 日动量改为 60 日动量）
**何时 bump minor**：inputs 列新增（如增加 event_signal 列）
**何时 bump patch**：描述/注释更新

---

## 7. 集成模式

### 7.1 与 DataSource (P5) 的关系

```
DataSource.fetch(tickers) -> MarketData[] -> DataFrame
                                                    |
                                              FactorEngine.compute()
```

DataSource 是数据供应层，FactorEngine 是计算层。两者通过 DataFrame 解耦。FactorEngine SHOULD NOT 直接调用 DataSource。

### 7.2 与 Event System (P3/P4) 的关系

Event 信号通过 `enrich_with_events()` 注入因子计算。FactorSpec 的 `event_signal_types` 字段声明该因子消费哪些 EventType。这保持了事件系统和因子系统的松耦合。

### 7.3 与 Thesis/Decision 的关系

FactorAuditReport 的 `leakage_risk` 字段 SHOULD 被 Decision schema 引用。当 `leakage_risk == "high"` 时，Decision SHOULD NOT 依赖该因子值。

---

## 8. 关键建议

1. **FactorSpec MUST 继承 BaseSchema** — 这是最紧迫的改造，否则与系统其余部分脱节
2. **因子值 MUST 持久化为 Parquet** — YAML 无法承载百万级行数据
3. **enrich_with_events() MUST 实现** — P6 的核心差异化在于 event-augmented factor
4. **point-in-time 校验 MUST 加入 compute_factor()** — 防止 look-ahead bias
5. **FactorAuditReport MUST 有 to_dict/from_dict** — 与现有 schema 模式统一
