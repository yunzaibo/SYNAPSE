---
title: Coding Conventions
readMode: optional
priority: medium
scope: project
dimension: specs
keywords: [pattern, adapter, rate-limit, pipeline, frozen-dataclass, adj-type]
---

# Coding Conventions

- [pattern:adapter-factory] adapter_fetch_fn 工厂函数将 DataSource 适配为 StreamingIngestion 的 fetch_fn callable (2026-05-19)
- [pattern:rate-limiting] 数据源适配器内置 min_interval_sec 频率控制，避免 API 过载 (2026-05-19)
- [pattern:frozen-dataclass] 市场数据模型使用 `@dataclass(frozen=True, slots=True)` 实现不可变性，配合 to_dict/from_dict 方法 (2026-05-19)
- [pattern:adj-type-default] adj_type 参数默认值为 AdjustmentType.NONE，确保向后兼容性 (2026-05-19)
- [pattern:pipeline-scoring] ScoringEngine 使用可组合的评分函数管道，通过 register/unregister 动态管理评分维度 (2026-05-19)
- [pattern:stable-sort] 排序使用 key + reverse 参数实现稳定排序，确保相同分数的条目保持原始顺序 (2026-05-19)
