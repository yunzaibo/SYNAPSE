# System Architect Analysis: P6 Factor Research Engine

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FactorEngine                             │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ FactorRegistry│  │ComputeOrchestr│  │ AuditPipeline         │ │
│  │  (register,   │  │  (batch/rt,  │  │  (IC, RankIC,         │ │
│  │   lookup,     │  │   parallel,  │  │   coverage,           │ │
│  │   lifecycle)  │  │   checkpoint)│  │   leakage detection)  │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘ │
│         │                 │                      │              │
│  ┌──────▼─────────────────▼──────────────────────▼───────────┐  │
│  │                  Factor Computation Layer                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐  │  │
│  │  │ BaseFactor   │  │ FormulaFactor│  │ EventFactor      │  │  │
│  │  │ (ABC)        │  │ (pandas eval)│  │ (event->signal)  │  │  │
│  │  └─────────────┘  └─────────────┘  └──────────────────┘  │  │
│  └────────────────────────┬──────────────────────────────────┘  │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ DataSource   │  │ Event System     │  │ Social Signals   │
│ (P5 adapters)│  │ (P3 detectors)   │  │ (P4 sentiment)   │
└─────────────┘  └──────────────────┘  └──────────────────┘
```

## Component Design

### 1. FactorRegistry -- 复用 DetectorRegistry 模式

现有 `DetectorRegistry` 已验证了注册表模式的有效性。FactorRegistry 应遵循相同约定：

```python
class FactorRegistry:
    def register(self, factor_cls: type[BaseFactor]) -> None: ...
    def unregister(self, factor_id: str) -> type[BaseFactor] | None: ...
    def get_factor(self, factor_id: str) -> type[BaseFactor] | None: ...
    def list_factors(self) -> dict[str, type[BaseFactor]]: ...
    def compute_all(self, data: pd.DataFrame) -> dict[str, pd.Series]: ...
```

**关键决策**: Factor 类通过 `factor_id()` classmethod 自注册，与 `BaseDetector.event_type()` 一致。注册时 MUST 校验 `factor_id` 非空且不重复。

**理由**: 项目已有 DetectorRegistry 先例，保持一致降低认知成本。Registry 同时承担生命周期管理（注册/注销/查找）和批量调度（compute_all）。

### 2. BaseFactor ABC -- 扩展接口

```python
class BaseFactor(ABC):
    @classmethod
    @abstractmethod
    def factor_id(cls) -> str: ...

    @abstractmethod
    def compute(self, data: pd.DataFrame) -> pd.Series: ...

    @abstractmethod
    def required_columns(self) -> list[str]: ...

    def validate_data(self, data: pd.DataFrame) -> bool:
        """Check required columns exist. Subclasses MAY override."""
        return all(c in data.columns for c in self.required_columns())
```

**扩展模型**: 新增因子只需实现 BaseFactor 的三个抽象方法，调用 `registry.register(MyFactor)` 即可。MUST NOT 要求修改 FactorEngine 核心代码。

**三种因子子类**:
- **FormulaFactor**: 现有 `compute_factor` 的封装，声明式公式定义
- **EventFactor**: 从 Event 信号派生数值因子（如事件密度、情绪因子）
- **CompositeFactor**: 组合多个子因子（如加权合成）

### 3. ComputeOrchestrator -- 计算调度

**批量模式** (MUST 支持):
- 输入: tickers 列表 + 时间范围 + FactorSpec 列表
- 从 DataSource 拉取数据，一次性计算所有因子
- 支持断点续算: 每个因子完成后写入中间结果，失败因子跳过不阻塞整体

**实时模式** (SHOULD 支持):
- 监听 StreamBuffer 中的新 MarketData
- 增量计算受影响的因子（非全量重算）
- 延迟目标: 单因子增量计算 < 100ms

**内存管理**:
- 大数据集（>10万行）SHOULD 使用分块计算
- 中间结果 SHOULD 使用 `pd.DataFrame` 而非嵌套 dict，利用 pandas 内存优化
- 计算完成后 SHOULD 及时释放原始数据引用

### 4. AuditPipeline -- 因子质量审计

现有 `audit_factor` 已实现 IC/RankIC 计算。扩展方向:

| 指标 | 当前状态 | P6 增强 |
|------|---------|---------|
| IC / RankIC | 已实现 | 增加滚动窗口 IC（稳定性） |
| Coverage | 已实现 | 增加分行业覆盖率 |
| Leakage Risk | 启发式（>0.95） | 增加时序前后一致性检查 |
| Turnover | 无 | 新增因子换手率 |
| Decay | 无 | 新增 IC 衰减半衰期 |

**审计流水线**: `audit_factor` -> `FactorAuditResult` -> 持久化到 YAML/JSON -> 趋势追踪。

### 5. Integration Points

**DataSource -> FactorEngine**:
- FactorEngine 通过 `DataSource.fetch_batch(tickers)` 获取 MarketData
- MarketData.payload 解析为 DataFrame（需要标准化列名映射）
- 建议新增 `DataSource.to_dataframe(tickers)` 便捷方法或独立的 DataAdapter

**Event -> FactorEngine**:
- EventFactor 从 Event schema 读取 severity, confidence, decay_rate
- 事件密度因子: 滚动窗口内事件计数
- 事件情绪因子: 从 SocialMediaSignal.sentiment_score 聚合

**FactorEngine -> Workflow**:
- 输出 FactorValues（因子值 DataFrame）供 decision_flow 消费
- AuditResult 供 review_flow 做因子质量把关

## Error Handling Strategy

```
FactorComputationError (FACTOR_COMPUTE_FAILED)
├── FactorDataMissingError    -- 数据列缺失或为空
├── FactorFormulaError        -- 公式语法/语义错误
├── FactorTimeoutError        -- 计算超时（大数据集）
└── FactorAuditError          -- 审计数据不足

