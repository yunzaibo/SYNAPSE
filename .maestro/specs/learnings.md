---
title: Learnings
readMode: optional
priority: medium
scope: project
dimension: specs
keywords: [bug, learning, debugging, market-semantics]
---

# Learnings

- [bug:compensation-workdays] 中国调休工作日（如春节前补班）需要特殊处理，不能简单依赖 weekend 判断，必须维护 CHINA_TRADING_DAYS 集合 (2026-05-19)
- [learning:decimal-precision] A 股价格调整必须使用 Decimal 类型而非 float，避免浮点精度问题（如 24.01 * 1.10 = 26.4101 而非 26.411） (2026-05-19)
- [learning:ipo-no-limit] IPO 首日不设涨跌停限制，price_limit 函数需要特殊处理 symbol.startswith('N') 的情况 (2026-05-19)
- [learning:lazy-upcast] 新增 dataclass 字段时使用默认值实现 Lazy Upcast，to_dict/from_dict 自动处理新旧格式兼容 (2026-05-19)
- [learning:weight-auto-normalize] 评分权重总和不为 1 时自动归一化并发出 warning，而非抛出异常，提高容错性 (2026-05-19)
- [bug:shared-mutable-state] DI 组件中的共享可变状态（如 MetricsCalculator._benchmark_returns）会导致并发和复用问题，应在 compute() 调用间重置 (2026-05-20)
- [bug:path-traversal] persistence 层 factor_id/run_id 未做路径清理，存在路径遍历漏洞，需要 sanitize 输入 (2026-05-20)
