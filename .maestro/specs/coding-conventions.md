---
title: Coding Conventions
readMode: optional
priority: medium
scope: project
dimension: specs
keywords: [pattern, adapter, rate-limit, pipeline, frozen-dataclass, adj-type, lazy-imports, yaml-config, regex-registry]
---

# Coding Conventions

- [pattern:adapter-factory] adapter_fetch_fn 工厂函数将 DataSource 适配为 StreamingIngestion 的 fetch_fn callable (2026-05-19)
- [pattern:rate-limiting] 数据源适配器内置 min_interval_sec 频率控制，避免 API 过载 (2026-05-19)
- [pattern:frozen-dataclass] 市场数据模型使用 `@dataclass(frozen=True, slots=True)` 实现不可变性，配合 to_dict/from_dict 方法 (2026-05-19)
- [pattern:adj-type-default] adj_type 参数默认值为 AdjustmentType.NONE，确保向后兼容性 (2026-05-19)
- [pattern:pipeline-scoring] ScoringEngine 使用可组合的评分函数管道，通过 register/unregister 动态管理评分维度 (2026-05-19)
- [pattern:stable-sort] 排序使用 key + reverse 参数实现稳定排序，确保相同分数的条目保持原始顺序 (2026-05-19)
- [pattern:single-pass-computation] 性能关键的指标计算使用单次 O(n) 遍历累加器模式，避免多次遍历 DataFrame (2026-05-20)
- [pattern:protocol-di] 可选组件使用 Protocol 接口定义，BacktestEngine 等通过构造函数注入，实现依赖反转 (2026-05-20)
- [pattern:lazy-imports-cross-package] 跨包依赖使用 __getattr__ 懒加载避免循环导入，NLP 模块通过此模式与 event 包解耦 (2026-05-20)
- [pattern:yaml-lexicon-config] 领域词典使用 YAML 文件 + schema 校验，支持用户自定义无需改代码 (2026-05-20)
- [pattern:regex-pattern-registry] 金融指标/事件抽取使用 dict-based 正则模式注册表，便于扩展新指标类型 (2026-05-20)
