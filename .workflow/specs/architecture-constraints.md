---
title: "Architecture Constraints"
readMode: required
priority: high
category: arch
keywords:
  - architecture
  - module
  - layer
  - boundary
  - dependency
  - structure
  - performance
  - security
---

# Architecture Constraints

## Module Structure

- [rule:arch] 模块间禁止循环依赖
- [rule:arch] 计算逻辑/服务必须无状态（状态仅在数据层）
- [rule:arch] 使用依赖注入提升可测试性（Python 中使用参数注入）

## Layer Boundaries

- [rule:arch] 严格分层：UI → Workflow → Core → Data（不可跳层）

## Dependency Rules

- [rule:tech] 添加新依赖需要明确理由和审查
- [rule:tech] 所有依赖使用精确版本号
- [rule:tech] 遵循 pandas/numpy 官方最佳实践

## Technology Constraints

- [rule:perf] 分析查询响应时间 < 500ms（研究场景）
- [rule:perf] 大文件分块加载，避免内存溢出
- [rule:perf] 计算结果缓存，避免重复计算
- [rule:perf] 避免 O(n²) 循环，优先向量化操作

## Security Constraints

- [rule:security] 所有用户输入必须验证和清理
- [rule:security] API 密钥、密码不入代码，用环境变量
- [rule:security] 文件路径必须验证，防止目录遍历
- [rule:security] YAML 加载禁用 unsafe_load（使用 yaml.safe_load）

## File Organization

- [rule:file] 测试放在独立 tests/ 目录（保持 P1 一致性）
- [rule:file] 使用 __init__.py 做包导入（库项目需要）

## Documentation

- [rule:doc] 数据类和核心函数必须有 docstring（Public API docstring）
- [rule:doc] 复杂业务逻辑注释"为什么"而非"做什么"（Why-only 注释）
- [rule:doc] 每个主要模块有自己的 README

## Design Decisions (P3 Hardening)

- [decision:abc] ABC 使用 @classmethod @abstractmethod 实现零成本类级别注册（避免创建临时实例）
- [rule:cli] CLI 命令必须尽早验证目录/路径存在性（fail-fast 模式）

## Entries

<spec-entry category="arch" keywords="ADR-005,ADR-006,China-A-shares,event-driven,sentiment,market-domain,roadmap" date="2026-05-17">

### ADR-005/006: China A-Shares + Event-driven route frozen

SYNAPSE positions as Chinese AI-native Financial Research System. Initial market: China A-Shares. Initial focus: Event-driven + Sentiment-aware Research. P1 = China Market Semantics Layer only (no NLP, RAG, knowledge graph, multi-agent). ADR-005 Accepted, ADR-006 Accepted. US Equities rejected — too mature, low differentiation potential.

</spec-entry>

<spec-entry category="arch" keywords="architecture,layered,dependency-injection,stateless" date="2026-05-18">

### Round 3: 架构约束确认

用户选择：禁止循环依赖 + 严格分层 + 无状态服务 + 依赖注入

</spec-entry>

<spec-entry category="performance" keywords="query-response,chunked-loading,cache,vectorization" date="2026-05-18">

### Round 4: 性能约束确认

用户选择：查询响应时间 + 分块加载 + 结果缓存 + 避免 N+1

</spec-entry>

<spec-entry category="security" keywords="input-validation,no-code-secrets,path-validation,yaml-safety" date="2026-05-18">

### Round 4: 安全约束确认

用户选择：输入验证 + 无代码密钥 + 路径验证 + 安全 YAML

</spec-entry>
- [decision:architecture] Feature 隔离：每个新 feature 独立模块文件（sentiment.py, divergence.py, correlation.py），无跨 feature 耦合 (2026-05-19)
