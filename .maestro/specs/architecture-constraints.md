---
title: Architecture Constraints
readMode: optional
priority: medium
scope: project
dimension: specs
keywords: [architecture, design, adapter, dependency, parquet, round-half-up, source-provenance]
---

# Architecture Constraints

- [decision:data-source] DataSource ABC 作为统一数据源接口，所有适配器必须继承并实现 fetch(tickers) 方法 (2026-05-19)
- [pattern:optional-deps] 可选依赖使用 try/except ImportError 模式优雅降级，不阻塞核心功能 (2026-05-19)
- [decision:parquet-storage] 调整因子、北向资金、指数成分等市场数据使用 Parquet 格式存储，支持高效列式查询 (2026-05-19)
- [rule:round-half-up] 所有 A 股金融计算使用 ROUND_HALF_UP（四舍五入），不使用银行家舍入法 (2026-05-19)
- [rule:source-provenance] 所有数据记录必须包含 source 字段用于来源追溯 (2026-05-19)
- [decision:scoring-weights] 4 维度评分权重默认值：signal=0.35, event=0.30, portfolio=0.20, market=0.15，支持自定义覆盖 (2026-05-19)
- [pattern:backward-compat-fields] 新增 dataclass 字段必须提供默认值，to_dict/from_dict 使用 .get() 实现 Lazy Upcast (2026-05-19)
