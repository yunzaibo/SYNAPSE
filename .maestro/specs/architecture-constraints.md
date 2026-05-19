---
title: Architecture Constraints
readMode: optional
priority: medium
scope: project
dimension: specs
keywords: [architecture, design, adapter, dependency]
---

# Architecture Constraints

- [decision:data-source] DataSource ABC 作为统一数据源接口，所有适配器必须继承并实现 fetch(tickers) 方法 (2026-05-19)
- [pattern:optional-deps] 可选依赖使用 try/except ImportError 模式优雅降级，不阻塞核心功能 (2026-05-19)
