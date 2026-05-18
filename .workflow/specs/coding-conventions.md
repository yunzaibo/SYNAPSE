---
title: "Coding Conventions"
readMode: required
priority: high
category: coding
keywords:
  - style
  - naming
  - import
  - pattern
  - convention
  - formatting
---

# Coding Conventions

## Formatting

- [rule:style] 严格遵循 PEP 8，最大行宽 88（Black 格式化）
- [rule:style] 优先使用提前返回/守卫子句，避免深层嵌套（Early returns）

## Naming

- [rule:naming] 变量和函数使用 snake_case（如 get_user_name）
- [rule:naming] 类、数据类使用 PascalCase（如 UserProfile）
- [rule:naming] 常量使用 UPPER_SNAKE_CASE（如 MAX_RETRIES）
- [rule:naming] 不使用前缀区分类型，遵循 Python 惯例

## Imports

- [rule:import] 使用包导入（from synapse.core import X）
- [rule:import] 禁止循环依赖

## Patterns

- [rule:pattern] 所有函数签名和类属性使用类型提示（Type hints）
- [rule:pattern] 优先使用纯函数、列表推导，避免可变状态（Functional style）
- [rule:pattern] dataclass 用于数据建模，纯函数用于计算逻辑

## Patterns (P3 Hardening)

- [pattern:enum] 枚举合并使用向后兼容别名：`NewEnum = OldEnum` 保留旧导入，移除重复定义
- [pattern:exception] 异常收窄：只捕获 API 实际抛出的异常（如 `date.fromisoformat()` 仅抛 ValueError）
- [pattern:integration] 集成测试覆盖跨模块流水线（如 detection → dedup）

## Entries

<spec-entry category="coding" keywords="type-hints,functional,pep8,early-return" date="2026-05-18">

### Round 1: 编码风格确认

用户选择：Type hints + Functional style + PEP 8 strict + Early returns（可同时使用，互补不冲突）

</spec-entry>

<spec-entry category="naming" keywords="snake-case,pascal-case,upper-snake,no-prefix" date="2026-05-18">

### Round 1: 命名规范确认

用户选择：snake_case 变量 + PascalCase 类型 + UPPER_SNAKE 常量 + 无前缀

</spec-entry>