处理策略:
- 单因子失败 MUST NOT 阻塞其他因子计算
- 失败因子记录错误日志 + FACTOR_COMPUTE_FAILED 异常
- 返回 PartialResult: 成功因子 + 失败因子列表 + 错误详情
- 重试策略: 公式错误不重试，数据缺失等待重试（最多3次）
```

**边界场景**:
- 并发计算: 多个 ComputeOrchestrator 实例操作同一 Registry 时，Registry 的 dict 操作 MUST 使用 threading.Lock 保护
- Rate limiting: DataSource 已有内置限流（EastMoneyAdapter._throttle），FactorEngine SHOULD NOT 再加一层
- 关闭清理: ComputeOrchestrator SHOULD 支持 `cancel()` 方法中断进行中的计算
- 可扩展性: 500+ 因子批量计算时，SHOULD 支持多进程并行（multiprocessing.Pool）

## Observability Requirements

| 指标 | 类型 | 说明 |
|------|------|------|
| `factor_compute_duration_seconds` | Histogram | 单因子计算耗时 |
| `factor_compute_total` | Counter | 计算成功/失败次数 |
| `factor_audit_ic_value` | Gauge | 最新 IC 值 |
| `factor_coverage_ratio` | Gauge | 因子覆盖率 |
| `factor_registry_count` | Gauge | 已注册因子数量 |
| `factor_batch_size` | Gauge | 批量计算的 ticker 数量 |

日志事件: factor_computed, factor_failed, audit_completed, registry_updated。

健康检查: Registry.list_factors() 返回非空 + 最近一次审计 IC 绝对值 > 0.02。

## Data Model (Key Entities)

```
FactorSpec (已有):
  factor_id: str          -- 唯一标识
  formula: str            -- pandas eval 表达式
  frequency: str          -- daily | intraday
  direction: str          -- positive | negative | unknown

FactorValue (新增):
  factor_id: str
  ticker: str
  date: date
  value: float
  version: str

FactorAuditResult (已有，增强):
  factor_id, version, coverage, ic, rank_ic, leakage_risk
  + rolling_ic: list[float]     -- 滚动 IC 序列
  + turnover: float             -- 换手率
  + ic_decay_half_life: float   -- IC 衰减半衰期
```

## Risk Areas

1. **pandas eval 安全性**: 现有 `data.eval(formula)` 存在代码注入风险。SHOULD 限制可调用的函数白名单（只允许 shift, rolling, log, abs 等量化常用函数）。
2. **内存膨胀**: 500 因子 x 5000 ticker x 250 天 = 6.25 亿单元格。SHOULD 使用 float32 替代 float64，或分批计算。
3. **IC 过拟合**: 高 IC 可能是数据泄露。现有泄漏检测（>0.95 阈值）过于粗糙。SHOULD 增加样本外 IC 验证。
4. **DataSource 失败传播**: AkshareAdapter 网络不稳定，批量计算时部分 ticker 数据缺失。SHOULD 实现优雅降级（跳过缺失数据的 ticker，而非整体失败）。

## Key Decisions Summary

| 决策 | 选择 | 理由 |
|------|------|------|
| 架构模式 | Registry + Plugin | 复用 DetectorRegistry 先例，降低认知成本 |
| 计算框架 | pandas eval (保留) + ABC 扩展 | 向后兼容现有 FactorSpec，同时支持复杂因子 |
| 审计增强 | 滚动 IC + 换手率 + 衰减分析 | 仅 IC 不够，需多维度质量评估 |
| 内存策略 | float32 + 分块 + 及时释放 | A-share 全市场数据量大，必须控制内存 |
| 错误隔离 | PartialResult 模式 | 单因子失败不阻塞批量计算 |
