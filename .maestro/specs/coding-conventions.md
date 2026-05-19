---
title: Coding Conventions
readMode: optional
priority: medium
scope: project
dimension: specs
keywords: [pattern, adapter, rate-limit, pipeline]
---

# Coding Conventions

- [pattern:adapter-factory] adapter_fetch_fn 工厂函数将 DataSource 适配为 StreamingIngestion 的 fetch_fn callable (2026-05-19)
- [pattern:rate-limiting] 数据源适配器内置 min_interval_sec 频率控制，避免 API 过载 (2026-05-19)
