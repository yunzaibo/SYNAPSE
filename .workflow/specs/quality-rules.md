---
title: "Quality Rules"
readMode: required
priority: medium
category: review
keywords:
  - quality
  - lint
  - rule
  - enforcement
  - testing
  - coverage
---

# Quality Rules

## Testing & Coverage

- [rule:quality] 新代码最低 80% 测试覆盖率，低于阈值禁止合并
- [rule:quality] 提交代码中禁止跳过测试（.skip/.only）

## Lint & Type Check

- [rule:quality] 所有代码必须通过 linter 检查（pre-commit 强制）
- [rule:quality] 类型检查必须通过（mypy --strict）

## Testing Patterns (P3 Hardening)

- [rule:testing] ABC 的所有具体实现必须有正向和反向单元测试
- [pattern:debt] 技术债务用内联注释记录：说明当前限制和未来改进路径

## Entries

<spec-entry category="quality" keywords="coverage,skip-test,lint,type-check" date="2026-05-18">

### Round 5: 质量规则确认

用户选择：最低测试覆盖率 + 禁止跳过测试 + Lint 必须通过 + 类型检查通过

</spec-entry>
