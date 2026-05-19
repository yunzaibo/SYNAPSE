# F-010: FactorSpec & Registry

**Priority**: P0
**Status**: Draft
**Session**: WFS-synapse-p6-factor-engine

---

## Summary

因子元数据模型 + 注册机制。所有因子必须通过 FactorSpec 定义，通过 FactorRegistry 注册。

## Motivation

P6 因子引擎需要统一的因子定义和管理方式。参考 P3 DetectorRegistry 的成功模式。

## Design

### FactorSpec Dataclass

```python
@dataclass
class FactorSpec:
    factor_id: str              # 唯一标识 (e.g. "momentum_6m_1m")
    name: str                   # 人类可读名称
    description: str            # 因子描述
    category: str               # "momentum" | "value" | "quality" | "volatility" | "liquidity" | "event"
    inputs: list[str]           # 依赖的数据字段 (e.g. ["close", "volume"])
    lookback_days: int          # 回看窗口天数
    data_source: str            # 数据来源 ("eastmoney" | "akshare" | "event")
    publication_lag: int        # 数据发布延迟天数 (防止 look-ahead bias)
    compute_fn: Callable        # 计算函数
    version: str = "1.0.0"      # semver 版本
```

### FactorRegistry

```python
class FactorRegistry:
    def register(self, factor_cls: type[BaseFactor]) -> None: ...
    def unregister(self, factor_id: str) -> type[BaseFactor] | None: ...
    def get_factor(self, factor_id: str) -> type[BaseFactor] | None: ...
    def list_factors(self) -> dict[str, type[BaseFactor]]: ...
    def list_by_category(self, category: str) -> dict[str, type[BaseFactor]]: ...
```

### BaseFactor ABC

```python
class BaseFactor(ABC):
    @classmethod
    @abstractmethod
    def factor_id(cls) -> str: ...

    @classmethod
    @abstractmethod
    def spec(cls) -> FactorSpec: ...

    @abstractmethod
    def compute(self, data: pd.DataFrame) -> pd.Series: ...

    @classmethod
    def required_columns(cls) -> list[str]: ...
```

## Acceptance Criteria

- [ ] FactorSpec 定义完整，包含所有必要字段
- [ ] FactorRegistry 实现 register/unregister/get/list
- [ ] BaseFactor ABC 定义清晰，子类必须实现 3 个方法
- [ ] 注册时校验 factor_id 非空且不重复
- [ ] 单元测试覆盖注册/注销/查找/重复注册

## Dependencies

- None (P0 foundation)
