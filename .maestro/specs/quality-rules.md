---
title: Quality Rules
readMode: optional
priority: medium
scope: project
dimension: specs
keywords: [test, coverage, quality, market-data]
---

# Quality Rules

- [test:frozen-dataclass] 市场数据模型必须包含 to_dict/from_dict 往返测试，确保序列化一致性 (2026-05-19)
- [test:missing-file] 数据加载函数必须测试 FileNotFoundError 场景，返回空结果而非抛出异常 (2026-05-19)
- [test:backward-compat] adj_type 参数必须测试 NONE 默认值保持向后兼容性 (2026-05-19)
- [test:enum-values] 所有枚举类型必须测试 value 属性正确性（如 NorthChannel.HGT.value == "沪股通"） (2026-05-19)
- [test:scoring-pipeline] ScoringEngine 必须测试 register/unregister 动态管理、权重归一化、多维度聚合 (2026-05-19)
- [test:backward-compat] 新增 dataclass 字段必须测试旧数据格式兼容性（Lazy Upcast） (2026-05-19)
- [test:coverage-target] 核心模块测试覆盖率目标 ≥ 80%，关键路径 ≥ 90% (2026-05-19)
